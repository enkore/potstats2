import {MatSort} from '@angular/material';
import { Observable, combineLatest } from 'rxjs';
import {PosterStats} from '../data/types';
import {PosterStatsService} from '../data/poster-stats.service';
import {YearStateService} from "../year-state.service";
import {BaseDataSource} from "../base-datasource";

export class AppPosterstatsDataSource extends BaseDataSource<PosterStats> {

  constructor(dataLoader: PosterStatsService,
              private yearState: YearStateService,
              loadMore: Observable<void>,
              sort: MatSort) {
    super(dataLoader, loadMore, sort);
  }


  protected  changedParameters(): Observable<{}>{
    return combineLatest(this.yearState.yearSubject,
      this.sorting,
      (year, sort) => {
      return {
        year: year,
        order_by: sort.active,
        order: sort.direction,
      }
    })
  }

}
