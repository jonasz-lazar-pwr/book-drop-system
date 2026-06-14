// services/order.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LockerShipment, Order, Locker, OrderStatus } from '@models/order';
import { UUID } from '@models/types';
import { runtimeEnv } from '@runtime/runtime-env';

@Injectable({ providedIn: 'root' })
export class OrderService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${runtimeEnv.API_URL}/api/orders`;
  private readonly lockersUrl = `${runtimeEnv.API_URL}/api/lockers`;

  /**
   * ✅ GET /api/orders
   * Pobiera listę zamówień użytkownika (aktywne + historia)
   */
  getOrders(status?: OrderStatus): Observable<Order[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Order[]>(this.baseUrl, { params });
  }

  /**
   * ✅ GET /api/orders/{orderId}
   * Pobiera szczegóły konkretnego zamówienia
   */
  getOrderDetails(orderId: UUID): Observable<Order> {
    return this.http.get<Order>(`${this.baseUrl}/${orderId}`);
  }

  /**
   * ✅ POST /api/orders/{orderId}/confirm-pickup
   * Potwierdza odbiór książek z książkomatu
   */
  confirmPickup(orderId: UUID): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.baseUrl}/${orderId}/confirm-pickup`,
      {}
    );
  }

  /**
   * ✅ POST /api/orders/{orderId}/initiate-return
   * Inicjuje zwrot - wybiera książkomat i tworzy shipment
   */
  initiateReturn(orderId: UUID, lockerId: UUID): Observable<LockerShipment> {
    return this.http.post<LockerShipment>(
      `${this.baseUrl}/${orderId}/initiate-return`,
      { locker_id: lockerId }
    );
  }

  /**
   * ✅ POST /api/orders/{orderId}/confirm-return
   * Potwierdza umieszczenie książek w książkomacie (zwrot)
   */
  confirmReturn(orderId: UUID): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.baseUrl}/${orderId}/confirm-return`,
      {}
    );
  }

  /**
   * ✅ GET /api/lockers
   * Pobiera listę książkomatów (z opcjonalnym geolokalizacją)
   */
  getLockers(lat?: number, lng?: number, limit: number = 10): Observable<Locker[]> {
    let params = new HttpParams().set('limit', limit.toString());

    if (lat !== undefined && lng !== undefined) {
      params = params.set('lat', lat.toString()).set('lng', lng.toString());
    }

    return this.http.get<Locker[]>(this.lockersUrl, { params });
  }
}
