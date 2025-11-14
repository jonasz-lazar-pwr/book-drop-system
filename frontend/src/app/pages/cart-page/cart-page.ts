import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { catchError, finalize, of } from 'rxjs';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { CartService } from '@services/cart.service';
import { CartItem, CartResponse } from '@models/cart';
import { Router, RouterLink } from '@angular/router';
import { ToastService } from '@services/toast.service';

@Component({
  selector: 'app-cart-page',
  standalone: true,
  imports: [NavbarComponent, NgOptimizedImage, RouterLink],
  templateUrl: './cart-page.html',
  styleUrl: './cart-page.scss',
})
export class CartPage implements OnInit {
  private readonly cartService = inject(CartService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  cart = signal<CartResponse | null>(null);
  loading = signal(false);
  submitting = signal(false);

  totalItems = computed(() => this.cart()?.total_items ?? 0);
  hasItems = computed(() => (this.cart()?.items?.length ?? 0) > 0);

  ngOnInit() {
    this.loadCart();
  }

  private loadCart() {
    this.loading.set(true);
    this.cartService
      .getCart()
      .pipe(
        catchError(() => {
          this.toast.show('Nie udało się wczytać koszyka.', 'error');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((data) => this.cart.set(data));
  }

  removeItem(isbn: string) {
    if (this.loading()) return;
    this.loading.set(true);

    this.cartService
      .removeItem(isbn)
      .pipe(
        catchError(() => {
          this.toast.show('Nie udało się usunąć pozycji.', 'error');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((data) => {
        if (data) {
          this.cart.set(data);
          this.toast.show('Usunięto pozycję z koszyka.', 'info');
        }
      });
  }

  changeQuantity(item: CartItem, delta: number) {
    const newQuantity = item.quantity + delta;
    if (newQuantity < 1) return;
    if (item.available_count && newQuantity > item.available_count) {
      this.toast.show('Wyczerpano dostępne egzemplarze.', 'error');
      return;
    }
    if (this.loading()) return;

    this.loading.set(true);
    this.cartService
      .updateQuantity(item.isbn, { quantity: newQuantity })
      .pipe(
        catchError(() => {
          this.toast.show('Nie udało się zmienić ilości.', 'error');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((data) => {
        if (data) {
          this.cart.set(data);
          this.toast.show('Zaktualizowano ilość.', 'success');
        }
      });
  }

  clearCart() {
    if (!confirm('Czy na pewno chcesz usunąć wszystkie pozycje z koszyka?')) return;
    if (this.loading()) return;

    this.loading.set(true);
    this.cartService
      .clear()
      .pipe(
        catchError(() => {
          this.toast.show('Nie udało się wyczyścić koszyka.', 'error');
          return of(null);
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe(() => {
        this.cart.set(null);
        this.toast.show('Koszyk został wyczyszczony.', 'info');
      });
  }

  submitCart() {
    if (!this.hasItems()) {
      this.toast.show('Koszyk jest pusty.', 'info');
      return;
    }
    if (this.submitting()) return;

    this.submitting.set(true);
    this.cartService
      .prepareOrder()
      .pipe(
        catchError((err) => {
          console.error('[CartPage] Error preparing order:', err);
          const msg = err?.error?.detail || 'Nie udało się zweryfikować koszyka.';
          this.toast.show(msg, 'error');
          return of(null);
        }),
        finalize(() => this.submitting.set(false)),
      )
      .subscribe((res) => {
        if (res) {
          this.toast.show('Koszyk został zweryfikowany.', 'success');
          this.router.navigate(['/checkout']);
        }
      });
  }
}
