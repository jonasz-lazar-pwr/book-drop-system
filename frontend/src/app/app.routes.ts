import { Routes } from '@angular/router';
import { LandingPage } from '@pages/landing-page/landing-page';
import { LoginPage } from '@pages/login-page/login-page';
import { RegisterPage } from '@pages/register-page/register-page';
import { DashboardPage } from '@pages/dashboard-page/dashboard-page';
import { authGuard } from '@guards/auth-guard';

export const routes: Routes = [
  { path: '', component: LandingPage },
  { path: 'login', component: LoginPage },
  { path: 'register', component: RegisterPage },
  {
    path: 'dashboard',
    component: DashboardPage,
    canActivate: [authGuard],
  },
  { path: '**', redirectTo: '' },
];
