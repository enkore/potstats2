import { Component, OnInit} from '@angular/core';
import {YearStatsService} from "../data/year-stats.service";
import {AppYearStatsDataSource} from "./app-year-stats-data-source";

@Component({
  selector: 'app-year-stats',
  templateUrl: './app-year-stats.component.html',
  styleUrls: ['./app-year-stats.component.css']
})
export class AppYearStatsComponent implements OnInit {
  dataSource: AppYearStatsDataSource;

  displayedColumns = ['year', 'post_count', 'edit_count', 'avg_post_length', 'threads_created'];

  constructor(private service: YearStatsService) {}
  ngOnInit() {
    this.dataSource = new AppYearStatsDataSource(this.service);
  }

}
