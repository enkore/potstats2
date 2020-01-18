import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { AppPosterDevelopmentStatsComponent } from './app-poster-development-stats.component';

describe('AppPosterDevelopmentStatsComponent', () => {
  let component: AppPosterDevelopmentStatsComponent;
  let fixture: ComponentFixture<AppPosterDevelopmentStatsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ AppPosterDevelopmentStatsComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(AppPosterDevelopmentStatsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
