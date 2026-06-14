import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { runtimeEnv } from '@runtime/runtime-env';

import {
  LibrarianOrderListItem,
  LibrarianOrderDetails,
  AssignItemsRequest,
  SimpleMessageResponse,
  LibrarianOrderSummary,
} from '@models/librarian';

@Injectable({
  providedIn: 'root',
})
export class LibrarianService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${runtimeEnv.API_URL}/api/librarian`;

  /**
   * GET /api/librarian/orders
   * Lista wszystkich zamówień (wszystkie statusy)
   */
  listOrders(): Observable<LibrarianOrderListItem[]> {
    return this.http.get<LibrarianOrderListItem[]>(`${this.baseUrl}/orders`);
  }

  /**
   * GET /api/librarian/orders/{id}
   * Szczegóły zamówienia NEW (do przypisania egzemplarzy)
   */
  getOrderDetails(id: string): Observable<LibrarianOrderDetails> {
    return this.http.get<LibrarianOrderDetails>(`${this.baseUrl}/orders/${id}`);
  }

  /**
   * GET /api/librarian/orders/{id}/summary
   * Podsumowanie zamówienia (dla statusów > new)
   */
  getOrderSummary(id: string): Observable<LibrarianOrderSummary> {
    return this.http.get<LibrarianOrderSummary>(`${this.baseUrl}/orders/${id}/summary`);
  }

  /**
   * POST /api/librarian/orders/{id}/assign-items
   * Przypisz egzemplarze do zamówienia NEW
   */
  assignItems(id: string, body: AssignItemsRequest): Observable<SimpleMessageResponse> {
    return this.http.post<SimpleMessageResponse>(
      `${this.baseUrl}/orders/${id}/assign-items`,
      body
    );
  }

  /**
   * POST /api/librarian/orders/{id}/accept-return
   * Potwierdź przyjęcie zwrotu książek
   */
  acceptReturn(id: string): Observable<SimpleMessageResponse> {
    return this.http.post<SimpleMessageResponse>(
      `${this.baseUrl}/orders/${id}/accept_return`,
      {}
    );
  }
}
