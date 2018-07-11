import { Observable} from 'rxjs';
import {YearStats} from '../data/types';
import {BaseDataSource} from '../base-datasource';
import {YearStatsService} from '../data/year-stats.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {map} from 'rxjs/operators';

export class AppYearStatsDataSource extends BaseDataSource<YearStats> {

  constructor(dataLoader: YearStatsService, private stateService: GlobalFilterStateService) {
    super(dataLoader);
  }


  protected  changedParameters(): Observable<{}> {
    return this.stateService.state.pipe(map(state => {
      return {
        bid: state.bid,
      };
    }));
  }

}
