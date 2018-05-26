import { Injectable } from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient, HttpParams} from '@angular/common/http';
import {PosterStatsResponse} from './types';
import {environment} from '../../environments/environment';
import {map} from 'rxjs/operators';

@Injectable({
  providedIn: DataModule,
})
export class PosterStatsService {

  uri = environment.backend + '/poster-stats';

  constructor(private http: HttpClient) { }
  execute(year: number | null) {
    const options = year ?
      { params: new HttpParams().set('year', year.toString()) } : {};
    return this.http.get<PosterStatsResponse>(this.uri, options).pipe(
      map(response => response.rows)
    );
  }
}
