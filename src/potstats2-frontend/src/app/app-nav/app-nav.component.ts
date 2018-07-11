import {Component, OnInit} from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import {delay, filter, map, mergeMap} from 'rxjs/operators';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {BoardsService} from '../data/boards.service';
import {ActivatedRoute, NavigationEnd, Router} from '@angular/router';

@Component({
  selector: 'app-nav',
  templateUrl: './app-nav.component.html',
  styleUrls: ['./app-nav.component.css']
})
export class AppNavComponent implements OnInit {

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
    .pipe(
      map(result => result.matches)
    );

  selectedYear: number;
  years: number[] = [];

  boards = this.boardsService.execute({});
  selectedBoard: number;

  constructor(private breakpointObserver: BreakpointObserver,
              private router: Router,
              private activatedRoute: ActivatedRoute,
              private stateService: GlobalFilterStateService,
              private boardsService: BoardsService) {
    const now = (new Date()).getFullYear();
    for (let year = now; year >= 2003; year--) { this.years.push(year); }
  }
  setYear($event) {
    this.stateService.setYear($event.value);
  }

  setBoard($event) {
    this.stateService.setBoard($event.value);
  }
  ngOnInit(): void {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      map(() => this.activatedRoute),
      map(route => {
        while (route.firstChild) { route = route.firstChild; }
        return route;
      }),
      filter(route => route.outlet === 'primary'),
      map(route => route.snapshot.paramMap)
  ).subscribe((data) => {
    console.log(data);
    });
    this.stateService.state.pipe(
      // We delay the update to another cycle in case another components changes the year while initialising
      delay(0)
    ).subscribe(state => {
      this.selectedYear = state.year;
      this.selectedBoard = state.bid;
    });
  }


}
