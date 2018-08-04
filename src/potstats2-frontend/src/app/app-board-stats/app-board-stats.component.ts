import {Component, OnInit} from '@angular/core';
import {AppBoardStatsDataSource} from './app-board-stats-data-source';
import {BoardsService} from '../data/boards.service';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {Stats} from '../data/types';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';

@Component({
  selector: 'app-board-stats',
  templateUrl: './app-board-stats.component.html',
  styleUrls: ['./app-board-stats.component.css']
})
export class AppBoardStatsComponent extends FilterAwareComponent implements OnInit {
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
  displayedColumns = ['row_index', 'name'].concat(...this.selectableStats.map(stats => stats.value));

  constructor(private service: BoardsService,
              private stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              router: Router) {
    super(router, stateService, activatedRoute);
  }
  ngOnInit() {
    this.onInit();
    this.dataSource = new AppBoardStatsDataSource(this.service, this.stateService);
  }
}
