import { Injectable } from '@angular/core';
import {Subject} from "rxjs/internal/Subject";
import {BehaviorSubject} from "rxjs/internal/BehaviorSubject";

@Injectable({
  providedIn: 'root'
})
export class YearStateService {

  yearSubject: Subject<number> = new BehaviorSubject(null);
  constructor() {
  }

  setYear(year: number) {
    this.yearSubject.next(year);
  }
}
