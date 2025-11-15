import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { StorageService } from '@services/storage.service';
import { AuthService } from '@services/auth.service';
import { firstValueFrom } from 'rxjs';

export const authGuard: CanActivateFn = async (route, state) => {
  const storage = inject(StorageService);
  const auth = inject(AuthService);
  const router = inject(Router);

  // Block access if user is not authenticated
  if (!storage.isAuthenticated()) {
    await router.navigate(['/login']);
    return false;
  }

  try {
    // Load user information (cached or fresh)
    const user = await firstValueFrom(auth.getCurrentUser());
    const path = state.url.split('?')[0];

    // Check role-based access to route
    if (!auth.canAccess(user.role, path)) {
      await router.navigate([auth.getRedirectPathForRole(user.role)]);
      return false;
    }

    return true;
  } catch {
    // Invalid token / failed request → clear session
    storage.clear();
    await router.navigate(['/login']);
    return false;
  }
};
