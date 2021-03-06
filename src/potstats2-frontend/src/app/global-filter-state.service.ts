import { Injectable } from '@angular/core';
import {Subject} from 'rxjs/internal/Subject';
import {BehaviorSubject} from 'rxjs/internal/BehaviorSubject';

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
    if (year === this.year)  {
      return;
    }
    this.year = year;
    this.next();
  }
  setBoard(bid: number) {
    if (bid === this.bid)  {
      return;
    }
    this.bid = bid;
    this.next();
  }
  setBoth(year: number | string, bid: number | string) {
    if (+year === this.year && +bid === this.bid) {
      return;
    }
    if (+year > 0) {
      this.year = +year;
    }
    if (+bid > 0) {
      this.bid = +bid;
    }
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
  year: number;
  bid: number;
}
