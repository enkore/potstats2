import { DataSource } from '@angular/cdk/collections';
import {MatSort, Sort} from '@angular/material';
import { Observable, merge } from 'rxjs';
import {BaseDataService} from './base-data-service';
import {concat, flatMap, map, takeWhile} from 'rxjs/operators';
import {of} from 'rxjs/internal/observable/of';

export abstract class BaseDataSource<T> extends DataSource<T> {
  protected connected = false;
  protected loadedData: T[] = [];

  protected sorting: Observable<Sort>;

  protected constructor(protected dataLoader: BaseDataService<T>,
                        private loadMore: Observable<void> = null, private sort: MatSort = null) {
    super();
    if (sort !== null) {
      this.sorting = of(this.sort).pipe(concat(<Observable<Sort>>this.sort.sortChange));
    }
  }

  protected abstract changedParameters(): Observable<{}>;

  /**
   * Connect this data source to the table. The table will only update when
   * the returned stream emits new items.
   * @returns A stream of the items to be rendered.
   */
  connect(): Observable<T[]> {
    this.connected = true;
    const freshLoader = this.changedParameters().pipe(
      flatMap(params => this.dataLoader.execute(params)),
      map(data => {
        this.loadedData = data;
        return data;
      })
    );
    if (this.loadMore != null) {
      const infiniteLoader: Observable<T[]> =
        this.loadMore.pipe(
          flatMap(() => this.dataLoader.next().pipe(
            map(data => {
              this.loadedData.push(...data);
              return this.loadedData;
            })
          ))
        );
      return merge(infiniteLoader, freshLoader).pipe(
        takeWhile(() => this.connected),
      );
    } else {
      return freshLoader.pipe(
        takeWhile(() => this.connected)
      );
    }
  }

  /**
   *  Called when the table is being destroyed. Use this function, to clean up
   * any open connections or free any held resources that were set up during connect.
   */
  disconnect() {
    this.connected = false;
  }

}

