import { Routes } from '@angular/router';
// import { AuthGuard } from '@guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('@pages/landing-page/landing-page.component').then((m) => m.LandingPageComponent),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
