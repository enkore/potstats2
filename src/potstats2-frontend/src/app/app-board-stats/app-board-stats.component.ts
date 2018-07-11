import {Component, OnInit} from '@angular/core';
import {AppBoardStatsDataSource} from './app-board-stats-data-source';
import {BoardsService} from '../data/boards.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Stats} from '../data/types';

@Component({
  selector: 'app-board-stats',
  templateUrl: './app-board-stats.component.html',
  styleUrls: ['./app-board-stats.component.css']
})
export class AppBoardStatsComponent implements OnInit {
  dataSource: AppBoardStatsDataSource;

  selectableStats: Stats[] = [
    {
      label: 'Posts',
      value: 'post_count',
    },
    {
      label: 'Threads',
      value: 'thread_count',
    },
  ];
  displayedColumns = ['name'].concat(...this.selectableStats.map(stats => stats.value));

  constructor(private service: BoardsService, private yearState: GlobalFilterStateService) {}
  ngOnInit() {
    this.dataSource = new AppBoardStatsDataSource(this.service, this.yearState);
  }
}
