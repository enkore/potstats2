import {Component, OnInit} from '@angular/core';
import {AppWeekdayStatsDatasource} from './app-weekday-stats-datasource';
import {WeekdayStatsService} from '../data/weekday-stats.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Stats} from '../data/types';
import {WeekdayPipe} from '../weekday.pipe';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';

@Component({
  selector: 'app-weekday-stats',
  templateUrl: './app-weekday-stats.component.html',
  styleUrls: ['./app-weekday-stats.component.css']
})
export class AppWeekdayStatsComponent extends FilterAwareComponent implements OnInit {
  dataSource: AppWeekdayStatsDatasource;
  protected path = 'weekday-stats';

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
  displayedColumns = ['weekday'].concat(...this.selectableStats.map(stats => stats.value));
  pipe = new WeekdayPipe();

  constructor(private service: WeekdayStatsService,
              private stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              router: Router
              ) {
    super(router, stateService, activatedRoute);
  }
  ngOnInit() {
    this.onInit();
    this.dataSource = new AppWeekdayStatsDatasource(this.service, this.stateService);
  }

}
