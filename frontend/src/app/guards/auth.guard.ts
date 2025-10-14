import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '@services/auth.service';

export const AuthGuard: CanActivateFn = () => {
  // Inject OIDC service to access authentication state
  const authService = inject(AuthService);

  // Inject router to allow redirection
  const router = inject(Router);

  // Check if user is authenticated
  if (authService.isAuthenticated()) {
    return true; // Allow route activation
  }
  // Redirect to landing page if not authenticated
  router.navigate(['/']);
  return false;
};
