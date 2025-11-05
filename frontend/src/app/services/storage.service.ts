import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class StorageService {
  private ACCESS_KEY = 'access_token';
  private REFRESH_KEY = 'refresh_token';

  setAccessToken(token: string): void {
    localStorage.setItem(this.ACCESS_KEY, token);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_KEY);
  }

  setRefreshToken(token: string): void {
    localStorage.setItem(this.REFRESH_KEY, token);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_KEY);
  }

  clear(): void {
    localStorage.removeItem(this.ACCESS_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}
