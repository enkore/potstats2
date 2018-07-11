import { Injectable } from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient} from '@angular/common/http';
import {PosterStats} from './types';
import {environment} from '../../environments/environment';
import {BaseDataService} from '../base-data-service';

@Injectable({
  providedIn: DataModule,
})
export class PosterStatsService extends BaseDataService<PosterStats> {

  protected uri = environment.backend + '/api/poster-stats';

  constructor(protected http: HttpClient) { super(); }
}
