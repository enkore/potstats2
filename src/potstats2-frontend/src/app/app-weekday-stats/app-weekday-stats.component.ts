import { Component, OnInit} from '@angular/core';
import {AppWeekdayStatsDatasource} from "./app-weekday-stats-datasource";
import {WeekdayStatsService} from "../data/weekday-stats.service";
import {GlobalFilterStateService} from "../global-filter-state.service";

@Component({
  selector: 'app-weekday-stats',
  templateUrl: './app-weekday-stats.component.html',
  styleUrls: ['./app-weekday-stats.component.css']
})
export class AppWeekdayStatsComponent implements OnInit {
  dataSource: AppWeekdayStatsDatasource;

  displayedColumns = ['weekday', 'active_users', 'post_count', 'edit_count', 'avg_post_length', 'threads_created'];

  constructor(private service: WeekdayStatsService, private stateService: GlobalFilterStateService) {}
  ngOnInit() {
    this.dataSource = new AppWeekdayStatsDatasource(this.service, this.stateService);
  }

}
