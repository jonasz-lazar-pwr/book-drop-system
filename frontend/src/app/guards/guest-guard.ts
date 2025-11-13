import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { StorageService } from '@services/storage.service';
import { AuthService } from '@services/auth.service';
import { firstValueFrom } from 'rxjs';

export const guestGuard: CanActivateFn = async () => {
  const storage = inject(StorageService);
  const router = inject(Router);
  const auth = inject(AuthService);

  // Allow access only for unauthenticated users
  if (!storage.isAuthenticated()) return true;

  try {
    const user = await firstValueFrom(auth.getCurrentUser());
    const target = user ? auth.getRedirectPathForRole(user.role) : '/';
    await router.navigate([target]);
  } catch {
    await router.navigate(['/']);
  }

  return false;
};
