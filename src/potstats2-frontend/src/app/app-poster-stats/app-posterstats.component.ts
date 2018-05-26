import { Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator, MatSort } from '@angular/material';
import { AppPosterstatsDataSource } from './app-posterstats-data-source';
import {PosterStatsService} from '../data/poster-stats.service';
import {YearStateService} from "../year-state.service";
import {Subject} from "rxjs/internal/Subject";

@Component({
  selector: 'app-userstats',
  templateUrl: './app-posterstats.component.html',
  styleUrls: ['./app-posterstats.component.css']
})
export class AppPosterstatsComponent implements OnInit {
  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;
  dataSource: AppPosterstatsDataSource;

  loadMore = new Subject<void>();
  /** Columns displayed in the table. Columns IDs can be added, removed, or reordered. */
  displayedColumns = ['name', 'post_count', 'edit_count', 'avg_post_length', 'threads_created', 'quoted_count', 'quotes_count'];

  constructor(private service: PosterStatsService, private yearState: YearStateService) {}
  ngOnInit() {
    this.dataSource = new AppPosterstatsDataSource(
      this.service, this.yearState, this.loadMore, this.sort);
  }

  trackByUid(index, item) {
    return item.uid;
  }

  onScroll() {
    this.loadMore.next();
  }
}
