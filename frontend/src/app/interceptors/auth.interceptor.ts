import { Injectable, inject } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '@services/auth.service';
import { runtimeEnv } from '@environments/runtime-env';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private authService = inject(AuthService);

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const idToken = this.authService.getIdToken();

    if (req.url.startsWith('api') && idToken) {
      const apiReq = req.clone({
        url: `${runtimeEnv.apiUrl}${req.url}`,
        setHeaders: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      return next.handle(apiReq);
    }

    return next.handle(req);
  }
}
