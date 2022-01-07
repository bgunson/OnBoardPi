import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatRadioChange } from '@angular/material/radio';
import { ConnectionParameters, Settings } from '../../models/settings.model';
import { SettingsService } from '../../services/settings.service';

@Component({
  selector: 'app-log-level',
  templateUrl: './log-level.component.html',
  styleUrls: ['./log-level.component.scss', '../../settings.component.scss']
})
export class LogLevelComponent implements OnInit, OnDestroy {

  /**
   * See https://docs.python.org/3/library/logging.html#logging-levels
   */
  levels: string[] = [
    'CRITICAL',
    'ERROR',
    'WARNING',
    'INFO',
    'DEBUG',
    'NOTSET'
  ];

  settings$: Promise<Settings>;
  connection$: Promise<ConnectionParameters>

  constructor(private settingsService: SettingsService) { }

  set(event: MatRadioChange) {
    console.log(event)
  }

  ngOnInit(): void {
    this.settings$ = this.settingsService.getSettings();
    this.connection$ = this.settings$.then(s => s.connection);
  }

  ngOnDestroy(): void {
    this.settings$.then(s => this.settingsService.updateSettings(s));
  }

}
