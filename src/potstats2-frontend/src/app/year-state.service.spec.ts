import { TestBed, inject } from '@angular/core/testing';

import { YearStateService } from './year-state.service';

describe('YearStateService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [YearStateService]
    });
  });

  it('should be created', inject([YearStateService], (service: YearStateService) => {
    expect(service).toBeTruthy();
  }));
});
