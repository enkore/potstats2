import {Component, Input, OnInit, PipeTransform, ViewChild} from '@angular/core';
import {Stats} from "../data/types";
import {Observable} from "rxjs/internal/Observable";
import {combineLatest, concat, map} from "rxjs/operators";
import {of} from 'rxjs';
import {MatSelect} from "@angular/material";
import {NoopPipe} from "../noop.pipe";

@Component({
  selector: 'app-app-bar-graph',
  templateUrl: './app-bar-graph.component.html',
  styleUrls: ['./app-bar-graph.component.css']
})
export class AppBarGraphComponent implements OnInit {
  @ViewChild(MatSelect) statsSelect: MatSelect;

  @Input()
  selectableStats: Stats[];

  @Input()
  xLabel: string;

  @Input()
  xValue: string;

  @Input()
  dataSource: Observable<any>;

  @Input()
  pipe: PipeTransform = new NoopPipe();

  @Input()
  viewSize = [800, 500];

  chartData: Observable<{}[]>;

  selectedStats: Stats;

  ngOnInit() {
    this.selectedStats = this.selectableStats[0];
    this.chartData = this.dataSource.pipe(
      combineLatest(of(this.selectableStats[0]).pipe(concat(<Observable<Stats>>this.statsSelect.valueChange)), (rows, selectedStats) => {
        return {
          rows: rows,
          selectedStats: selectedStats
        }
      }),
      map(state => {
        return state.rows.map(row => {
          return {
            name: this.pipe.transform(row[this.xValue]).toString(),
            value: row[(<any>state.selectedStats).value],
          }
        });
      })
    );
  }

}
