import {Component, OnInit} from '@angular/core';
import {DailyStatsService} from "../data/daily-stats.service";
import {GlobalFilterStateService} from "../global-filter-state.service";
import {Observable} from "rxjs/internal/Observable";
import {SeriesStats} from "../data/types";
import {AppDailyStatsDataSource} from "./app-daily-stats-data-source";

@Component({
  selector: 'app-app-hourly-stats',
  templateUrl: './app-hourly-stats.component.html',
  styleUrls: ['./app-hourly-stats.component.css']
})
export class AppHourlyStatsComponent implements OnInit {

  statsSource: Observable<SeriesStats[]>;

  constructor(private service: DailyStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    const dataSource = new AppDailyStatsDataSource(this.service, this.stateService);
    this.statsSource = dataSource.connect();
  }
}

