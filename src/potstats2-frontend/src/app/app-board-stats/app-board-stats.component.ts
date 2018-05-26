import { Component, OnInit} from '@angular/core';
import {AppBoardStatsDataSource} from "./app-board-stats-data-source";
import {BoardsService} from "../data/boards.service";
import {YearStateService} from "../year-state.service";

@Component({
  selector: 'app-board-stats',
  templateUrl: './app-board-stats.component.html',
  styleUrls: ['./app-board-stats.component.css']
})
export class AppBoardStatsComponent implements OnInit {
  dataSource: AppBoardStatsDataSource;

  displayedColumns = ['name', 'post_count', 'thread_count'];

  constructor(private service: BoardsService, private yearState: YearStateService) {}
  ngOnInit() {
    this.dataSource = new AppBoardStatsDataSource(this.service, this.yearState);
  }
}
