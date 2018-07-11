import {Component, OnInit, ViewChild} from '@angular/core';
import {DailyStatsService} from '../data/daily-stats.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Observable} from 'rxjs/internal/Observable';
import {SeriesStats, Stats} from '../data/types';
import {AppDailyStatsDataSource} from './app-daily-stats-data-source';
import {MatSelect} from '@angular/material';
import {map} from 'rxjs/operators';
import {concat, of} from 'rxjs';

@Component({
  selector: 'app-app-hourly-stats',
  templateUrl: './app-daily-stats.component.html',
  styleUrls: ['./app-daily-stats.component.css']
})
export class AppDailyStatsComponent implements OnInit {
  @ViewChild(MatSelect) statsSelect: MatSelect;

  statsSource: Observable<SeriesStats[]>;

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
      label: 'Threads erstellt',
      value: 'threads_created',
    },
  ];

  selectedStats = this.selectableStats[0];

  defaultYear = 2018;
  activeYear: Observable<number>;

  constructor(private service: DailyStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    const statSelect = concat(of(this.selectableStats[0]), <Observable<Stats>>this.statsSelect.valueChange);
    this.activeYear = this.stateService.state.pipe(
      map(state => {
        if (state.year) {
          return state.year;
        } else {
          this.stateService.setYear(this.defaultYear);
          return this.defaultYear;
        }
      })
    );
    const dataSource = new AppDailyStatsDataSource(this.service, this.stateService, statSelect);
    this.statsSource = dataSource.connect();
  }
}

