import { inject, Injectable } from '@angular/core';
import { catchError, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';
// import { runtimeEnv } from '@environments/runtime-env';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);

  constructor() {}

  // Decodes the ID token and extracts the user's "sub" (unique identifier)
  // getUserSub(): string | null {
  //   const idToken = this.getIdToken();
  //   if (!idToken) return null;
  //
  //   try {
  //   } catch (e) {}
  // }

  // Returns true if the user is authenticated (based on presence of id_token)
  isAuthenticated(): boolean {
    return !!this.getTokenFromSessionStorage('id_token');
  }

  // Retrieves the ID token from sessionStorage
  getIdToken(): string | null {
    return this.getTokenFromSessionStorage('id_token');
  }

  // Reads either id_token or access_token from OIDC sessionStorage entry
  private getTokenFromSessionStorage(tokenType: 'id_token' | 'access_token'): string | null {
    const storageKeys = Object.keys(sessionStorage);
    const oidcKey = storageKeys.find((key) => key.startsWith('0-'));

    if (!oidcKey) return null;

    try {
      const storedData = JSON.parse(sessionStorage.getItem(oidcKey) || '{}');
      return storedData.authnResult?.[tokenType] || null;
    } catch (error) {
      console.error(`Error parsing sessionStorage data for ${tokenType}:`, error);
      return null;
    }
  }

  // Sends a POST request to backend to register a user (only called once after login)
  registerUser(): Observable<boolean> {
    return this.http.post('api/users/register', null).pipe(
      map(() => true),
      catchError((error) => {
        console.error('User registration failed:', error);
        return of(false);
      }),
    );
  }

  // Starts the OIDC login redirect flow
  login(): void {}

  // Clears sessionStorage, log out and redirects
  logout(): void {
    if (window.sessionStorage) {
      window.sessionStorage.clear();
    }

    // Redirect after logout
  }
}
