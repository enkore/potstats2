import { Component } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {GlobalFilterStateService} from "../global-filter-state.service";
import {BoardsService} from "../data/boards.service";

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

  boards = this.boardsService.execute({});
  selectedBoard: number;

  constructor(private breakpointObserver: BreakpointObserver,
              private stateService: GlobalFilterStateService,
              private boardsService: BoardsService) {
    const now = (new Date()).getFullYear();
    for (let year=now; year >= 2003; year--) { this.years.push(year)}
    stateService.state.subscribe(state => {
      this.selectedYear = state.year;
      this.selectedBoard = state.bid;
    });
  }
  setYear($event) {
    this.stateService.setYear($event.value);
  }

  setBoard($event) {
    this.stateService.setBoard($event.value);
  }
}
