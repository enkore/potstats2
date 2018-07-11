import { Injectable } from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient} from '@angular/common/http';
import {YearStats} from './types';
import {environment} from '../../environments/environment';
import {BaseDataService} from '../base-data-service';

@Injectable({
  providedIn: DataModule,
})
export class YearStatsService  extends BaseDataService<YearStats> {

  protected uri = environment.backend + '/api/year-over-year-stats';

  constructor(protected http: HttpClient) { super(); }
}
