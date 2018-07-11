import { Observable} from 'rxjs';
import {BoardStats} from '../data/types';
import {BaseDataSource} from '../base-datasource';
import {BoardsService} from '../data/boards.service';
import {GlobalFilterStateService} from '../global-filter-state.service';

export class AppBoardStatsDataSource extends BaseDataSource<BoardStats> {

  constructor(dataLoader: BoardsService,
              private stateService: GlobalFilterStateService) {
    super(dataLoader);
  }


  protected  changedParameters(): Observable<{}> {
    return this.stateService.state;
  }

}

