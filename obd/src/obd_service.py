import os
import signal
import asyncio
import threading
from collections import defaultdict

import elm
import obd
from obd import OBDResponse, OBDCommand

from .response_callback import ResponseCallback
from .configuration_service import ConfigurationService
from .logger import register_logger
from .unit_systems import imperial

class OBDService():

    def __init__(self, sio, config):
        self.logger = register_logger(obd.__name__, config.settings["connection"]["log_level"], file_logger=True)

        self.__register_events(sio)

        self.sio = sio
        self.__emulator = None
        self.__lock = asyncio.Lock()
        self.config: ConfigurationService = config
        self.__commands = defaultdict(OBDResponse)   # key = OBDCommand, value = Response
        self.__callbacks = defaultdict(dict[ResponseCallback])  # key = OBDCommand, value = list of Functions
        self.__is_running = asyncio.Event()
        self.__is_connecting_now = asyncio.Event()
        self.connection = obd.OBD("init") # a temp connection to nowhere so self.connection instantiated


    async def connect(self, portstr: str = None):
        async with self.__lock:
            self.__connect(portstr)
        

    def __connect(self, portstr: str = None):
        if self.connection.is_connected() or self.__is_connecting_now.is_set():
            return
        self.__is_connecting_now.set()
        if portstr is None:
            params = self.config.load_connection_params()
        else:
            params = {"portstr": portstr}

        self.connection = obd.OBD(
            params.get("portstr"),
            params.get("baudrate"),
            params.get("protocol"))
        self.__is_connecting_now.clear()


    async def disconnect(self):
        async with self.__lock:
            await self.__disconnect()


    async def __disconnect(self):
        self.connection.close()
        self.__commands.clear()
        self.__callbacks.clear()


    async def shutdown(self):
        async with self.__lock:
            await self.__stop()
            await self.__disconnect()


    async def start(self):
        async with self.__lock:
            await self.__start()


    async def __start(self):
        if not self.connection.is_connected() or len(self.__commands) == 0:
            return

        if not self.__is_running.is_set():
            self.__is_running.set()
            self.sio.start_background_task(self.__watch_loop)


    async def stop(self):
        async with self.__lock:
            await self.__stop()


    async def __stop(self):
        if self.__is_running.is_set():
            self.__is_running.clear()


    async def watch_commands(self, commands: list[OBDCommand], callback: ResponseCallback, force=False):
        async with self.__lock:
            await self.__watch_commands(list(commands), callback, force)


    async def __watch_commands(self, commands: list[OBDCommand], callback: ResponseCallback, force=False):
        await self.__stop()
        for cmd in commands:
            if not force and not self.connection.test_cmd(cmd):
                # `test_cmd()` will print warnings
                continue
            
            # New command being watched, store the command
            if cmd not in self.__commands:
                self.__commands[cmd] = None  # Initialize with a default value

            if callback.client_id not in self.__callbacks[cmd]:
                self.__callbacks[cmd][callback.client_id] = callback

        await self.__start()


    async def unwatch_all(self, client_id: str):
        async with self.__lock:
            await self.__unwatch_commands(list(self.__commands.keys()), client_id)


    async def unwatch_commands(self, commands: list[OBDCommand], client_id: str):
        async with self.__lock:
            await self.__unwatch_commands(commands, client_id)


    async def __unwatch_commands(self, commands: list[OBDCommand], client_id: str):
        await self.__stop()
        for cmd in commands:
            if cmd in self.__commands and client_id in self.__callbacks[cmd]:
                self.__callbacks[cmd].pop(client_id)

            if not self.__callbacks[cmd] and cmd in self.__commands:
                self.__commands.pop(cmd)

        await self.__start()
                        

    async def __watch_loop(self):
        while self.__is_running.is_set() and self.connection.is_connected():
            if len(self.__commands) > 0:
                await self.sio.sleep(self.config.delay)
                # loop over the requested commands, send, and collect the response
                for c in list(self.__commands):
                    # re-check invariant in case a client acts between command iterations
                    if not self.__is_running.is_set() or not self.connection.is_connected():
                        break
                    # force, since commands are checked for support in watch()
                    r = self.connection.query(c, force=True)

                    # check empty response
                    if r.is_null():
                        continue

                    if self.config.use_imperial_units and (r.command.mode == 1 or 2):
                        r = imperial.convert(r)

                    # check if value has changed
                    if self.__commands[c] == r.value:
                        continue

                    # store the response
                    self.__commands[c] = r.value

                    # fire the callbacks, if there are any
                    for callback in list(self.__callbacks[c].values()):
                        await callback.run(r)
            else:
                await self.sio.sleep(0.25)  # idle


    def __register_events(self, sio):

        @sio.event
        async def disconnect(sid):
            await self.unwatch_all(sid)


        @sio.event
        async def watch(sid, commands):
            async def sid_emit(r):
                await sio.emit("watching", r, to=sid)

            obd_commands = [obd.commands[c] for c in commands if c is not None and obd.commands.has_name(c)]
            await self.watch_commands(obd_commands, ResponseCallback(sid, sid_emit, is_async=True))

        
        @sio.event
        async def unwatch(sid, commands):
            obd_commands = [obd.commands[c] for c in commands if c is not None and obd.commands.has_name(c)]
            await self.unwatch_commands(obd_commands, sid)


        @sio.event
        async def unwatch_all(sid):
            await self.unwatch_all(sid)
        
        
        @sio.event
        async def status(sid):
            await sio.emit('status', self.connection.status(), to=sid)


        @sio.event
        async def is_connected(sid):
            await sio.emit('is_connected', self.connection.is_connected(), to=sid)


        @sio.event
        async def port_name(sid):
            await sio.emit('port_name', self.connection.port_name(), to=sid)


        @sio.event
        async def supports(sid, cmd):
            if obd.commands.has_name(cmd):
                await sio.emit('supports', self.connection.supports(obd.commands[cmd]), to=sid)
            else:
                await sio.emit('supports', False, to=sid)


        @sio.event
        async def protocol_id(sid):
            await sio.emit('protocol_id', self.connection.protocol_id(), to=sid)


        @sio.event
        async def protocol_name(sid):
            await sio.emit('protocol_name', self.connection.protocol_name(), to=sid)


        @sio.event
        async def supported_commands(sid):
            await sio.emit('supported_commands', self.connection.supported_commands, to=sid)


        @sio.event
        async def query(sid, cmd):
            if obd.commands.has_name(cmd):
                await self.stop()
                await sio.emit('query', self.connection.query(obd.commands[cmd]), to=sid)
                await self.start()
            else:
                await sio.emit('query', None, to=sid)


        @sio.event
        async def has_name(sid, name):
            await sio.emit('has_name', obd.commands.has_name(name), to=sid)


        @sio.event
        async def close(sid):
            await self.stop()
            self.connection.close()
            await sio.emit('obd_closed')


        @sio.event
        async def available_ports(sid):
            await sio.emit('available_ports', obd.scan_serial(), to=sid)


        @sio.event
        async def all_protocols(sid):
            all = [
                obd.protocols.ISO_14230_4_5baud,
                obd.protocols.ISO_14230_4_fast,
                obd.protocols.ISO_15765_4_11bit_250k,
                obd.protocols.ISO_15765_4_11bit_500k,
                obd.protocols.ISO_15765_4_29bit_250k,
                obd.protocols.ISO_15765_4_29bit_500k,
                obd.protocols.ISO_9141_2,
                obd.protocols.SAE_J1850_PWM,
                obd.protocols.SAE_J1850_VPW,
                obd.protocols.SAE_J1939
            ]
            await sio.emit('all_protocols', sorted(all, key=lambda p: p.ELM_ID), to=sid)


        @sio.event
        async def all_dtcs(sid):
            await sio.emit('all_dtcs', obd.codes.DTC, to=sid)


        @sio.event
        async def clear_dtc(sid):
            await self.stop()
            res = self.connection.query(obd.commands['CLEAR_DTC'])
            await self.start()
            return res


        @sio.event
        async def all_commands(sid):
            all = list(obd.commands.modes)
            all[0] = obd.commands.base_commands()
            await sio.emit('all_commands', all, to=sid)


        @sio.event
        async def get_command(sid, cmd):
            if obd.commands.has_name(cmd):
                await sio.emit('get_command', obd.commands[cmd], to=sid)
            else:
                await sio.emit('get_command', None, to=sid)


        @sio.event
        async def connect_obd(sid, portstr=None):
            await self.connect(portstr)  
            await sio.emit("connect_obd", self.connection.is_connected())


        @sio.event
        async def start_emulator(sid):
            if self.__emulator is None:
                self.__emulator = elm.Elm()
                threading.Thread(target=self.__emulator.run, daemon=True).start()
                await sio.emit('emulator_port', self.__emulator.get_pty())


        @sio.event
        async def stop_emulator(sid):
            if not self.__emulator is None:
                self.__emulator.terminate()
                self.__emulator = None
                await sio.emit('stop_emulator')
            

        @sio.event
        async def kill(sid):
            os.kill(os.getpid(), signal.SIGTERM)