import {BrowserModule} from '@angular/platform-browser';
import {NgModule} from '@angular/core';

import {AppComponent} from './app.component';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {LayoutModule} from '@angular/cdk/layout';
import {
  MatButtonModule,
  MatCardModule,
  MatIconModule,
  MatListModule,
  MatSelectModule,
  MatSidenavModule,
  MatSortModule,
  MatTableModule,
  MatToolbarModule
} from '@angular/material';
import {AppNavComponent} from './app-nav/app-nav.component';
import {ImpressComponent} from './impress/impress.component';
import {PrivacyComponent} from './privacy/privacy.component';
import {RouterModule, Routes} from '@angular/router';
import {AppPosterstatsComponent} from './app-poster-stats/app-posterstats.component';
import {DataModule} from './data/data.module';
import {InfiniteScrollModule} from "ngx-infinite-scroll";
import {NgxChartsModule} from '@swimlane/ngx-charts';
import {AppYearStatsComponent} from './app-year-stats/app-year-stats.component';
import {AppWeekdayStatsComponent} from './app-weekday-stats/app-weekday-stats.component';
import {WeekdayPipe} from './weekday.pipe';
import {AppBoardStatsComponent} from './app-board-stats/app-board-stats.component';
import {FlexModule} from "@angular/flex-layout";
import {AppBarGraphComponent} from './app-bar-graph/app-bar-graph.component';
import {NoopPipe} from './noop.pipe';
import {AppDailyStatsComponent} from './app-daily-stats/app-daily-stats.component';


const routes: Routes = [
  { path: 'userstats', component: AppPosterstatsComponent},
  { path: 'year-to-year-stats', component: AppYearStatsComponent},
  { path: 'weekday-stats', component: AppWeekdayStatsComponent},
  {path: 'daily-stats', component: AppDailyStatsComponent},
  { path: 'board-stats', component: AppBoardStatsComponent},
  { path: 'impress', component: ImpressComponent },
  { path: 'privacy', component: PrivacyComponent }
];
@NgModule({
  declarations: [
    AppComponent,
    AppNavComponent,
    ImpressComponent,
    PrivacyComponent,
    AppPosterstatsComponent,
    AppYearStatsComponent,
    AppWeekdayStatsComponent,
    WeekdayPipe,
    AppBoardStatsComponent,
    AppBarGraphComponent,
    NoopPipe,
    AppDailyStatsComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    InfiniteScrollModule,
    LayoutModule,
    NgxChartsModule,
    MatToolbarModule,
    MatButtonModule,
    MatSidenavModule,
    MatIconModule,
    MatListModule,
    MatSelectModule,
    MatCardModule,
    FlexModule,
    RouterModule.forRoot(routes),
    MatTableModule,
    MatSortModule,
    DataModule,
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
