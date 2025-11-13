import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { runtimeEnv } from '@runtime/runtime-env';
import { AccessToken, LoginPayload, RegisterPayload, TokenPair, UserInfo } from '@models/auth';
import { StorageService } from '@services/storage.service';
import { tap, throwError } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly api = `${runtimeEnv.API_URL}/auth`;
  private readonly http = inject(HttpClient);
  private readonly storage = inject(StorageService);

  register(data: RegisterPayload) {
    return this.http
      .post<TokenPair>(`${this.api}/register`, data)
      .pipe(tap((tokens) => this.saveTokens(tokens)));
  }

  login(data: LoginPayload) {
    return this.http
      .post<TokenPair>(`${this.api}/login`, data)
      .pipe(tap((tokens) => this.saveTokens(tokens)));
  }

  refresh() {
    const token = this.storage.getRefreshToken();
    if (!token) return throwError(() => new Error('Missing refresh token'));

    return this.http
      .post<AccessToken>(`${this.api}/refresh`, { refresh_token: token })
      .pipe(tap((res) => this.storage.setAccessToken(res.access_token)));
  }

  logout() {
    this.storage.clear();
    return this.http
      .post(`${this.api}/logout`, {})
      .pipe(tap(() => this.storage.clear()));
  }

  getCurrentUser() {
    return this.http.get<UserInfo>(`${this.api}/me`);
  }

  getRedirectPathForRole(role: string): string {
    switch (role) {
      case 'reader': return '/catalog';
      case 'librarian': return '/orders';
      case 'courier': return '/deliveries';
      default: return '/';
    }
  }

  canAccess(role: string, path: string): boolean {
    const accessMap: Record<string, string[]> = {
      reader: ['/catalog', '/orders', '/lockers', '/profile', '/cart'],
      librarian: ['/catalog', '/orders', '/returns', '/profile'],
      courier: ['/deliveries', '/profile'],
    };
    return accessMap[role]?.includes(path) ?? false;
  }

  // Store access and refresh tokens in local storage
  private saveTokens(tokens: TokenPair) {
    this.storage.setAccessToken(tokens.access_token);
    this.storage.setRefreshToken(tokens.refresh_token);
  }
}
