import { Component, OnInit, ViewChild } from '@angular/core';
import {Subject} from "rxjs/internal/Subject";
import {YearStatsService} from "../data/year-stats.service";
import {AppYearStatsDataSource} from "./app-year-stats-data-source";

@Component({
  selector: 'app-year-stats',
  templateUrl: './app-year-stats.component.html',
  styleUrls: ['./app-year-stats.component.css']
})
export class AppYearStatsComponent implements OnInit {
  dataSource: AppYearStatsDataSource;
  loadMore = new Subject<void>();

  displayedColumns = ['year', 'post_count', 'edit_count', 'avg_post_length', 'threads_created'];

  constructor(private service: YearStatsService) {}
  ngOnInit() {
    this.dataSource = new AppYearStatsDataSource(this.service, this.loadMore);
  }

  onScroll() {
    this.loadMore.next();
  }
}
