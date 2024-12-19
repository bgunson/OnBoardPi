import { Injectable } from '@angular/core';
import { AppSocket } from 'src/app/app.module';
import { CrudService } from 'src/app/shared/services/crud.service';
import { Settings } from './settings.model';

@Injectable({
  providedIn: 'root'
})
export class SettingsService {

  constructor(private crud: CrudService, private socket: AppSocket) { }

  getUserSetting(key: string): string | null {
    return localStorage.getItem(key);
  }

  updateUserSetting(key: string, value: any) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  getSettings() {
    this.crud.read<Settings>('settings');
    return this.socket.fromOneTimeEvent<Settings>('settings:response');
  }

  updateSettings(updated: Settings) {
    this.socket.emit('settings:update', updated);
  }

  reset() {
    if (window.confirm("Are you sure you want to do this?")) {
      this.socket.emit('settings:reset')
    }
  }

}
