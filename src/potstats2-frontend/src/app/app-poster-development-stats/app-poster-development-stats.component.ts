import {Component, OnInit} from '@angular/core';
import {PosterDevelopmentService} from '../data/poster-development.service';
import {FormControl} from '@angular/forms';
import {catchError, debounceTime, filter, flatMap, map, shareReplay} from 'rxjs/operators';
import {EMPTY, merge, Observable} from 'rxjs';
import {PosterDevelopment, Stats, YearlyPosterStats} from '../data/types';

@Component({
  selector: 'app-app-poster-development-stats',
  templateUrl: './app-poster-development-stats.component.html',
  styleUrls: ['./app-poster-development-stats.component.css']
})
export class AppPosterDevelopmentStatsComponent implements OnInit {

  user = new FormControl('');
  uid = new FormControl('');

  selectableStats: Stats[] = [
    {
      label: 'Posts',
      value: 'post_count',
    },
    {
      label: 'Edits',
      value: 'edit_count',
    },
    {
      label: 'Threads',
      value: 'threads_created',
    },
    {
      label: 'Zitiert worden',
      value: 'quoted_count',
    },
    {
      label: 'Zitate',
      value: 'quotes_count',
    },
    {
      label: 'Durchschnittliche Postlänge',
      value: 'avg_post_length',
    },
  ];

  dataSource: Observable<YearlyPosterStats[]>;

  activeUser: Observable<string>;

  constructor(private posterDevelopmentService: PosterDevelopmentService) {
  }

  ngOnInit() {
    const fullResponse = merge(
      this.user.valueChanges.pipe(
        filter((value: string) => value.length > 0),
        debounceTime(500),
        flatMap(value =>
          this.posterDevelopmentService.getByUsername(value).pipe(
            catchError(() => EMPTY)
          ))
      ),
      this.uid.valueChanges.pipe(
        filter((value: string) => value.length > 0),
        debounceTime(500),
        flatMap(value =>
          this.posterDevelopmentService.getByUID(value).pipe(
            catchError(() => EMPTY)
          ))
      ),
    );

    this.dataSource = fullResponse.pipe(
      map((response: PosterDevelopment) => response.years),
      shareReplay()
    );
    this.activeUser = fullResponse.pipe(
      map((response: PosterDevelopment) => response.user.name)
    );
  }

}
