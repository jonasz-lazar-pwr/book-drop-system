import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { StorageService } from '@services/storage.service';

export const authGuard: CanActivateFn = () => {
  const storage = inject(StorageService);
  const router = inject(Router);

  if (!storage.isAuthenticated()) {
    router.navigate(['/']);
    return false;
  }

  return true;
};
