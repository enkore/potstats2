import { Component, OnInit, ViewChild } from '@angular/core';
import { MatSort } from '@angular/material';
import { AppPosterstatsDataSource } from './app-posterstats-data-source';
import {PosterStatsService} from '../data/poster-stats.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Subject} from 'rxjs/internal/Subject';

@Component({
  selector: 'app-userstats',
  templateUrl: './app-posterstats.component.html',
  styleUrls: ['./app-posterstats.component.css']
})
export class AppPosterstatsComponent implements OnInit {
  @ViewChild(MatSort) sort: MatSort;
  dataSource: AppPosterstatsDataSource;

  loadMore = new Subject<void>();
  displayedColumns = ['name', 'post_count', 'edit_count', 'avg_post_length', 'threads_created', 'quoted_count', 'quotes_count'];

  constructor(private service: PosterStatsService, private stateService: GlobalFilterStateService) {}
  ngOnInit() {
    this.dataSource = new AppPosterstatsDataSource(
      this.service, this.stateService, this.loadMore, this.sort);
  }

  trackByUid(index, item) {
    return item.uid;
  }

  onScroll() {
    this.loadMore.next();
  }
}
