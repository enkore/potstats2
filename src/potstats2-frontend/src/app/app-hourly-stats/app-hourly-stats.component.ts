import {Component, OnInit} from '@angular/core';
import {HourlyStatsService} from "../data/hourly-stats.service";
import {GlobalFilterStateService} from "../global-filter-state.service";
import {AppHourlyStatsDataSource} from "./app-hourly-stats-data-source";
import {Observable} from "rxjs/internal/Observable";
import {MultiSeriesStat} from "../data/types";

@Component({
  selector: 'app-app-hourly-stats',
  templateUrl: './app-hourly-stats.component.html',
  styleUrls: ['./app-hourly-stats.component.css']
})
export class AppHourlyStatsComponent implements OnInit {

  statsSource: Observable<MultiSeriesStat[]>;
  selectedValue = 'post_count';

  constructor(private service: HourlyStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    const dataSource = new AppHourlyStatsDataSource(this.service, this.stateService);
  }
}

