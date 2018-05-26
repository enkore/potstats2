import { Component } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {YearStateService} from "../year-state.service";

@Component({
  selector: 'app-nav',
  templateUrl: './app-nav.component.html',
  styleUrls: ['./app-nav.component.css']
})
export class AppNavComponent {

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
    .pipe(
      map(result => result.matches)
    );

  selectedYear: number;
  years: number[] = [];

  constructor(private breakpointObserver: BreakpointObserver, private yearState: YearStateService) {
    const now = (new Date()).getFullYear();
    for (let year=now; year >= 2003; year--) { this.years.push(year)}
    yearState.yearSubject.subscribe(year => {
      this.selectedYear = year;
    });
  }
  setYear(event) {
    this.yearState.setYear(event.value);
  }

}
