import { Observable} from 'rxjs';
import {WeekdayStats} from '../data/types';
import {YearStateService} from "../year-state.service";
import {BaseDataSource} from "../base-datasource";
import {WeekdayStatsService} from "../data/weekday-stats.service";
import {map} from "rxjs/operators";

export class AppWeekdayStatsDatasource extends BaseDataSource<WeekdayStats> {

  constructor(dataLoader: WeekdayStatsService,
              private yearState: YearStateService) {
    super(dataLoader);
  }


  protected  changedParameters(): Observable<{}>{
    return this.yearState.yearSubject.pipe(
      map(year => {
        return { year: year }
      }
    ));
  }

}
