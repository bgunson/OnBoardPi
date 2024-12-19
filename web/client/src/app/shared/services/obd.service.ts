import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { scan, share, shareReplay, takeWhile, tap, timeout } from 'rxjs/operators';
import { OBDSocket } from 'src/app/app.module';
import { SettingsService } from 'src/app/settings/settings.service';
import { OBDCommand, OBDResponse, Protocol, ResponseSet } from '../models/obd.model';


/**
 * This service handles communication with the OBD websocket server to control the connection with the vehicle through the python-OBD API.
 * See https://github.com/bgunson/obd-socketio
 */
@Injectable({
  providedIn: 'root'
})
export class OBDService {

  private _watching$: Observable<ResponseSet>;

  /** Active set of watched commands by name */
  private _watchList: Set<string> = new Set<string>();

  private _status$: Observable<string>;
  private _isConnected$: Observable<boolean>;

  // connectingNow: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);    // TODO: maybe make this server side from appSocket event so other clients know if connecting

  constructor(
    private socket: OBDSocket,
    private settingsService: SettingsService
  ) {
    socket.on('unwatch', () => this.watch([...this._watchList]));

    // socket.fromEvent<string>('status').subscribe(v => this._status$.next(v));
    // socket.fromEvent<boolean>('is_connected').subscribe(v => this._isConnected$.next(v));

    socket.on('obd_closed', () => {
      this.isConnected();
      this.getStatus();
    });

    socket.on('obd_connecting', () => {
      this.getStatus();
      this.isConnected();
    });

    socket.on('disconnect', () => {
      this._isConnected$ = of(false)
      this._status$ = of('Not Connected');
    });

    socket.on('connect', () => {
      this.getStatus();
      this.isConnected();
    });
  }

  async waitForConnection(): Promise<boolean> {
    return new Promise(async (resolve, reject) => {
      try {
        const connected: boolean = await this.isConnected().pipe(takeWhile(v => v === false), timeout(5000)).toPromise();
      } catch (err) {
        const connectObd: boolean = confirm(`Looks like the vehicle is not connected. Would you like to try to connect now?\n${err}`);
        if (connectObd) {
          return this.connect().then((connected) => resolve(connected));
        } else {
          reject(false);
        }
      }
    });
  }

  connect(): Promise<boolean> {
    this.socket.emit('connect_obd');
    return this.socket.fromOneTimeEvent<boolean>('connect_obd');
  }

  disconnect(): void {
    this.socket.emit('close');
  }

  getStatus(): Observable<string> {
    this.socket.emit('status');
    if (!this._status$) {
      this._status$ = this.socket.fromEvent<string>('status').pipe(shareReplay());
    }
    return this._status$;
  }

  isConnected(): Observable<boolean> {
    this.socket.emit('is_connected');
    if (!this._isConnected$) {
      this._isConnected$ = this.socket.fromEvent<boolean>('is_connected').pipe(shareReplay());
    }
    return this._isConnected$;
  }

  watch(cmds: string[]): void {
    cmds.forEach(c => this._watchList.add(c));
    this.socket.emit('watch', cmds);
  }

  unwatch(cmds: string[]): void {
    cmds.forEach(c => this._watchList.delete(c));
    this.socket.emit('unwatch', cmds);
  }

  query(cmd: string): Promise<OBDResponse> {
    this.socket.emit('query', cmd);
    return this.socket.fromOneTimeEvent<any>('query');
  }

  getWatching(): Observable<ResponseSet> {
    if (!this._watching$) {
      this._watching$ = this.socket.fromEvent<OBDResponse>('watching').pipe(
        scan((acc: ResponseSet, val: OBDResponse) => {
          acc[val.command.name] = val;
          return acc;
        }, {} as ResponseSet),
        share()
      );
    }
    return this._watching$;
  }

  getCommand(cmd: string): Promise<OBDCommand> {
    this.socket.emit('get_command', cmd);
    return this.socket.fromOneTimeEvent<OBDCommand>('get_command');
  }

  supports(cmd: OBDCommand): Promise<boolean> {
    this.socket.emit('supports', cmd.name);
    return this.socket.fromOneTimeEvent<boolean>('supports');
  }

  getSupported(): Promise<OBDCommand[]> {
    this.socket.emit('supported_commands');
    return this.socket.fromOneTimeEvent<any>('supported_commands');
  }

  allDTCs(): Promise<{ [key: string]: string }> {
    this.socket.emit('all_dtcs');
    return this.socket.fromOneTimeEvent<{ [key: string]: string }>('all_dtcs');
  }

  clearDTCs(): Promise<any> {
    return new Promise(resolve => this.socket.emit('clear_dtc', resolve));
  }

  allProtocols(): Promise<Protocol[]> {
    this.socket.emit('all_protocols');
    return this.socket.fromOneTimeEvent<Protocol[]>('all_protocols');
  }

  allCommands(): Promise<OBDCommand[][]> {
    this.socket.emit('all_commands');
    return this.socket.fromOneTimeEvent<any>('all_commands');
  }

  /** 
   * Check if user has 'Supported only' setting chosen locally
   *  
   * @returns All OBD commands or only those supported if the seeting is true
   */
  async usersCommands(): Promise<OBDCommand[][]> {
    let cmds = this.allCommands();
    if (this.settingsService.getUserSetting('supportedOnly') === "true") {
      const supported = await this.getSupported().then(cmds => cmds.map(c => c.name));
      cmds = cmds.then(modes => modes.map(cmds => cmds.filter(c => c ? supported.includes(c.name) : false)));
    }
    return cmds;
  }

  getProtocolName(): Promise<string> {
    this.socket.emit('protocol_name');
    return this.socket.fromOneTimeEvent<string>('protocol_name');
  }

  getPortName(): Promise<string> {
    this.socket.emit('port_name');
    return this.socket.fromOneTimeEvent<string>('port_name');
  }

  getAvailablePorts(): Promise<string[]> {
    this.socket.emit('available_ports');
    return this.socket.fromOneTimeEvent<string[]>('available_ports');
  }

  getInjectorState(injectorType: string): Promise<any> {
    this.socket.emit('injector_state', injectorType);
    return this.socket.fromOneTimeEvent<any>('injector_state');
  }

  setLoggerLevel(loggerName: string, level: string) {
    this.socket.emit('set_logger_level', loggerName, level);
  }

  enableInjector(injectorType: string) {
    this.socket.emit('enable_injector', injectorType);
  }

  disableInjector(injectorType: string) {
    this.socket.emit('disable_injector', injectorType);
  }

}
