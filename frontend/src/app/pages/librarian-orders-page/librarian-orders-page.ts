import { Component, inject, signal, OnInit } from '@angular/core';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { LibrarianService } from '@services/librarian.service';
import { LibrarianOrderListItem } from '@models/librarian';
import { NgClass, DatePipe } from '@angular/common';
import { StatusLabelPipe } from '@shared/status-label-pipe';

import {
  LibrarianOrderAssignComponent
} from '@pages/librarian-orders-page/components/librarian-order-assign/librarian-order-assign';

import {
  LibrarianOrderDetailsComponent
} from '@pages/librarian-orders-page/components/librarian-order-details/librarian-order-details';

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
  ],
  templateUrl: './librarian-orders-page.html',
  styleUrl: './librarian-orders-page.scss',
})
export class LibrarianOrdersPage implements OnInit {
  private readonly api = inject(LibrarianService);

  orders = signal<LibrarianOrderListItem[]>([]);
  loading = signal(true);

  selectedAssignOrderId = signal<string | null>(null);
  selectedDetailsOrderId = signal<string | null>(null);

  ngOnInit() {
    this.api.listOrders().subscribe({
      next: (res) => {
        this.orders.set(res);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  openOrderModal(order: LibrarianOrderListItem) {
    if (order.status === 'new') {
      this.selectedAssignOrderId.set(order.order_id);
    } else {
      this.selectedDetailsOrderId.set(order.order_id);
    }
  }

  closeAssign() {
    this.selectedAssignOrderId.set(null);
  }

  closeDetails() {
    this.selectedDetailsOrderId.set(null);
  }

  statusClass(status: string) {
    return {
      "bg-blue-100 text-blue-700": status === "new",
      "bg-indigo-100 text-indigo-700": status === "prepared",
      "bg-yellow-100 text-yellow-700": status === "in_transit",
      "bg-green-100 text-green-700": status === "ready_for_pickup",
      "bg-gray-200 text-gray-700": status === "picked_up",
      "bg-orange-100 text-orange-700": status === "return_in_progress",
      "bg-emerald-100 text-emerald-700": status === "returned",
      "bg-red-100 text-red-700": status === "canceled",
    };
  }
}
