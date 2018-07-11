import { Component, OnInit } from '@angular/core';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';

@Component({
  selector: 'app-privacy',
  templateUrl: './privacy.component.html',
  styleUrls: ['./privacy.component.css']
})
export class PrivacyComponent extends FilterAwareComponent implements OnInit {

  constructor(stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              router: Router) {
    super(router, stateService, activatedRoute);
  }

  ngOnInit() {
    this.onInit();
  }
}
