"""
    Adapted from https://github.com/bluewave-studio/openauto-pro-api/blob/main/api_examples/python/ObdInject.py#L2

    The OAPInjector passes OBD values from python-OBD to OpenAuto Pro via its protobuf API

"""
from logging import Logger
from src.response_callback import ResponseCallback
from .event_handler import EventHandler
from .Message import Message
from src.injector_base import InjectorBase
from src.obd_service import OBDService
from .Api_pb2 import ObdInjectGaugeFormulaValue, MESSAGE_OBD_INJECT_GAUGE_FORMULA_VALUE, MESSAGE_BYEBYE
from .oap_client import OAPClient
import configparser
import os
import asyncio
import obd
from obd import OBDCommand

MAX_RESTARTS = 10


class OAPInjector(InjectorBase):
    """
    Controls data injection and connection to the OpenAuto Pro protobuf API (obd gauges, notifications, status icon)
    """

    def __init__(self, obd: OBDService, logger: Logger, *args, **kwargs):
        handler = EventHandler()
        self.client = OAPClient(handler)
        self.obd = obd
        self.logger = logger
        self.logger.info("======================================================")
        self.logger.info("Initializing an OpenAuto Pro injector." + str(args) + str(kwargs))
        self.__init_cmds()
        self._oap_api_port = self.__parse_oap_api_port()
        self.__oap_inject = ObdInjectGaugeFormulaValue()
        self.__n_restarts = 0
        self._enabled = asyncio.Event()
        self._enabled.set()

        @handler.event
        async def disconnect(restart=False):
            await obd.unwatch_all(self.id)
            if restart:
                await self.restart()

        @handler.event
        async def ping():
            if not obd.connection.is_connected():
                await obd.connect()
                await obd.watch_commands(self.get_commands(), ResponseCallback(self.id, self.inject, is_async=True))


    async def restart(self):
        """
        On OAP event handler failure restart if still enabled and not reached max restart attempts
        """
        self.logger.info("OAP injector event handler is no longer active")
        if self._enabled.is_set() and self.__n_restarts < MAX_RESTARTS:
            self.logger.info("OAP injector restarting...")
            self.__n_restarts += 1
            await self.start()

        if self.__n_restarts >= MAX_RESTARTS:
            self.logger.info(
                "OAP injector exceeded maxmium number of restarts. Make sure OpenAuto Pro is running and manually disable/enable me")


    async def start(self):
        """
        Start the injector from a disabled state. Not called on __init__, called at some point during runtime usually from an async event 
        """
        self._enabled.set()
        self.logger.info("OAP injector starting...")
        
        attempts = 0    
        while True:
            await asyncio.sleep(attempts * 0.25)
            attempts += 1
            if not self._enabled.is_set() or self.client.is_connected.is_set():
                break
        
            try:
                host = os.environ.get("OAP_HOST", "127.0.0.1")
                self.logger.info(f"Attempting to connect to the OAP protobuf API at {host}:{self._oap_api_port}")
                await self.client.connect(host, self._oap_api_port)
            except Exception as e:
                self.logger.error(f"OAP injector error on start: {e}")
        if not self.obd.connection.is_connected():
            await self.obd.connect()
        await self.obd.watch_commands(self.get_commands(), ResponseCallback(self.id, self.inject, is_async=True))


    async def stop(self):
        """Stop and disable the running injection
        """
        self.logger.info("OAP injector stopped by user")
        self.logger.info("======================================================")
        
        await self.obd.unwatch_all(self.id)

        self.__n_restarts = 0
        self._enabled.clear()

        # queue a bye-bye message to be sent; marker for the message queue consumer to stop and disconnect
        byebye = (0, Message(MESSAGE_BYEBYE, 0, bytes()))
        await self.client.message_queue.put(byebye)


    def is_enabled(self):
        """Whether the injecotr is currently enabled but not neccesarily active.

        Returns:
            bool: True if enabled, from settings file at start or was anabled from disabled state by user. False otherwise.
        """
        return self._enabled.is_set()


    def is_active(self):
        return self.client.is_connected.is_set()
    

    def get_commands(self) -> list[OBDCommand]:
        """Get the list of OBD command names used by this injector

        Returns:
            list: List of commands in order as defined in `/home/pi/.openauto/config/openauto_obd_pids.ini`. Example: ['RPM', 'SPEED', ...] 
                    Note: some commands may be None if the injector could not cross reference it with python-obd.
        """
        return [obd.commands[c] for c in self.__commands_names if c is not None and obd.commands.has_name(c)]
    

    @property
    def id(self):
        return 'oap'
    

    async def inject(self, obd_response):
        """Inject an obd response value to its OAP gauge

        Args:
            obd_response obd.OBDResponse: The response object returned in python-obd callback
        """
        if obd_response.is_null():
            return
        try:
            # The index of the command as defined in the openauto config file, may raise a ValueError
            cmd_index = self.__commands_names.index(obd_response.command.name)
            self.__oap_inject.formula = f"getPidValue({cmd_index})"

            if not hasattr(obd_response.value, "magnitude"):
                return

            self.__oap_inject.value = obd_response.value.magnitude

            # only queue inject msg if value has changed
            self.logger.debug(f"Injecting value: {self.__oap_inject.value} to PID: {obd_response.command.name} ({cmd_index})")

            msg = (1, Message(MESSAGE_OBD_INJECT_GAUGE_FORMULA_VALUE, 0, self.__oap_inject.SerializeToString()))

            await self.client.message_queue.put(msg)

        except ValueError:
            # This OBD response is for a command not needed by OAP. i.e. the obd_response.command is not contained in self.__commands
            return
        except Exception as e:
            self.logger.error("OAP injector error on inject: {e}")

    def __parse_oap_api_port(self):
        """We can try to determine the OpenAuto Pro API port from the opanauto_system config file. This file may not exist if the user has not altered 
        any settings in the OpenAuto GUI so in that case assume the port is 44405.

        Returns:
            int: The API port from the confdig file, or 44405 if not found.
        """
        config = configparser.ConfigParser()
        oap_sys_conf_path = os.path.join(os.path.join(os.environ.get(
            'OAP_CONFIG_DIR', "/home/pi/.openauto/config"), "openauto_system.ini"))
        config.read(oap_sys_conf_path)
        return config.getint('Api', 'EndpointListenPort', fallback=44405)

    def __init_cmds(self):
        """Parse the OAP PID configuration file and construct a list of pythonOBD OBDCommands which 
        correspond to the OpenAuto pids in the order they appear in the file. These are not expected to change at runtime.

        Raises:
            ValueError: When a command from the file is not defined by pythonOBD, but is caught and replaced with None in this injector's command list
        """
        pid_config_path = os.path.join(os.environ.get(
            'OAP_CONFIG_DIR', "/home/pi/.openauto/config"), "openauto_obd_pids.ini")
        config = configparser.ConfigParser()
        config.read(pid_config_path)

        self.__commands_names = []

        num_pids = config.getint("ObdPids", "Count", fallback=0)
        for i in range(num_pids):
            query = config.get(f"ObdPid_{i}", "Query", fallback=None)

            if query is None:
                self.__commands_names.append(None)
                continue

            # Try to parse the PID from the openauto config
            try:
                mode = int(query[:2])
                pid = int(query[2:], 16)    # pid in decimal

                if not obd.commands.has_pid(mode, pid):
                    raise ValueError

                cmd = obd.commands[mode][pid]
            except ValueError:
                # Check if the command is a base command such as ELM_VOLTAGE whose query is b'ATRV' (cannot be indexed from obd.commands), fallback to none
                cmd = next(filter(lambda c: c.command == query.encode(), obd.commands.base_commands()), None)

            if cmd is not None and hasattr(cmd, 'name'):
                self.__commands_names.append(cmd.name)
            else:
                self.logger.warning(f"OAP injector could not determine a valid OBD command for ObdPid_{i} with query: {query}")
                self.__commands_names.append(None)

        self.logger.info(f"OAP injector commands are: {self.__commands_names}")
