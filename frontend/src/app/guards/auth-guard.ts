import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot } from '@angular/router';
import { StorageService } from '@services/storage.service';
import { AuthService } from '@services/auth.service';
import { firstValueFrom } from 'rxjs';

export const authGuard: CanActivateFn = async (route: ActivatedRouteSnapshot) => {
  const storage = inject(StorageService);
  const router = inject(Router);
  const auth = inject(AuthService);

  // Check authentication
  if (!storage.isAuthenticated()) {
    await router.navigate(['/']);
    return false;
  }

  try {
    const user = await firstValueFrom(auth.getCurrentUser());
    const path = '/' + route.routeConfig?.path;

    // Check role access permission
    if (!auth.canAccess(user.role, path)) {
      const redirect = auth.getRedirectPathForRole(user.role);
      await router.navigate([redirect]);
      return false;
    }

    return true;
  } catch {
    // Redirect to home if token or session invalid
    await router.navigate(['/']);
    return false;
  }
};
