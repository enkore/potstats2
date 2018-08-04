import {Component, OnInit} from '@angular/core';
import {YearStatsService} from '../data/year-stats.service';
import {AppYearStatsDataSource} from './app-year-stats-data-source';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Stats} from '../data/types';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';

@Component({
  selector: 'app-year-stats',
  templateUrl: './app-year-stats.component.html',
  styleUrls: ['./app-year-stats.component.css']
})
export class AppYearStatsComponent extends FilterAwareComponent implements OnInit {
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
  displayedColumns = ['row_index', 'year'].concat(...this.selectableStats.map(stats => stats.value));

  constructor(private service: YearStatsService,
              private stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              router: Router) {
    super(router, stateService, activatedRoute);
  }

  ngOnInit() {
    this.onInit();
    this.dataSource = new AppYearStatsDataSource(this.service, this.stateService);
  }

}
