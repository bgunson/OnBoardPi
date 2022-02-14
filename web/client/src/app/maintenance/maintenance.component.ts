import { CollectionViewer, DataSource } from '@angular/cdk/collections';
import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';
import { ActionService } from 'src/app/shared/services/action.service';
import { DisplayService } from 'src/app/shared/services/display.service';
import { RecordFormComponent } from './record-form/record-form.component';
import { MaintenanceRecord } from './maintenance.model';
import { MaintenanceService } from './maintenance.service';

@Component({
  selector: 'app-maintenance',
  templateUrl: './maintenance.component.html',
  styleUrls: ['./maintenance.component.scss']
})
export class MaintenanceComponent implements OnInit, OnDestroy {

  @ViewChild(MatSort) sort: MatSort;

  initialLoad$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  dataSource = new MatTableDataSource<MaintenanceRecord>();
  displayedColumns: string[] = ['date', 'description', 'odometer', 'notes', 'action'];

  subscriptions: Subscription = new Subscription();

  constructor(
    private maintenanceService: MaintenanceService, 
    private action: ActionService,
    private dialog: MatDialog,
    public display: DisplayService
  ) { }

  applyFilter(value: string) {
    const filterValue = value.toLowerCase().trim();
    this.dataSource.filter = filterValue;
  }

  edit(record: MaintenanceRecord) {
    this.dialog.open(RecordFormComponent, {
      data: {
        record: {...record}
      }
    });
  }

  delete(record: MaintenanceRecord) {
    this.maintenanceService.deleteRecord(record);
  }

  ngOnInit(): void {
    this.action.setAction('post_add');
    this.subscriptions.add(this.action.actionClick.subscribe(() => this.dialog.open(RecordFormComponent)));
    this.subscriptions.add(this.maintenanceService.getRecords().subscribe(records => {
      this.initialLoad$.next(true);
      this.dataSource.data = records;
      this.dataSource.sort = this.sort;
    }));
  }

  ngOnDestroy(): void {
      this.subscriptions.unsubscribe();
  }

}

export class MaintenanceDataSource extends DataSource<MaintenanceRecord> {

  private _dataStream: Observable<MaintenanceRecord[]>;

  constructor(initialData: Observable<MaintenanceRecord[]>) {
    super();
    this._dataStream = initialData;
  }

  connect(): Observable<MaintenanceRecord[]> {
    return this._dataStream;
  }

  disconnect(collectionViewer: CollectionViewer): void {
      
  }

}
