import { Component, HostListener, OnInit, inject, computed } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '@services/auth.service';
import { CartService } from '@services/cart.service';
import { UserInfo } from '@models/auth';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss',
})
export class NavbarComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly cart = inject(CartService);
  private readonly router = inject(Router);

  user?: UserInfo;
  showMenu = false;
  showMobileMenu = false;
  menuItems: { label: string; path: string }[] = [];
  cartCount = computed(() => this.cart.cartCount());

  ngOnInit(): void {
    // Load current user on navbar init
    this.auth.getCurrentUser().subscribe({
      next: (u) => {
        this.user = u;
        this.setupMenu(u.role);

        // Readers always have cart
        if (u.role === 'reader') {
          this.cart.getCart().subscribe();
        }
      },
      error: () => {
        this.user = undefined;
        this.menuItems = [];
      },
    });
  }

  // Assign menu items based on role
  private setupMenu(role: string): void {
    switch (role) {
      case 'reader':
        this.menuItems = [
          { label: 'Katalog', path: '/catalog' },
          { label: 'Zamówienia', path: '/orders' },
        ];
        break;

      case 'librarian':
        this.menuItems = [
          { label: 'Zamówienia', path: '/librarian/orders' },
          // { label: 'Zwroty', path: '/librarian/returns' },
        ];
        break;

      case 'courier':
        this.menuItems = [{ label: 'Dostawy', path: '/deliveries' }];
        break;

      default:
        this.menuItems = [];
        break;
    }
  }

  toggleMobileMenu(): void {
    this.showMobileMenu = !this.showMobileMenu;
  }

  // Close profile dropdown when clicking outside
  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: Event): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.profile-menu')) {
      this.showMenu = false;
    }
  }

  // Clear session and redirect
  logout(): void {
    this.auth.logout().subscribe({
      next: () => {
        this.user = undefined;
        this.menuItems = [];
        this.router.navigate(['/login']);
      },
      error: () => {
        this.user = undefined;
        this.menuItems = [];
        this.router.navigate(['/login']);
      },
    });
  }
}
