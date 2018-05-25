
import { fakeAsync, ComponentFixture, TestBed } from '@angular/core/testing';

import { AppPosterstatsComponent } from './app-posterstats.component';

describe('AppPosterstatsComponent', () => {
  let component: AppPosterstatsComponent;
  let fixture: ComponentFixture<AppPosterstatsComponent>;

  beforeEach(fakeAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ AppPosterstatsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AppPosterstatsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }));

  it('should compile', () => {
    expect(component).toBeTruthy();
  });
});
