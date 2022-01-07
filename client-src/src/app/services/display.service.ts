import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { OverlayContainer } from '@angular/cdk/overlay';
import { Injectable } from '@angular/core';
import { ThemePalette } from '@angular/material/core';
import { Observable } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class DisplayService {

  palette: ThemePalette;  // this is 'primary' | 'accent' | 'warn'

  theme: string;
  defaultColor: string;

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
    .pipe(
      map(result => result.matches),
      shareReplay()
    );

  isPortrait$: Observable<boolean> = this.breakpointObserver.observe([
    '(orientation: portrait)',
    '(orientation: landscape)',
  ]).pipe(map(result => result.breakpoints['(orientation: portrait)']));

  constructor(
    private breakpointObserver: BreakpointObserver,
    private overlay: OverlayContainer
  ) { }

  setTheme(theme: string) {
    this.overlay.getContainerElement().classList.remove('dark-theme');
    this.overlay.getContainerElement().classList.add(theme + '-theme');
    this.theme = theme;
    localStorage.setItem('theme', this.theme);

    if (this.theme === 'light') {
      this.defaultColor = '#00796b';
    } else {
      this.defaultColor = '#ffc107';
    }
  }

  checkTheme() {
    let existing = localStorage.getItem('theme');
    if (existing) {
      this.setTheme(existing);
    } else {
      this.setTheme('dark');
    }
  }
}
