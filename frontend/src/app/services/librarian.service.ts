import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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

  listOrders() {
    return this.http.get<LibrarianOrderListItem[]>(`${this.baseUrl}/orders`);
  }

  getOrderDetails(id: string) {
    return this.http.get<LibrarianOrderDetails>(`${this.baseUrl}/orders/${id}`);
  }

  getOrderSummary(id: string) {
    return this.http.get<LibrarianOrderSummary>(`${this.baseUrl}/orders/${id}/summary`);
  }

  assignItems(id: string, body: AssignItemsRequest) {
    return this.http.post<SimpleMessageResponse>(
      `${this.baseUrl}/orders/${id}/assign-items`,
      body
    );
  }
}
