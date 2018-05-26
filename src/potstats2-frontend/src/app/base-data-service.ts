
import {HttpClient} from '@angular/common/http';
import {map} from 'rxjs/operators';

export class RowResponse<T> {
  rows: T[];
}

export abstract class BaseDataService<T> {

  protected abstract uri: string;
  protected abstract http: HttpClient;

  execute(params: {}) {
    for (let k in params) {
      if (params[k] === null || params[k] === '' || params[k] === undefined) {
        delete params[k];
      }
    }
    return this.http.get<RowResponse<T>>(this.uri, {params: params}).pipe(
      map(response => response.rows)
    );
  }
}
