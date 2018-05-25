import { Injectable } from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient} from '@angular/common/http';
import {PosterStatsResponse} from './types';
import {environment} from '../../environments/environment';
import {map} from 'rxjs/operators';

@Injectable({
  providedIn: DataModule,
})
export class PosterStatsService {

  uri = environment.backend + '/poster-stats';

  constructor(private http: HttpClient) { }
  execute() {
    return this.http.get<PosterStatsResponse>(this.uri).pipe(
      map(response => response.rows)
    );
  }
}
