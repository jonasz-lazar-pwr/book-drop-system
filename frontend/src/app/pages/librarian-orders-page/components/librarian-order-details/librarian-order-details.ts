import {
  Component,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
  OnInit,
} from '@angular/core';

import { LibrarianService } from '@services/librarian.service';
import { ToastService } from '@services/toast.service';
import { LibrarianOrderSummary } from '@models/librarian';

import { DatePipe, NgClass } from '@angular/common';
import { StatusLabelPipe } from '@shared/pipes/status-label-pipe';

@Component({
  selector: 'app-librarian-order-details',
  standalone: true,
  templateUrl: './librarian-order-details.html',
  styleUrl: './librarian-order-details.scss',
  imports: [DatePipe, NgClass, StatusLabelPipe],
})
export class LibrarianOrderDetailsComponent implements OnInit {
  private readonly api = inject(LibrarianService);
  private readonly toastService = inject(ToastService);

  @Input() orderId!: string;
  @Output() closed = new EventEmitter<void>();

  loading = signal(true);
  accepting = signal(false);
  data = signal<LibrarianOrderSummary | null>(null);

  ngOnInit() {
    this.api.getOrderSummary(this.orderId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading order summary:', err);
        this.loading.set(false);
        this.toastService.show('Nie udało się pobrać szczegółów zamówienia', 'error');
        this.closed.emit();
      },
    });
  }

  acceptReturn() {
    if (this.accepting()) return;

    this.accepting.set(true);

    this.api.acceptReturn(this.orderId).subscribe({
      next: () => {
        this.accepting.set(false);
        this.toastService.show('Zwrot przyjęty! Książki są ponownie dostępne.', 'success');
        this.closed.emit();
      },
      error: (err) => {
        console.error('Error accepting return:', err);
        this.accepting.set(false);

        const errorMsg = err.error?.detail || 'Nie udało się przyjąć zwrotu';
        this.toastService.show(errorMsg, 'error');
      },
    });
  }

  formatOrderId(id: string): string {
    return `#${id.slice(-8).toUpperCase()}`;
  }

  onKey(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      this.closed.emit();
    }
  }

  statusClass(status: string) {
    return {
      'bg-blue-100 text-blue-700': status === 'new',
      'bg-green-100 text-green-700': status === 'ready_for_pickup',
      'bg-gray-200 text-gray-700': status === 'picked_up',
      'bg-orange-100 text-orange-700': status === 'return_in_progress',
      'bg-emerald-100 text-emerald-700': status === 'returned',
    };
  }
}
