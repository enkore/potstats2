import { DataSource } from '@angular/cdk/collections';
import { MatPaginator, MatSort } from '@angular/material';
import { Observable} from 'rxjs';

export abstract class BaseDataSource<T> extends DataSource<T> {
  protected connected = false;

  protected constructor(private paginator: MatPaginator, protected sort: MatSort) {
    super();
  }

  protected abstract connectData(): Observable<T[]>

  /**
   * Connect this data source to the table. The table will only update when
   * the returned stream emits new items.
   * @returns A stream of the items to be rendered.
   */
  connect(): Observable<T[]> {
    this.connected = true;
    const dataSource = this.connectData();

    // TODO: pagination

    return dataSource;
  }

  /**
   *  Called when the table is being destroyed. Use this function, to clean up
   * any open connections or free any held resources that were set up during connect.
   */
  disconnect() {
    this.connected = false;
  }

  /**
   * Paginate the data (client-side). If you're using server-side pagination,
   * this would be replaced by requesting the appropriate data from the server.
   */
  private getPagedData(data: T[]) {
    const startIndex = this.paginator.pageIndex * this.paginator.pageSize;
    return data.splice(startIndex, this.paginator.pageSize);
  }

}

