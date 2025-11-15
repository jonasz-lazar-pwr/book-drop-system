import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { runtimeEnv } from '@runtime/runtime-env';
import { LoginPayload, TokenPair, UserInfo } from '@models/auth';
import { StorageService } from '@services/storage.service';
import { catchError, Observable, of, shareReplay, tap, throwError } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly api = `${runtimeEnv.API_URL}/auth`;
  private readonly http = inject(HttpClient);
  private readonly storage = inject(StorageService);

  private currentUserCache: UserInfo | null = null;
  private currentUserRequest$: Observable<UserInfo> | null = null;

  // Registers a new user and stores tokens
  register(data: Omit<UserInfo, 'id' | 'role'> & { password: string }) {
    return this.http.post<TokenPair>(`${this.api}/register`, data).pipe(
      tap((tokens) => {
        this.storage.setAccessToken(tokens.access_token);
        this.storage.setRefreshToken(tokens.refresh_token);
        this.currentUserCache = null;
        this.currentUserRequest$ = null;
      })
    );
  }

  // Logs in and stores tokens
  login(data: LoginPayload) {
    return this.http.post<TokenPair>(`${this.api}/login`, data).pipe(
      tap((tokens) => {
        this.storage.setAccessToken(tokens.access_token);
        this.storage.setRefreshToken(tokens.refresh_token);
        this.currentUserCache = null;
        this.currentUserRequest$ = null;
      })
    );
  }

  // Clears tokens and sends logout request
  logout() {
    this.storage.clear();
    this.currentUserCache = null;
    this.currentUserRequest$ = null;
    return this.http.post(`${this.api}/logout`, {});
  }

  // Refreshes access token
  refresh() {
    const refreshToken = this.storage.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('Missing refresh token'));
    }

    return this.http
      .post<{ access_token: string }>(`${this.api}/refresh`, {
        refresh_token: refreshToken,
      })
      .pipe(
        tap((res) => {
          this.storage.setAccessToken(res.access_token);
        })
      );
  }

  // Returns current user with caching + request deduplication
  getCurrentUser(): Observable<UserInfo> {
    if (this.currentUserCache) {
      return of(this.currentUserCache);
    }

    if (this.currentUserRequest$) {
      return this.currentUserRequest$;
    }

    this.currentUserRequest$ = this.http.get<UserInfo>(`${this.api}/me`).pipe(
      tap((u) => (this.currentUserCache = u)),
      shareReplay(1),
      catchError((err) => {
        this.currentUserRequest$ = null;
        throw err;
      })
    );

    return this.currentUserRequest$;
  }

  // Maps a role to its landing page
  getRedirectPathForRole(role: string): string {
    switch (role) {
      case 'reader': return '/catalog';
      case 'librarian': return '/librarian/orders';
      case 'courier': return '/deliveries';
      default: return '/';
    }
  }

  // Checks if a role is allowed to access a given path
  canAccess(role: string, path: string): boolean {
    const accessMap: Record<string, string[]> = {
      reader: ['/catalog', '/orders', '/profile', '/cart', '/checkout'],
      librarian: ['/librarian/orders', '/librarian/returns', '/profile'],
      courier: ['/deliveries', '/profile'],
    };

    return accessMap[role]?.includes(path) ?? false;
  }
}
