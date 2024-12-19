import { Component, OnDestroy, OnInit } from '@angular/core';
import { DisplayService } from 'src/app/shared/services/display.service';
import { environment } from 'src/environments/environment';
import { Settings } from './settings.model';
import { SettingsService } from './settings.service';


@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent implements OnInit, OnDestroy {


  isDarkTheme: boolean;
  isRHD: boolean;
  settings$: Promise<Settings>;

  version = environment.version;

  constructor(
    public display: DisplayService,
    private settingsService: SettingsService,
  ) { }

  switchTheme() {
    this.display.setTheme(this.isDarkTheme ? 'dark' : 'light');
  }

  saveSettings = () => {
    console.log("Settings action invoked", this.settings$);
  }

  clearSiteDataAndRefresh(): void {
    localStorage.clear();
    sessionStorage.clear();
    this.clearCookies();
    window.location.reload();
  }

  private clearCookies(): void {
    const cookies = document.cookie.split(";");

    for (const cookie of cookies) {
      const eqPos = cookie.indexOf("=");
      const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
      document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
    }
  }

  resetSettings() {
    this.settingsService.reset();
  }

  ngOnInit(): void {
    this.settings$ = this.settingsService.getSettings();
    this.isDarkTheme = this.display.theme === 'dark';
    this.isRHD = this.display.getSidenavPosition() === 'end';
  }

  ngOnDestroy() {
    this.settings$.then(s => this.settingsService.updateSettings(s));
  }

}
