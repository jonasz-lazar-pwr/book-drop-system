import { Injectable, OnDestroy, inject } from '@angular/core';
import { interval, Subscription, switchMap, of } from 'rxjs';
import { AuthService } from '@services/auth.service';
import { StorageService } from '@services/storage.service';

@Injectable({ providedIn: 'root' })
export class TokenMonitorService implements OnDestroy {
  private readonly checkIntervalMs = 60_000;
  private readonly refreshThresholdMs = 60_000;
  private intervalSub?: Subscription;
  private isRefreshing = false;

  private readonly auth = inject(AuthService);
  private readonly storage = inject(StorageService);

  constructor() {
    this.intervalSub = interval(this.checkIntervalMs)
      .pipe(switchMap(() => this.checkAndRefreshToken()))
      .subscribe();
  }

  private checkAndRefreshToken() {
    const accessToken = this.storage.getAccessToken();
    if (!accessToken || this.isRefreshing) return of(null);

    const payload = this.decodeJwt(accessToken);
    const exp = typeof payload?.['exp'] === 'number' ? payload['exp'] : null;
    if (!exp) return of(null);

    const expiresAt = exp * 1000;
    const remaining = expiresAt - Date.now();

    if (remaining < this.refreshThresholdMs && remaining > 0) {
      this.isRefreshing = true;
      return this.auth.refresh().pipe(
        switchMap(() => {
          this.isRefreshing = false;
          return of(true);
        })
      );
    }

    return of(null);
  }

  private decodeJwt(token: string): Record<string, unknown> | null {
    try {
      const [, payload] = token.split('.');
      return JSON.parse(atob(payload));
    } catch {
      return null;
    }
  }

  ngOnDestroy() {
    this.intervalSub?.unsubscribe();
  }
}
