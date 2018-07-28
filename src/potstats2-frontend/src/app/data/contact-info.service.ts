import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {Observable} from "rxjs/internal/Observable";
import {ContactInfo} from "./types";

@Injectable({
  providedIn: 'root'
})
export class ContactInfoService {

  private uri = 'http://potstats2.enkore.de/api/imprint'

  constructor(private http: HttpClient) {
  }

  execute(): Observable<ContactInfo> {
    return this.http.get<ContactInfo>(this.uri)
  }
}
