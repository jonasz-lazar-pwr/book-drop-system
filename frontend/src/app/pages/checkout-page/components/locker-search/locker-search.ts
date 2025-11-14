import { Component, EventEmitter, Output, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormControl } from '@angular/forms';
import { CheckoutService } from '@services/checkout.service';
import {
  debounceTime,
  distinctUntilChanged,
  filter,
  switchMap,
  catchError,
  of,
} from 'rxjs';
import { LockerResponse } from '@models/checkout';

@Component({
  selector: 'app-locker-search',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './locker-search.html',
  styleUrls: ['./locker-search.scss'],
})
export class LockerSearch {
  private readonly checkout = inject(CheckoutService);
  private readonly cdr = inject(ChangeDetectorRef);

  @Output() lockerSearch = new EventEmitter<LockerResponse | string>();

  searchControl = new FormControl('');
  suggestions: LockerResponse[] = [];
  loading = false;

  constructor() {
    this.searchControl.valueChanges
      .pipe(
        debounceTime(500),
        distinctUntilChanged(),
        filter((query) => !!query && query.trim().length >= 2),
        switchMap((query) => {
          this.loading = true;
          const value = query!.trim();
          const filters: Record<string, string> = {};

          const postalCodeRegex = /^\d{2}-\d{3}$/;
          const postalCodeNoDashRegex = /^\d{5}$/;
          const partialPostalRegex = /^\d{2,}$/;

          if (
            postalCodeRegex.test(value) ||
            postalCodeNoDashRegex.test(value) ||
            partialPostalRegex.test(value)
          ) {
            filters['postal_code'] = value;
          } else {
            filters['city'] = value;
          }

          return this.checkout.getLockers(filters).pipe(
            catchError(() => {
              this.loading = false;
              this.cdr.detectChanges();
              return of([]);
            })
          );
        })
      )
      .subscribe((res) => {
        this.suggestions = res.slice(0, 20);
        this.loading = false;
        this.cdr.detectChanges();
      });
  }

  // Handle suggestion selection
  selectSuggestion(locker: LockerResponse, event?: Event) {
    event?.preventDefault();
    event?.stopPropagation();

    this.searchControl.setValue(`${locker.city} (${locker.postal_code})`, {
      emitEvent: false,
    });
    this.suggestions = [];
    this.cdr.detectChanges();
    this.lockerSearch.emit(locker);
  }
}
