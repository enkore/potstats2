import { DataSource } from '@angular/cdk/collections';
import { MatPaginator, MatSort } from '@angular/material';
import { map } from 'rxjs/operators';
import { Observable, merge } from 'rxjs';
import {PosterStats} from '../data/types';
import {PosterStatsService} from '../data/poster-stats.service';
import {YearStateService} from "../year-state.service";
import {Subject} from "rxjs/internal/Subject";

/**
 * Data source for the AppUserstats view. This class should
 * encapsulate all logic for fetching and manipulating the displayed data
 * (including sorting, pagination, and filtering).
 */
export class AppPosterstatsDataSource extends DataSource<PosterStats> {

  data: PosterStats[] = [];
  constructor(private posterstatsService: PosterStatsService, private yearState: YearStateService,
              private paginator: MatPaginator, private sort: MatSort) {
    super();
  }

  /**
   * Connect this data source to the table. The table will only update when
   * the returned stream emits new items.
   * @returns A stream of the items to be rendered.
   */
  connect(): Observable<PosterStats[]> {
    const dataSubject: Subject<boolean> = new Subject();
    this.yearState.yearSubject.subscribe(year => {
        this.posterstatsService.execute(year).subscribe(data => {
            this.data = data;
            dataSubject.next(true);
          }
        )
      }
    );

    // Combine everything that affects the rendered data into one update
    // stream for the data-table to consume.
    const dataMutations = [
      dataSubject,
      this.paginator.page,
      this.sort.sortChange
    ];

    return merge(...dataMutations).pipe(map(() => {
      this.paginator.length = this.data.length;
      return this.getPagedData(this.getSortedData([...this.data]));
    }));
  }

  /**
   *  Called when the table is being destroyed. Use this function, to clean up
   * any open connections or free any held resources that were set up during connect.
   */
  disconnect() {}

  /**
   * Paginate the data (client-side). If you're using server-side pagination,
   * this would be replaced by requesting the appropriate data from the server.
   */
  private getPagedData(data: PosterStats[]) {
    const startIndex = this.paginator.pageIndex * this.paginator.pageSize;
    return data.splice(startIndex, this.paginator.pageSize);
  }

  /**
   * Sort the data (client-side). If you're using server-side sorting,
   * this would be replaced by requesting the appropriate data from the server.
   */
  private getSortedData(data: PosterStats[]) {
    if (!this.sort.active || this.sort.direction === '') {
      return data;
    }

    return data.sort((a, b) => {
      const isAsc = this.sort.direction === 'asc';
      if (this.sort.active === 'User') {
          return compare(a.User.name, b.User.name, isAsc);
      } else {
        return compare(a[this.sort.active], b[this.sort.active], isAsc);
      }
    });
  }
}

/** Simple sort comparator for example ID/Name columns (for client-side sorting). */
function compare(a, b, isAsc) {
  return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
}
