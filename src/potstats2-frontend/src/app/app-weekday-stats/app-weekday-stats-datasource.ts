import { Observable} from 'rxjs';
import {WeekdayStats} from '../data/types';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {BaseDataSource} from '../base-datasource';
import {WeekdayStatsService} from '../data/weekday-stats.service';
import {map} from 'rxjs/operators';

export class AppWeekdayStatsDatasource extends BaseDataSource<WeekdayStats> {

  constructor(dataLoader: WeekdayStatsService,
              private stateService: GlobalFilterStateService) {
    super(dataLoader);
  }


  protected  changedParameters(): Observable<{}> {
    return this.stateService.state;
  }

}
