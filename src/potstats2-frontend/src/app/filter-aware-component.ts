import {ActivatedRoute, Router} from '@angular/router';
import {GlobalFilterStateService} from './global-filter-state.service';

export class FilterAwareComponent {

  constructor(private _router: Router,
              private _stateService: GlobalFilterStateService,
              private _activatedRoute: ActivatedRoute,
  ) {}

  onInit() {
    const params = this._activatedRoute.snapshot.paramMap;
    const year = params.get('year');
    const bid = params.get('bid');
    this._stateService.setBoth(year, bid);
    const path = this._activatedRoute.snapshot.url[0].path;
    this._stateService.state.subscribe(state => {
      this._router.navigate([path, {year : state.year, bid : state.bid}]);
    });
  }
}
