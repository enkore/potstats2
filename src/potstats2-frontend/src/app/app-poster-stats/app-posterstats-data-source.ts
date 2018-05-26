import {MatPaginator, MatSort} from '@angular/material';
import {
  concat,
  distinctUntilChanged, filter,
  flatMap,
  map,
  takeWhile
} from 'rxjs/operators';
import { Observable, combineLatest, of, merge  } from 'rxjs';
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
    this.paginator.length = 9000;
    const paginator: Observable<PosterStats[]> = this.paginator.page.pipe(
      distinctUntilChanged((eventA, eventB) => eventA === eventB),
      takeWhile(() => this.connected),
      flatMap((event) => {
        if (event.pageIndex > event.previousPageIndex) {
          return this.posterstatsService.next()
        } else {
          return this.posterstatsService.previous();
        }
      })
    );
    const unpaginatedStream: Observable<PosterStats[]> = combineLatest(this.yearState.yearSubject,
      of(true).pipe( concat(this.sort.sortChange.pipe(map(() => true)))),
      of(this.paginator.pageSize).pipe( concat(this.paginator.page.pipe(
        filter(pageEvent => pageEvent.pageIndex == pageEvent.previousPageIndex),
        map(pageEvent => pageEvent.pageSize),
        distinctUntilChanged()
      ))),
      (year, sort, pageSize) => {
      return {
        year: year,
        order_by: this.sort.active,
        order: this.sort.direction,
        limit: pageSize,
      }
    }).pipe(
      takeWhile(() => this.connected),
      flatMap(params => this.posterstatsService.execute(params))
    );
    return merge(paginator, unpaginatedStream);
  }

}
