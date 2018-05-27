import {Component, OnInit, ViewChild} from '@angular/core';
import {YearStatsService} from "../data/year-stats.service";
import {AppYearStatsDataSource} from "./app-year-stats-data-source";
import {GlobalFilterStateService} from "../global-filter-state.service";
import {Observable} from "rxjs/internal/Observable";
import {combineLatest, concat, map} from "rxjs/operators";
import {MatSelect} from "@angular/material";
import {of} from 'rxjs';
import {Stats} from "../data/types";

@Component({
  selector: 'app-year-stats',
  templateUrl: './app-year-stats.component.html',
  styleUrls: ['./app-year-stats.component.css']
})
export class AppYearStatsComponent implements OnInit {
  dataSource: AppYearStatsDataSource;
  chartData: Observable<{}[]>;
  @ViewChild(MatSelect) statsSelect: MatSelect;

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
  selectedStats = this.selectableStats[0];

  constructor(private service: YearStatsService, private stateService: GlobalFilterStateService) {
  }

  ngOnInit() {
    this.dataSource = new AppYearStatsDataSource(this.service, this.stateService);
    const chartDataSource = this.dataSource.connect();
    this.chartData = chartDataSource.pipe(
      combineLatest(of(this.selectableStats[0]).pipe(concat(<Observable<Stats>>this.statsSelect.valueChange)), (rows, selectedStats) => {
        return {
          rows: rows,
          selectedStats: selectedStats
        }
      }),
      map(state => {
        return state.rows.map(row => {
          return {
            name: row.year.toString(),
            value: row[(<any>state.selectedStats).value],
          }
        });
      })
    );
  }

}
