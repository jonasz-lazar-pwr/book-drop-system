import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
  HttpErrorResponse,
} from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '@services/auth.service';
import { StorageService } from '@services/storage.service';
import { runtimeEnv } from '@runtime/runtime-env';

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const storage = inject(StorageService);
  const auth = inject(AuthService);
  const router = inject(Router);

  const apiUrl = runtimeEnv.API_URL ?? '';
  const isAuthRequest = req.url.startsWith(`${apiUrl}/auth/`);

  // Attach access token to authorized requests
  const token = storage.getAccessToken();
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 by trying to refresh the token
      if (error.status === 401 && !isAuthRequest) {
        const refreshToken = storage.getRefreshToken();

        if (!refreshToken) {
          storage.clear();
          router.navigate(['/']);
          return throwError(() => error);
        }

        // Attempt token refresh
        return auth.refresh().pipe(
          switchMap(() => {
            const newToken = storage.getAccessToken();
            if (newToken) {
              const cloned = req.clone({
                setHeaders: { Authorization: `Bearer ${newToken}` },
              });
              return next(cloned);
            }
            router.navigate(['/']);
            return throwError(() => error);
          }),
          catchError(() => {
            storage.clear();
            router.navigate(['/']);
            return throwError(() => error);
          }),
        );
      }

      return throwError(() => error);
    }),
  );
};
