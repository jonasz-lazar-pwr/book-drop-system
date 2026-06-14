import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { NavbarComponent } from '@shared/components/navbar/navbar.component';
import { LibrarianService } from '@services/librarian.service';
import { LibrarianOrderListItem } from '@models/librarian';
import { NgClass, DatePipe } from '@angular/common';
import { StatusLabelPipe } from '@shared/pipes/status-label-pipe';
import { FormsModule } from '@angular/forms';

import {
  LibrarianOrderAssignComponent
} from '@pages/librarian-orders-page/components/librarian-order-assign/librarian-order-assign';

import {
  LibrarianOrderDetailsComponent
} from '@pages/librarian-orders-page/components/librarian-order-details/librarian-order-details';
import { ToastService } from '@services/toast.service';

@Component({
  selector: 'app-librarian-orders-page',
  standalone: true,
  imports: [
    NavbarComponent,
    LibrarianOrderAssignComponent,
    LibrarianOrderDetailsComponent,
    NgClass,
    StatusLabelPipe,
    DatePipe,
    FormsModule,
  ],
  templateUrl: './librarian-orders-page.html',
  styleUrl: './librarian-orders-page.scss',
})
export class LibrarianOrdersPage implements OnInit {
  private readonly api = inject(LibrarianService);
  private readonly toastService = inject(ToastService);

  // Data
  orders = signal<LibrarianOrderListItem[]>([]);
  loading = signal(true);

  // Modals
  selectedAssignOrderId = signal<string | null>(null);
  selectedDetailsOrderId = signal<string | null>(null);

  // 🔥 ZAKŁADKI - ujednolicone opisy
  tabs = [
    {
      key: 'pending',
      label: 'Do obsługi',
      statuses: ['new'],
      statusOptions: [
        { value: '', label: 'Status: wszystkie' },
        { value: 'new', label: 'Status: nowe zamówienia' },
      ]
    },
    {
      key: 'active',
      label: 'Aktywne',
      statuses: ['ready_for_pickup', 'picked_up'],
      statusOptions: [
        { value: '', label: 'Status: wszystkie' },
        { value: 'ready_for_pickup', label: 'Status: gotowe do odbioru' },
        { value: 'picked_up', label: 'Status: wypożyczone' },
      ]
    },
    {
      key: 'returns',
      label: 'Zwroty',
      statuses: ['return_in_progress'],
      statusOptions: [
        { value: '', label: 'Status: wszystkie' },
        { value: 'return_in_progress', label: 'Status: do przyjęcia' },
      ]
    },
    {
      key: 'completed',
      label: 'Zakończone',
      statuses: ['returned'],
      statusOptions: [
        { value: '', label: 'Status: wszystkie' },
        { value: 'returned', label: 'Status: zwrócone' },
      ]
    },
  ];
  activeTab = signal<string>('pending');

  // 🔥 FILTROWANIE PO STATUSIE
  selectedStatusFilter = signal<string>('');

  // 🔥 SORTOWANIE - NOWE: jeden sygnał z 4 opcjami
  sortMode = signal<'date_desc' | 'date_asc' | 'reader_desc' | 'reader_asc'>('date_desc');

  // 🔥 WYSZUKIWANIE
  searchQuery = signal<string>('');

  // 🔥 COMPUTED - filtrowanie + sortowanie + wyszukiwanie
  displayedOrders = computed(() => {
    const active = this.activeTab();
    const tab = this.tabs.find(t => t.key === active);
    const statusFilter = this.selectedStatusFilter();
    const query = this.searchQuery().toLowerCase().trim();

    // Parse sortMode: ['date', 'desc']
    const [sortBy, sortDir] = this.sortMode().split('_') as ['date' | 'reader', 'asc' | 'desc'];

    // 1. Filtruj po zakładce
    let filtered = this.orders().filter(o => tab?.statuses.includes(o.status));

    // 2. Filtruj po konkretnym statusie (dropdown)
    if (statusFilter) {
      filtered = filtered.filter(o => o.status === statusFilter);
    }

    // 3. Wyszukiwanie
    if (query) {
      filtered = filtered.filter(o =>
        o.reader_first_name.toLowerCase().includes(query) ||
        o.reader_last_name.toLowerCase().includes(query) ||
        o.reader_email.toLowerCase().includes(query)
      );
    }

    // 4. Sortowanie
    filtered.sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'date') {
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else {
        const nameA = `${a.reader_first_name} ${a.reader_last_name}`;
        const nameB = `${b.reader_first_name} ${b.reader_last_name}`;
        comparison = nameA.localeCompare(nameB);
      }
      return sortDir === 'asc' ? comparison : -comparison;
    });

    return filtered;
  });

  tabCounts = computed(() => {
    const orders = this.orders();
    return this.tabs.map(tab => {
      const count = orders.filter(o => tab.statuses.includes(o.status)).length;
      return { ...tab, count };
    });
  });

  // Pobierz opcje statusów dla aktywnej zakładki
  get currentStatusOptions() {
    const tab = this.tabs.find(t => t.key === this.activeTab());
    return tab?.statusOptions || [];
  }

  ngOnInit() {
    this.loadOrders();
  }

  loadOrders() {
    this.loading.set(true);
    this.api.listOrders().subscribe({
      next: (res) => {
        this.orders.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading orders:', err);
        this.loading.set(false);
        this.toastService.show('Nie udało się pobrać listy zamówień', 'error');
      },
    });
  }

  switchTab(key: string) {
    this.activeTab.set(key);
    this.selectedStatusFilter.set('');
    this.searchQuery.set('');  // ✅ DODAJ: reset wyszukiwania
  }

  openOrderModal(order: LibrarianOrderListItem) {
    if (order.status === 'new') {
      this.selectedAssignOrderId.set(order.order_id);  // ✅ Assign modal
    } else {
      this.selectedDetailsOrderId.set(order.order_id); // ✅ Details modal
    }
  }

  closeAssign() {
    this.selectedAssignOrderId.set(null);
    setTimeout(() => this.loadOrders(), 300);
  }

  closeDetails() {
    this.selectedDetailsOrderId.set(null);
    setTimeout(() => this.loadOrders(), 300);
  }

  getButtonLabel(order: LibrarianOrderListItem): string {
    if (order.status === 'new') return 'Przypisz egzemplarze';
    return 'Szczegóły zamówienia';  // ✅ Spójne z logiką
  }

  formatOrderId(id: string): string {
    return `#${id.slice(-8).toUpperCase()}`;
  }

  statusClass(status: string) {
    return {
      "bg-blue-100 text-blue-700": status === "new",
      "bg-green-100 text-green-700": status === "ready_for_pickup",
      "bg-gray-200 text-gray-700": status === "picked_up",
      "bg-orange-100 text-orange-700": status === "return_in_progress",
      "bg-emerald-100 text-emerald-700": status === "returned",
    };
  }

  getSubStatusLabel(status: string): string {
    switch (status) {
      case 'ready_for_pickup': return 'Czeka na odbiór przez czytelnika';
      case 'picked_up': return 'Wypożyczone';
      case 'return_in_progress': return 'Książki w paczkomacie - do przyjęcia';
      default: return '';
    }
  }
}
