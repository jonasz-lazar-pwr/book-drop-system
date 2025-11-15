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
import { LibrarianOrderSummary } from '@models/librarian';

import { DatePipe, NgClass } from '@angular/common';
import { StatusLabelPipe } from '@shared/status-label-pipe';

@Component({
  selector: 'app-librarian-order-details',
  standalone: true,
  templateUrl: './librarian-order-details.html',
  styleUrl: './librarian-order-details.scss',
  imports: [DatePipe, NgClass, StatusLabelPipe],
})
export class LibrarianOrderDetailsComponent implements OnInit {
  private readonly api = inject(LibrarianService);

  @Input() orderId!: string;
  @Output() closed = new EventEmitter<void>();

  loading = signal(true);
  data = signal<LibrarianOrderSummary | null>(null);

  ngOnInit() {
    // Load summary details for non-"new" orders
    this.api.getOrderSummary(this.orderId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  // Allow modal close via keyboard (Enter / Space)
  onKey(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      this.closed.emit();
    }
  }

  // Status badge color mapping
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
}
