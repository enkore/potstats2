import { Observable} from 'rxjs';
import {YearStats} from '../data/types';
import {BaseDataSource} from "../base-datasource";
import {YearStatsService} from "../data/year-stats.service";
import {of} from "rxjs/internal/observable/of";

export class AppYearStatsDataSource extends BaseDataSource<YearStats> {

  constructor(dataLoader: YearStatsService) {
    super(dataLoader);
  }


  protected  changedParameters(): Observable<{}> {
    return of({});
  }

}
