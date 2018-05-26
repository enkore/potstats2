
import {HttpClient} from '@angular/common/http';
import {map} from 'rxjs/operators';
import {Observable} from "rxjs/internal/Observable";
import {environment} from "../environments/environment";
import {isObject} from "util";

export class RowResponse<T> {
  rows: T[];
  next: string;
}

export abstract class BaseDataService<T> {

  protected abstract uri: string;
  protected abstract http: HttpClient;

  private nextPage: string;

  private prevPages = [];

  execute(params: {}): Observable<T[]> {
    for (let k in params) {
      if (params[k] === null || params[k] === '' || params[k] === undefined) {
        delete params[k];
      }
    }
    return this.http.get<RowResponse<T>>(this.uri, {params: params}).pipe(
      map(response => {
        this.prevPages.push(params);
        this.nextPage = response.next;
        return response.rows;
      })
    );
  }
  next(): Observable<T[]> {
    return this.http.get<RowResponse<T>>(environment.backend + this.nextPage).pipe(
      map(response => {
        this.prevPages.push(this.nextPage);
        this.nextPage = response.next;
        return response.rows;
      })
    );
  }

  previous(): Observable<T[]> {
    const params = this.prevPages.pop();
    let request: Observable<RowResponse<T>>;
    if (isObject(params)) {
      request = this.http.get<RowResponse<T>>(this.uri, {params: params});
    } else {
      request = this.http.get<RowResponse<T>>(environment.backend + params);
    }
    return request.pipe(
      map(response => {
        this.nextPage = response.next;
        return response.rows;
      })
    );

  }

}
