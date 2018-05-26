
import {HttpClient} from '@angular/common/http';
import {map} from 'rxjs/operators';
import {Observable} from "rxjs/internal/Observable";
import {environment} from "../environments/environment";
import {of} from "rxjs/internal/observable/of";

export class RowResponse<T> {
  rows: T[];
  next: string;
}

export abstract class BaseDataService<T> {

  protected abstract uri: string;
  protected abstract http: HttpClient;

  private nextPage: string = null;

  execute(params: {}): Observable<T[]> {
    for (let k in params) {
      if (params[k] === null || params[k] === '' || params[k] === undefined) {
        delete params[k];
      }
    }
    if (!params.hasOwnProperty('limit')) {
      params['limit'] = environment.default_limit;
    }
    return this.http.get<RowResponse<T>>(this.uri, {params: params}).pipe(
      map(response => {
        this.nextPage = response.next;
        return response.rows;
      })
    );
  }
  next(): Observable<T[]> {
    if (this.nextPage == null) {
      return of([]);
    }
    return this.http.get<RowResponse<T>>(environment.backend + this.nextPage).pipe(
      map(response => {
        const next: string = response.next;
        if (next.includes('following')) {
          this.nextPage = response.next;
        } else {
          this.nextPage = null;
        }
        console.log("next page", this.nextPage);
        return response.rows;
      })
    );
  }

}
