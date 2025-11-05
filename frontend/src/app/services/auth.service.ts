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

  private http = inject(HttpClient);
  private storage = inject(StorageService);

  register(data: RegisterPayload) {
    return this.http.post<TokenPair>(`${this.api}/register`, data)
      .pipe(tap(tokens => this.saveTokens(tokens)));
  }

  login(data: LoginPayload) {
    return this.http.post<TokenPair>(`${this.api}/login`, data)
      .pipe(tap(tokens => this.saveTokens(tokens)));
  }

  refresh() {
    const token = this.storage.getRefreshToken();
    if (!token) return throwError(() => new Error('Missing refresh token'));

    return this.http.post<AccessToken>(`${this.api}/refresh`, { refresh_token: token })
      .pipe(tap(res => this.storage.setAccessToken(res.access_token)));
  }

  logout() {
    this.storage.clear();
    return this.http.post(`${this.api}/logout`, {}).pipe(tap(() => this.storage.clear()));
  }

  getCurrentUser() {
    return this.http.get<UserInfo>(`${this.api}/me`);
  }

  private saveTokens(tokens: TokenPair) {
    this.storage.setAccessToken(tokens.access_token);
    this.storage.setRefreshToken(tokens.refresh_token);
  }

  isLoggedIn(): boolean {
    return this.storage.isAuthenticated();
  }
}
