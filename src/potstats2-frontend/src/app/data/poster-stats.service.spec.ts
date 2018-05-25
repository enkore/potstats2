import { TestBed, inject } from '@angular/core/testing';

import { PosterStatsService } from './poster-stats.service';

describe('PosterStatsService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PosterStatsService]
    });
  });

  it('should be created', inject([PosterStatsService], (service: PosterStatsService) => {
    expect(service).toBeTruthy();
  }));
});
