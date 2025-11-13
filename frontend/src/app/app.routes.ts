import { Routes } from '@angular/router';
import { LandingPage } from '@pages/landing-page/landing-page';
import { LoginPage } from '@pages/login-page/login-page';
import { RegisterPage } from '@pages/register-page/register-page';
import { CatalogPage } from '@pages/catalog-page/catalog-page';
import { OrdersPage } from '@pages/orders-page/orders-page';
import { LockersPage } from '@pages/lockers-page/lockers-page';
import { ReturnsPage } from '@pages/returns-page/returns-page';
import { DeliveriesPage } from '@pages/deliveries-page/deliveries-page';
import { CartPage } from '@pages/cart-page/cart-page';
import { ProfilePage } from '@pages/profile-page/profile-page';
import { authGuard } from '@guards/auth-guard';
import { guestGuard } from '@guards/guest-guard';

export const routes: Routes = [
  { path: '', component: LandingPage, canActivate: [guestGuard], pathMatch: 'full' },
  { path: 'login', component: LoginPage, canActivate: [guestGuard] },
  { path: 'register', component: RegisterPage, canActivate: [guestGuard] },

  { path: 'catalog', component: CatalogPage, canActivate: [authGuard] },
  { path: 'orders', component: OrdersPage, canActivate: [authGuard] },
  { path: 'lockers', component: LockersPage, canActivate: [authGuard] },
  { path: 'returns', component: ReturnsPage, canActivate: [authGuard] },
  { path: 'deliveries', component: DeliveriesPage, canActivate: [authGuard] },
  { path: 'cart', component: CartPage, canActivate: [authGuard] },
  { path: 'profile', component: ProfilePage, canActivate: [authGuard] },

  { path: '**', redirectTo: '' },
];
