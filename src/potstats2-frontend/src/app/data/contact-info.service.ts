import {Injectable} from '@angular/core';
import {HttpClient} from "@angular/common/http";
import {Observable} from "rxjs/internal/Observable";
import {ContactInfo} from "./types";
import {environment} from "../../environments/environment";

@Injectable({
  providedIn: 'root'
})
export class ContactInfoService {

  private uri = environment.backend + '/api/imprint';

  constructor(private http: HttpClient) {
  }

  execute(): Observable<ContactInfo> {
    return this.http.get<ContactInfo>(this.uri)
  }
}
