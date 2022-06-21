import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { SettingsComponent } from './settings.component';
import { MatIconModule } from '@angular/material/icon';
import { FormsModule } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { AppRoutingModule } from 'src/app/app-routing.module';
import { MatDividerModule } from '@angular/material/divider';
import { MatRippleModule } from '@angular/material/core';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { SharedModule } from '../shared/shared.module';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { LogLevelComponent } from './components/log_level/log-level.component';
import { MatTooltipModule } from '@angular/material/tooltip';
import { OBDConnectionComponent } from './obd-connection/obd-connection.component';
import { OapInjectorComponent } from './oap-injector/oap-injector.component';
import { CommandLookupComponent } from './obd-connection/command-lookup/command-lookup.component';



@NgModule({
  declarations: [
    SettingsComponent,
    LogLevelComponent,
    OBDConnectionComponent,
    OapInjectorComponent,
    CommandLookupComponent,
  ],
  imports: [
    CommonModule,
    SharedModule,
    MatSlideToggleModule,
    AppRoutingModule,
    MatIconModule,
    FormsModule,
    MatListModule,
    MatCardModule,
    MatButtonModule,
    MatDividerModule,
    MatRippleModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatRippleModule,
    MatRadioModule,
    MatExpansionModule,
    MatAutocompleteModule,
    MatTooltipModule
  ]
})
export class SettingsModule { }
