import {Injectable} from '@angular/core';
import {DataModule} from './data.module';
import {HttpClient} from '@angular/common/http';
import {PosterDevelopment, PosterDevelopmentResponse} from './types';
import {environment} from '../../environments/environment';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

@Injectable({
  providedIn: DataModule,
})
export class PosterDevelopmentService {

  protected uri = environment.backend + '/api/poster-development';

  private transformation =
    map((response: PosterDevelopmentResponse) => {
      return {
        user: response.user,
        years: Object.values(response.years),
      };
    });

  constructor(protected http: HttpClient) { }

  getByUsername(user: string): Observable<PosterDevelopment> {
    return this.http.get<PosterDevelopmentResponse>(this.uri, { params: { user: user }}).pipe(
      this.transformation
    );
  }

  getByUID(uid: string): Observable<PosterDevelopment> {
    return this.http.get<PosterDevelopmentResponse>(this.uri, { params: { uid: uid }}).pipe(
      this.transformation
    );
  }
}
