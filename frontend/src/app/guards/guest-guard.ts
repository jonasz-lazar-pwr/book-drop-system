import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { StorageService } from '@services/storage.service';
import { AuthService } from '@services/auth.service';
import { firstValueFrom } from 'rxjs';

export const guestGuard: CanActivateFn = async () => {
  const storage = inject(StorageService);
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!storage.isAuthenticated()) return true;

  try {
    console.debug('[guestGuard] User logged in, redirecting');
    const user = await firstValueFrom(auth.getCurrentUser());
    await router.navigate([auth.getRedirectPathForRole(user.role)]);
  } catch {
    storage.clear();
    await router.navigate(['/login']);
  }

  return false;
};
