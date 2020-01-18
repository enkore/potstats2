import {BrowserModule} from '@angular/platform-browser';
import {LOCALE_ID, NgModule} from '@angular/core';

import {AppComponent} from './app.component';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {LayoutModule} from '@angular/cdk/layout';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';
import {AppNavComponent} from './app-nav/app-nav.component';
import {ImprintComponent} from './imprint/imprint.component';
import {PrivacyComponent} from './privacy/privacy.component';
import {RouterModule, Routes} from '@angular/router';
import {AppPosterstatsComponent} from './app-poster-stats/app-posterstats.component';
import {DataModule} from './data/data.module';
import {InfiniteScrollModule} from 'ngx-infinite-scroll';
import {NgxChartsModule} from '@swimlane/ngx-charts';
import {AppYearStatsComponent} from './app-year-stats/app-year-stats.component';
import {AppWeekdayStatsComponent} from './app-weekday-stats/app-weekday-stats.component';
import {WeekdayPipe} from './weekday.pipe';
import {AppBoardStatsComponent} from './app-board-stats/app-board-stats.component';
import {FlexModule} from '@angular/flex-layout';
import {AppBarGraphComponent} from './app-bar-graph/app-bar-graph.component';
import {NoopPipe} from './noop.pipe';
import {AppDailyStatsComponent} from './app-daily-stats/app-daily-stats.component';

import {registerLocaleData} from '@angular/common';
import localeDe from '@angular/common/locales/de';
import { AppPosterDevelopmentStatsComponent } from './app-poster-development-stats/app-poster-development-stats.component';
import {ReactiveFormsModule} from '@angular/forms';
import {MatInputModule} from '@angular/material';

registerLocaleData(localeDe, 'de');

const routes: Routes = [
  { path: '', redirectTo: '/userstats', pathMatch: 'full' },
  { path: 'userstats', component: AppPosterstatsComponent},
  { path: 'year-to-year-stats', component: AppYearStatsComponent},
  { path: 'weekday-stats', component: AppWeekdayStatsComponent},
  {path: 'daily-stats', component: AppDailyStatsComponent},
  { path: 'board-stats', component: AppBoardStatsComponent},
  { path: 'poster-dev-stats', component: AppPosterDevelopmentStatsComponent},
  { path: 'imprint', component: ImprintComponent },
  { path: 'privacy', component: PrivacyComponent }
];
@NgModule({
  declarations: [
    AppComponent,
    AppNavComponent,
    ImprintComponent,
    PrivacyComponent,
    AppPosterstatsComponent,
    AppYearStatsComponent,
    AppWeekdayStatsComponent,
    WeekdayPipe,
    AppBoardStatsComponent,
    AppBarGraphComponent,
    NoopPipe,
    AppDailyStatsComponent,
    AppPosterDevelopmentStatsComponent,
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
    MatInputModule,
    FlexModule,
    RouterModule.forRoot(routes),
    MatTableModule,
    MatSortModule,
    DataModule,
    ReactiveFormsModule,
  ],
  providers: [{provide: LOCALE_ID, useValue: 'de'}],
  bootstrap: [AppComponent]
})
export class AppModule { }
