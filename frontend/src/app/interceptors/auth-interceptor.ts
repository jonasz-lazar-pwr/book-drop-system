import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpErrorResponse,
} from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { StorageService } from '@services/storage.service';
import { runtimeEnv } from '@runtime/runtime-env';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const storage = inject(StorageService);
  const router = inject(Router);

  const apiUrl = runtimeEnv.API_URL ?? '';
  const isAuthRequest = req.url.startsWith(`${apiUrl}/auth/`);

  // attach JWT if available
  const token = storage.getAccessToken();
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      console.debug('[authInterceptor] ERROR status:', error.status);

      // If 401 AND not auth request → session expired
      if (error.status === 401 && !isAuthRequest) {
        console.debug('[authInterceptor] Invalid token → logout');

        storage.clear();
        router.navigate(['/login']);
      }

      return throwError(() => error);
    })
  );
};
