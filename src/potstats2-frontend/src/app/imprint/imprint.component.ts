import { Component, OnInit } from '@angular/core';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';

@Component({
  selector: 'app-impressum',
  templateUrl: './imprint.component.html',
  styleUrls: ['./imprint.component.css']
})
export class ImprintComponent extends FilterAwareComponent implements OnInit {

  constructor(stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              router: Router) {
    super(router, stateService, activatedRoute);
  }

  ngOnInit() {
    this.onInit();
  }

}
