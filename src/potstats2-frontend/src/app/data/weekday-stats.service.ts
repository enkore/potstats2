import { Injectable } from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient} from '@angular/common/http';
import {WeekdayStats} from './types';
import {environment} from '../../environments/environment';
import {BaseDataService} from '../base-data-service';

@Injectable({
  providedIn: DataModule,
})
export class WeekdayStatsService extends BaseDataService<WeekdayStats> {

  protected uri = environment.backend + '/api/weekday-stats';

  constructor(protected http: HttpClient) { super(); }
}

