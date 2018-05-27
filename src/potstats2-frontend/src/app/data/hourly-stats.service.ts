import {Injectable} from '@angular/core';
import {DataModule} from "./data.module";
import {BaseDataService} from "../base-data-service";
import {HourlyStats} from "./types";
import {HttpClient} from "@angular/common/http";
import {environment} from "../../environments/environment";

@Injectable({
  providedIn: DataModule
})
export class HourlyStatsService extends BaseDataService<HourlyStats> {

  protected uri = environment.backend + '/api/hourly-stats';

  constructor(protected http: HttpClient) {
    super()
  }
}
