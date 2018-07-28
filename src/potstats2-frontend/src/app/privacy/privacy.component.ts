import {Component, OnInit} from '@angular/core';
import {GlobalFilterStateService} from '../global-filter-state.service';
import {ActivatedRoute, Router} from '@angular/router';
import {FilterAwareComponent} from '../filter-aware-component';
import {ContactInfoService} from "../data/contact-info.service";
import {ContactInfo} from "../data/types";

@Component({
  selector: 'app-privacy',
  templateUrl: './privacy.component.html',
  styleUrls: ['./privacy.component.css']
})
export class PrivacyComponent extends FilterAwareComponent implements OnInit {

  contactInfo: ContactInfo;

  constructor(stateService: GlobalFilterStateService,
              activatedRoute: ActivatedRoute,
              private contactInfoService: ContactInfoService,
              router: Router) {
    super(router, stateService, activatedRoute);
  }

  ngOnInit() {
    this.onInit();
    this.contactInfoService.execute().subscribe(c => this.contactInfo = c)
  }
}
