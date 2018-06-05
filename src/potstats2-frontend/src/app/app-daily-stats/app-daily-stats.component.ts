import {Component, OnInit, ViewChild} from '@angular/core';
import {DailyStatsService} from "../data/daily-stats.service";
import {GlobalFilterStateService} from "../global-filter-state.service";
import {Observable} from "rxjs/internal/Observable";
import {SeriesStats, Stats} from "../data/types";
import {AppDailyStatsDataSource} from "./app-daily-stats-data-source";
import {of} from "rxjs/internal/observable/of";
import {MatSelect} from "@angular/material";
import {concat, map} from "rxjs/operators";

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
  selectedYear = this.defaultYear;

  constructor(private service: DailyStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    const statSelect = of(this.selectableStats[0]).pipe(
      concat(<Observable<Stats>>this.statsSelect.valueChange)
    );
    const selectedYear = this.stateService.state.pipe(
      map(state => {
        if (state.year) {
          return state;
        } else {
          const newstate = state;
          newstate.year = this.defaultYear;
          this.selectedYear = newstate.year;
          return newstate;
        }
      })
    );
    const dataSource = new AppDailyStatsDataSource(this.service, this.stateService, statSelect);
    this.statsSource = dataSource.connect();
  }
}

