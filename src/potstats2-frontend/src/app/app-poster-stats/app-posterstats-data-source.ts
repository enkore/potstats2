import { MatPaginator, MatSort } from '@angular/material';
import {concat, flatMap, map, takeWhile} from 'rxjs/operators';
import { Observable, combineLatest, of  } from 'rxjs';
import {PosterStats} from '../data/types';
import {PosterStatsService} from '../data/poster-stats.service';
import {YearStateService} from "../year-state.service";
import {BaseDataSource} from "../base-datasource";

/**
 * Data source for the AppUserstats view. This class should
 * encapsulate all logic for fetching and manipulating the displayed data
 * (including sorting, pagination, and filtering).
 */
export class AppPosterstatsDataSource extends BaseDataSource<PosterStats> {

  constructor(private posterstatsService: PosterStatsService, private yearState: YearStateService,
              paginator: MatPaginator, sort: MatSort) {
    super(paginator, sort);
  }
  protected  connectData(): Observable<PosterStats[]>{
    return combineLatest(this.yearState.yearSubject, of(true).pipe(concat(this.sort.sortChange.pipe(map(() => true)))),  (year, _) => {
      return {
        year: year,
        order_by: this.sort.active,
        order: this.sort.direction,
      }
    }).pipe(
      takeWhile(() => this.connected),
      flatMap(params => this.posterstatsService.execute(params))
    )
  }

}
