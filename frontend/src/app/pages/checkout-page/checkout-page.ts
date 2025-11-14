import { Component, inject, OnInit, signal } from '@angular/core';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { LockerSearch } from '@pages/checkout-page/components/locker-search/locker-search';
import { LockerMap } from '@pages/checkout-page/components/locker-map/locker-map';
import { CheckoutService } from '@services/checkout.service';
import { ToastService } from '@services/toast.service';
import { Router } from '@angular/router';
import { CheckoutSummaryResponse, LockerResponse } from '@models/checkout';
import { catchError, finalize, of } from 'rxjs';
import { DecimalPipe, NgClass } from '@angular/common';

@Component({
  selector: 'app-checkout-page',
  standalone: true,
  imports: [NavbarComponent, DecimalPipe, LockerSearch, LockerMap, NgClass],
  templateUrl: './checkout-page.html',
  styleUrls: ['./checkout-page.scss'],
})
export class CheckoutPage implements OnInit {
  private readonly checkout = inject(CheckoutService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  summary = signal<CheckoutSummaryResponse | null>(null);
  lockers = signal<LockerResponse[]>([]);
  selectedLocker = signal<LockerResponse | null>(null);
  loading = signal(true);

  ngOnInit() {
    this.loadSummary();
    this.loadLockers();
  }

  loadSummary() {
    this.summary.set(null);
    this.loading.set(true);
    this.checkout
      .getSummary()
      .pipe(
        catchError(() => {
          this.toast.show('Nie znaleziono aktywnego koszyka.', 'error');
          this.router.navigate(['/cart']);
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((res) => {
        this.summary.set(res);
      });
  }

  // Handle selection from LockerSearch (string or object)
  searchLockers(selection: LockerResponse | string) {
    if (typeof selection === 'object' && selection.id) {
      this.selectedLocker.set(selection);
      this.lockers.set([selection]);
      return;
    }

    const query = typeof selection === 'string' ? selection.trim() : '';
    if (!query) {
      this.toast.show('Podaj miasto, ulicę lub kod pocztowy.', 'info');
      return;
    }

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
        catchError(() => {
          this.toast.show('Nie znaleziono książkomatów.', 'error');
          return of([]);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((res) => {
        this.lockers.set(res);
        if (res.length === 0) {
          this.toast.show('Nie znaleziono książkomatów dla podanej lokalizacji.', 'info');
        }
      });
  }

  selectLocker(locker: LockerResponse) {
    this.selectedLocker.set(locker);
  }

  // Submit checkout and finalize order
  submit() {
    const locker = this.selectedLocker();

    if (!locker) {
      this.toast.show('Wybierz książkomat, aby kontynuować.', 'info');
      return;
    }

    this.loading.set(true);
    this.checkout
      .submitCheckout(locker.id)
      .pipe(
        catchError(() => {
          this.toast.show('Nie udało się złożyć zamówienia.', 'error');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((res) => {
        if (res) {
          this.toast.show('Zamówienie zostało utworzone.', 'success');
          this.router.navigate(['/orders']);
        }
      });
  }

  // Load all lockers (default view)
  loadLockers() {
    this.checkout
      .getLockers()
      .pipe(catchError(() => of([])))
      .subscribe((res) => {
        this.lockers.set(res);
      });
  }
}
