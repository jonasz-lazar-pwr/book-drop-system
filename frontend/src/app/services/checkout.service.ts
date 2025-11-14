import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { runtimeEnv } from '@runtime/runtime-env';
import { Observable } from 'rxjs';
import {
  CheckoutSubmitResponse,
  CheckoutSummaryResponse,
  LockerResponse
} from '@models/checkout';

@Injectable({
  providedIn: 'root',
})
export class CheckoutService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${runtimeEnv.API_URL}/api/checkout`;

  getSummary(): Observable<CheckoutSummaryResponse> {
    return this.http.get<CheckoutSummaryResponse>(`${this.baseUrl}/summary`);
  }

  getLockers(filters?: {
    city?: string;
    postal_code?: string;
    lat?: number;
    lon?: number;
    radius?: number;
  }): Observable<LockerResponse[]> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) params = params.set(key, value.toString());
      });
    }
    return this.http.get<LockerResponse[]>(`${this.baseUrl}/lockers`, { params });
  }

  submitCheckout(lockerId: string): Observable<CheckoutSubmitResponse> {
    return this.http.post<CheckoutSubmitResponse>(`${this.baseUrl}/submit`, { locker_id: lockerId });
  }
}
