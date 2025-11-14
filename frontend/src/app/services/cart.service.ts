import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { runtimeEnv } from '@runtime/runtime-env';
import { CartResponse, AddItemRequest, UpdateQuantityRequest } from '@models/cart';

@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${runtimeEnv.API_URL}/api/cart`;

  readonly cartCount = signal(0);

  private syncCount(res: CartResponse | null) {
    const count = res?.total_items ?? 0;
    if (this.cartCount() !== count) this.cartCount.set(count);
  }

  getCart() {
    return this.http.get<CartResponse>(this.baseUrl).pipe(
      tap((res) => this.syncCount(res))
    );
  }

  addItem(payload: AddItemRequest) {
    return this.http.post<CartResponse>(`${this.baseUrl}/items`, payload).pipe(
      tap((res) => this.syncCount(res))
    );
  }

  updateQuantity(isbn: string, payload: UpdateQuantityRequest) {
    return this.http.patch<CartResponse>(`${this.baseUrl}/items/${isbn}`, payload).pipe(
      tap((res) => this.syncCount(res))
    );
  }

  removeItem(isbn: string) {
    return this.http.delete<CartResponse>(`${this.baseUrl}/items/${isbn}`).pipe(
      tap((res) => this.syncCount(res))
    );
  }

  clear() {
    return this.http.delete<CartResponse>(`${this.baseUrl}/clear`).pipe(
      tap(() => this.syncCount(null))
    );
  }

  prepareOrder() {
    return this.http.post(`${this.baseUrl}/prepare-order`, {});
  }
}
