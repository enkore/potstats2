import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { LayoutModule } from '@angular/cdk/layout';
import {
  MatToolbarModule, MatButtonModule, MatSidenavModule, MatIconModule,
  MatListModule, MatTableModule, MatPaginatorModule, MatSortModule, MatSelectModule
} from '@angular/material';
import { AppNavComponent } from './app-nav/app-nav.component';
import { ImpressComponent } from './impress/impress.component';
import { PrivacyComponent } from './privacy/privacy.component';
import {RouterModule, Routes} from '@angular/router';
import { AppPosterstatsComponent } from './app-poster-stats/app-posterstats.component';
import { DataModule } from './data/data.module';


const routes: Routes = [
  { path: 'userstats', component: AppPosterstatsComponent},
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
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    LayoutModule,
    MatToolbarModule,
    MatButtonModule,
    MatSidenavModule,
    MatIconModule,
    MatListModule,
    MatSelectModule,
    RouterModule.forRoot(routes),
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    DataModule,
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
