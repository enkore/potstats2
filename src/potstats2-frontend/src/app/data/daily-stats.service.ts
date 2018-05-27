import {Injectable} from '@angular/core';
import {DataModule} from "./data.module";
import {MultiSeriesStat} from "./types";
import {HttpClient} from "@angular/common/http";
import {environment} from "../../environments/environment";
import {Observable} from "rxjs/internal/Observable";

@Injectable({
  providedIn: DataModule
})
export class DailyStatsService {

  protected uri = environment.backend + '/api/daily-stats';

  constructor(protected http: HttpClient) {
  }

  execute(params: {}): Observable<MultiSeriesStat> {
    for (let k in params) {
      if (params[k] === null || params[k] === '' || params[k] === undefined) {
        delete params[k];
      }
    }
    return this.http.get<MultiSeriesStat>(this.uri, {params: params});
  }
}
