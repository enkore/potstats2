import { Injectable } from '@angular/core';
import {DataModule} from "./data.module";
import {BaseDataService} from "../base-data-service";
import {BoardStats} from "./types";
import {environment} from "../../environments/environment";
import {HttpClient} from "@angular/common/http";

@Injectable({
  providedIn: DataModule
})
export class BoardsService extends BaseDataService<BoardStats> {

  protected uri = environment.backend + '/api/boards';

  constructor(protected http: HttpClient) { super() }
}
