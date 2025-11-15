import { Routes } from '@angular/router';
import { LandingPage } from '@pages/landing-page/landing-page';
import { LoginPage } from '@pages/login-page/login-page';
import { RegisterPage } from '@pages/register-page/register-page';
import { CatalogPage } from '@pages/catalog-page/catalog-page';
import { LibrarianOrdersPage } from '@pages/librarian-orders-page/librarian-orders-page';
import { CartPage } from '@pages/cart-page/cart-page';
import { CheckoutPage } from '@pages/checkout-page/checkout-page';
import { OrdersPage } from '@pages/orders-page/orders-page';
import { DeliveriesPage } from '@pages/deliveries-page/deliveries-page';
import { ReturnsPage } from '@pages/returns-page/returns-page';
import { ProfilePage } from '@pages/profile-page/profile-page';
import { authGuard } from '@guards/auth-guard';
import { guestGuard } from '@guards/guest-guard';

export const routes: Routes = [
  // PUBLIC
  { path: '', component: LandingPage, canActivate: [guestGuard], pathMatch: 'full' },
  { path: 'login', component: LoginPage, canActivate: [guestGuard] },
  { path: 'register', component: RegisterPage, canActivate: [guestGuard] },

  // READER
  { path: 'catalog', component: CatalogPage, canActivate: [authGuard] },
  { path: 'cart', component: CartPage, canActivate: [authGuard] },
  { path: 'checkout', component: CheckoutPage, canActivate: [authGuard] },
  { path: 'orders', component: OrdersPage, canActivate: [authGuard] },

  // LIBRARIAN
  { path: 'librarian/orders', component: LibrarianOrdersPage, canActivate: [authGuard] },
  { path: 'librarian/returns', component: ReturnsPage, canActivate: [authGuard] },

  // COURIER
  { path: 'deliveries', component: DeliveriesPage, canActivate: [authGuard] },

  // PROFILE
  { path: 'profile', component: ProfilePage, canActivate: [authGuard] },

  { path: '**', redirectTo: '' },
];
