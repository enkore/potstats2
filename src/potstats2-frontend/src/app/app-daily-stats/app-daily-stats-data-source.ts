import {combineLatest, Observable} from 'rxjs';
import {SeriesStats, Stats} from '../data/types';
import {GlobalFilterStateService} from "../global-filter-state.service";
import {DailyStatsService} from "../data/daily-stats.service";
import {flatMap, map} from "rxjs/operators";

export class AppDailyStatsDataSource {

  constructor(private dataLoader: DailyStatsService,
              private stateService: GlobalFilterStateService,
              private selectedStat: Observable<Stats>,
  ) {
  }

  connect(): Observable<SeriesStats[]> {
    return this.changedParameters().pipe(
      flatMap(params => this.dataLoader.execute(params).pipe(
        map(series => series.series)))
    );
  }

  private changedParameters(): Observable<{}> {
    return combineLatest(this.stateService.state.pipe(
      map(state => {
          if (state.year) {
            return state;
          } else {
            const newstate = state;
            newstate.year = 2018;
            return newstate;
          }
        }
      ),
      ), this.selectedStat,
      (state, selected) => {
        return {
          ...state,
          statistic: selected.value,
        }
      });
  }

}
