import { Component, OnInit} from '@angular/core';
import {AppWeekdayStatsDatasource} from "./app-weekday-stats-datasource";
import {WeekdayStatsService} from "../data/weekday-stats.service";
import {YearStateService} from "../year-state.service";

@Component({
  selector: 'app-weekday-stats',
  templateUrl: './app-weekday-stats.component.html',
  styleUrls: ['./app-weekday-stats.component.css']
})
export class AppWeekdayStatsComponent implements OnInit {
  dataSource: AppWeekdayStatsDatasource;

  displayedColumns = ['weekday', 'post_count', 'edit_count', 'avg_post_length', 'threads_created'];

  constructor(private service: WeekdayStatsService, private yearState: YearStateService) {}
  ngOnInit() {
    this.dataSource = new AppWeekdayStatsDatasource(this.service, this.yearState);
  }

}
