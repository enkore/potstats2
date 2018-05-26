
import { fakeAsync, ComponentFixture, TestBed } from '@angular/core/testing';

import { AppWeekdayStatsComponent } from './app-weekday-stats.component';

describe('AppWeekdayStatsComponent', () => {
  let component: AppWeekdayStatsComponent;
  let fixture: ComponentFixture<AppWeekdayStatsComponent>;

  beforeEach(fakeAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ AppWeekdayStatsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AppWeekdayStatsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }));

  it('should compile', () => {
    expect(component).toBeTruthy();
  });
});
