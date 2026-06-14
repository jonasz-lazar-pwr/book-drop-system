// orders-page.ts
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { StatusLabelPipe } from '@shared/pipes/status-label-pipe';
import { NavbarComponent } from '@shared/components/navbar/navbar.component';
import { OrderService } from '@services/order.service';
import { Order, OrderStatus } from '@models/order';
import { OrderDetails } from './components/order-details/order-details';

type TabType = 'in_progress' | 'ready' | 'borrowed' | 'completed';

@Component({
  selector: 'app-orders-page',
  imports: [NavbarComponent, DatePipe, NgOptimizedImage, StatusLabelPipe, OrderDetails, NgClass],
  templateUrl: './orders-page.html',
  styleUrl: './orders-page.scss',
})
export class OrdersPage implements OnInit {
  private readonly orderService = inject(OrderService);

  orders = signal<Order[]>([]);
  loading = signal(true);
  selectedOrder = signal<Order | null>(null);

  // Zakładka + Filtry
  activeTab = signal<TabType>('in_progress');
  statusFilter = signal<OrderStatus | 'all'>('all');
  sortOrder = signal<'newest' | 'oldest'>('newest');

  // Computed dla każdej zakładki
  inProgressOrders = computed(() => {
    return this.orders().filter((o) => ['new', 'prepared', 'in_transit'].includes(o.status));
  });

  readyOrders = computed(() => {
    return this.orders().filter((o) => o.status === 'ready_for_pickup');
  });

  borrowedOrders = computed(() => {
    return this.orders().filter((o) => {
      if (o.status === 'picked_up') return true;

      if (o.status === 'return_in_progress') {
        // Tylko jeśli user jeszcze NIE umieścił książek w książkomacie
        return o.shipment?.status === 'created';
      }

      return false;
    });
  });

  completedOrders = computed(() => {
    return this.orders().filter((o) => {
      if (o.status === 'returned' || o.status === 'canceled') return true;

      if (o.status === 'return_in_progress') {
        // User już umieścił książki - dla niego transakcja zakończona
        return o.shipment?.status === 'placed_in_locker' || o.shipment?.status === 'completed';
      }

      return false;
    });
  });
  // Dostępne statusy w aktualnej zakładce (dla dropdowna)
  availableStatuses = computed(() => {
    const tab = this.activeTab();
    let tabOrders: Order[] = [];

    switch (tab) {
      case 'in_progress':
        tabOrders = this.inProgressOrders();
        break;
      case 'ready':
        tabOrders = this.readyOrders();
        break;
      case 'borrowed':
        tabOrders = this.borrowedOrders();
        break;
      case 'completed':
        tabOrders = this.completedOrders();
        break;
    }

    const statusSet = new Set(tabOrders.map((o) => o.status));
    return Array.from(statusSet).sort();
  });

  // Wyświetlane zamówienia (z filtrowaniem i sortowaniem)
  displayedOrders = computed(() => {
    const tab = this.activeTab();
    let tabOrders: Order[] = [];

    // 1. Wybierz zakładkę
    switch (tab) {
      case 'in_progress':
        tabOrders = this.inProgressOrders();
        break;
      case 'ready':
        tabOrders = this.readyOrders();
        break;
      case 'borrowed':
        tabOrders = this.borrowedOrders();
        break;
      case 'completed':
        tabOrders = this.completedOrders();
        break;
    }

    // 2. Filtruj po statusie
    const filter = this.statusFilter();
    if (filter !== 'all') {
      tabOrders = tabOrders.filter((o) => o.status === filter);
    }

    // 3. Sortuj
    const sort = this.sortOrder();
    tabOrders = [...tabOrders].sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      return sort === 'newest' ? dateB - dateA : dateA - dateB;
    });

    return tabOrders;
  });

  ngOnInit(): void {
    this.loadOrders();
  }

  loadOrders(): void {
    this.loading.set(true);
    this.orderService.getOrders().subscribe({
      next: (orders) => {
        this.orders.set(orders);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading orders:', err);
        this.loading.set(false);
      },
    });
  }

  setTab(tab: TabType): void {
    this.activeTab.set(tab);
    this.statusFilter.set('all'); // Reset filtra przy zmianie zakładki
  }

  setStatusFilter(status: OrderStatus | 'all'): void {
    this.statusFilter.set(status);
  }

  setSortOrder(order: 'newest' | 'oldest'): void {
    this.sortOrder.set(order);
  }

  openOrderDetails(order: Order): void {
    this.selectedOrder.set(order);
  }

  closeOrderDetails(): void {
    this.selectedOrder.set(null);
    this.loadOrders();
  }

  statusClass(status: string) {
    return {
      'bg-blue-100 text-blue-700': status === 'new',
      'bg-indigo-100 text-indigo-700': status === 'prepared',
      'bg-yellow-100 text-yellow-700': status === 'in_transit',
      'bg-green-100 text-green-700': status === 'ready_for_pickup',
      'bg-gray-200 text-gray-700': status === 'picked_up',
      'bg-orange-100 text-orange-700': status === 'return_in_progress',
      'bg-emerald-100 text-emerald-700': status === 'returned',
      'bg-red-100 text-red-700': status === 'canceled',
    };
  }

  formatOrderId(id: string): string {
    return `#${id.slice(-8).toUpperCase()}`;
  }

  getBookThumbnails(order: Order): string[] {
    return order.items.slice(0, 2).map((item) => item.thumbnail || '');
  }

  getRemainingBooksCount(order: Order): number {
    return Math.max(0, order.items.length - 2);
  }
}
