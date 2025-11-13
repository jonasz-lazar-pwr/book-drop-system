import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Book } from '@models/catalog';
import { runtimeEnv } from '@runtime/runtime-env';

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${runtimeEnv.API_URL}/api/catalog`;

  getBooks(
    page = 1,
    limit = 15,
    search = '',
    sort = '',
    filters?: {
      publisher?: string;
      availableOnly?: boolean;
      yearFrom?: number;
      yearTo?: number;
    }
  ): Observable<{ items: Book[]; total: number }> {
    let params = new HttpParams()
      .set('page', String(page))
      .set('limit', String(limit))
      .set('search', search || '')
      .set('sort', sort || '');

    if (filters) {
      if (filters.publisher) params = params.set('publisher', filters.publisher);
      if (filters.availableOnly !== undefined)
        params = params.set('available_only', String(filters.availableOnly));
      if (filters.yearFrom != null) params = params.set('year_from', String(filters.yearFrom));
      if (filters.yearTo != null) params = params.set('year_to', String(filters.yearTo));
    }

    return this.http.get<{ items: Book[]; total: number }>(`${this.baseUrl}/books`, { params });
  }

  getPublishers(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/publishers`);
  }

  getBookDetails(isbn: string): Observable<Book> {
    return this.http.get<Book>(`${this.baseUrl}/books/${isbn}`);
  }
}
