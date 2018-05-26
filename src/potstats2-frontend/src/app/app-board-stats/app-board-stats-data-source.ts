import { Observable} from 'rxjs';
import {BoardStats} from '../data/types';
import {BaseDataSource} from "../base-datasource";
import {map} from "rxjs/operators";
import {BoardsService} from "../data/boards.service";
import {YearStateService} from "../year-state.service";

export class AppBoardStatsDataSource extends BaseDataSource<BoardStats> {

  constructor(dataLoader: BoardsService,
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

