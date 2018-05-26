import { Injectable } from '@angular/core';
import {Subject} from "rxjs/internal/Subject";
import {BehaviorSubject} from "rxjs/internal/BehaviorSubject";

@Injectable({
  providedIn: 'root'
})
export class GlobalFilterStateService {

  state: Subject<GlobalFilterState> = new BehaviorSubject({year: null, bid: null});

  private year: number = null;
  private bid: number = null;

  constructor() {
  }

  setYear(year: number) {
    this.year = year;
    this.next();
  }
  setBoard(bid: number) {
    this.bid = bid;
    this.next();
  }

  private next() {
    this.state.next({
      year: this.year,
      bid: this.bid,
  });
  }
}

export interface GlobalFilterState {
  year: number,
  bid: number,
}
