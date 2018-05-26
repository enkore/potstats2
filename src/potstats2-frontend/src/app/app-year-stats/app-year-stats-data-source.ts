import { Observable} from 'rxjs';
import {YearStats} from '../data/types';
import {BaseDataSource} from "../base-datasource";
import {map} from "rxjs/operators";
import {YearStatsService} from "../data/year-stats.service";

export class AppYearStatsDataSource extends BaseDataSource<YearStats> {

  constructor(dataLoader: YearStatsService,
              loadMore: Observable<void>) {
    super(dataLoader, loadMore);
  }


  protected  changedParameters(): Observable<{}>{
    return this.sorting.pipe(
      map(sort => {
        return {
          order_by: sort.active,
          order: sort.direction,
        }
      }));
  }

}
