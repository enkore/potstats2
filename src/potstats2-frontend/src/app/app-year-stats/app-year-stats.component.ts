import {Component, OnInit} from '@angular/core';
import {YearStatsService} from '../data/year-stats.service';
import {AppYearStatsDataSource} from './app-year-stats-data-source';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Stats} from '../data/types';

@Component({
  selector: 'app-year-stats',
  templateUrl: './app-year-stats.component.html',
  styleUrls: ['./app-year-stats.component.css']
})
export class AppYearStatsComponent implements OnInit {
  dataSource: AppYearStatsDataSource;

  selectableStats: Stats[] = [
    {
      label: 'Aktive User',
      value: 'active_users',
    },
    {
      label: 'Posts',
      value: 'post_count',
    },
    {
      label: 'Edits',
      value: 'edit_count',
    },
    {
      label: 'Durchschnittliche Postlänge',
      value: 'avg_post_length',
    },
    {
      label: 'Threads',
      value: 'threads_created',
    },
  ];
  displayedColumns = ['year'].concat(...this.selectableStats.map(stats => stats.value));

  constructor(private service: YearStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    this.dataSource = new AppYearStatsDataSource(this.service, this.stateService);
  }

}
