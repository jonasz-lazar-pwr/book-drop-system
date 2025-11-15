import { Component, inject, OnInit, signal } from '@angular/core';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { LockerSearch } from '@pages/checkout-page/components/locker-search/locker-search';
import { LockerMap } from '@pages/checkout-page/components/locker-map/locker-map';
import { CheckoutService } from '@services/checkout.service';
import { Router } from '@angular/router';
import { CheckoutSummaryResponse, LockerResponse } from '@models/checkout';
import { catchError, finalize, of } from 'rxjs';
import { DecimalPipe, NgClass } from '@angular/common';

@Component({
  selector: 'app-checkout-page',
  standalone: true,
  imports: [
    NavbarComponent,
    DecimalPipe,
    LockerSearch,
    LockerMap,
    NgClass
  ],
  templateUrl: './checkout-page.html',
  styleUrls: ['./checkout-page.scss'],
})
export class CheckoutPage implements OnInit {
  private readonly checkout = inject(CheckoutService);
  private readonly router = inject(Router);

  summary = signal<CheckoutSummaryResponse | null>(null);
  lockers = signal<LockerResponse[]>([]);
  selectedLocker = signal<LockerResponse | null>(null);
  loading = signal(true);

  ngOnInit() {
    this.loadSummary();
    this.loadLockers();
  }

  private loadSummary() {
    this.summary.set(null);
    this.loading.set(true);

    this.checkout
      .getSummary()
      .pipe(
        catchError(() => {
          this.router.navigate(['/cart']);
          return of(null);
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe((res) => this.summary.set(res));
  }

  // Handles search input (postal code, street name, city, or direct locker object)
  searchLockers(selection: LockerResponse | string) {
    if (typeof selection === 'object' && selection.id) {
      this.selectedLocker.set(selection);
      this.lockers.set([selection]);
      return;
    }

    const query = typeof selection === 'string' ? selection.trim() : '';
    if (!query) return;

    this.loading.set(true);

    const filters: Record<string, string | number> = {};
    const lower = query.toLowerCase();

    const postalCodeRegex = /^\d{2}-\d{3}$/;
    const postalCodeNoDashRegex = /^\d{5}$/;
    const streetIndicatorRegex =
      /(ul\.?|al\.|pl\.|os\.|wybrzeże|rynek|aleja|parkowa|plac|dworcowa|kościelna)/i;

    if (postalCodeRegex.test(query) || postalCodeNoDashRegex.test(query)) {
      filters['postal_code'] = query;
    } else if (/\d/.test(query) || streetIndicatorRegex.test(lower)) {
      filters['street'] = query;
    } else {
      filters['city'] = query;
    }

    this.checkout
      .getLockers(filters)
      .pipe(
        catchError(() => of([])),
        finalize(() => this.loading.set(false))
      )
      .subscribe((res) => this.lockers.set(res));
  }

  selectLocker(locker: LockerResponse) {
    this.selectedLocker.set(locker);
  }

  submit() {
    const locker = this.selectedLocker();
    if (!locker) return;

    this.loading.set(true);

    this.checkout
      .submitCheckout(locker.id)
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.loading.set(false))
      )
      .subscribe((res) => {
        if (res) this.router.navigate(['/orders']);
      });
  }

  private loadLockers() {
    this.checkout
      .getLockers()
      .pipe(catchError(() => of([])))
      .subscribe((res) => this.lockers.set(res));
  }
}
