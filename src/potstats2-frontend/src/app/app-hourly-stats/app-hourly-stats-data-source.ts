import {Observable} from 'rxjs';
import {HourlyStats} from '../data/types';
import {BaseDataSource} from "../base-datasource";
import {GlobalFilterStateService} from "../global-filter-state.service";
import {HourlyStatsService} from "../data/hourly-stats.service";

export class AppHourlyStatsDataSource extends BaseDataSource<HourlyStats> {

  constructor(dataLoader: HourlyStatsService, private stateService: GlobalFilterStateService) {
    super(dataLoader);
  }


  protected changedParameters(): Observable<{}> {
    return this.stateService.state;
  }

}
