import {MatSort} from '@angular/material';
import { Observable, combineLatest } from 'rxjs';
import {PosterStats} from '../data/types';
import {PosterStatsService} from '../data/poster-stats.service';
import {GlobalFilterStateService} from "../global-filter-state.service";
import {BaseDataSource} from "../base-datasource";

export class AppPosterstatsDataSource extends BaseDataSource<PosterStats> {

  constructor(dataLoader: PosterStatsService,
              private stateService: GlobalFilterStateService,
              loadMore: Observable<void>,
              sort: MatSort) {
    super(dataLoader, loadMore, sort);
  }


  protected  changedParameters(): Observable<{}>{
    return combineLatest(this.stateService.state,
      this.sorting,
      (state, sort) => {
      return {
        ...state,
        order_by: sort.active,
        order: sort.direction,
      }
    })
  }

}
