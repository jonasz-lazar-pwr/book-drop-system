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
import { LibrarianOrderDetails } from '@models/librarian';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-librarian-order-assign',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './librarian-order-assign.html',
  styleUrl: './librarian-order-assign.scss',
})
export class LibrarianOrderAssignComponent implements OnInit {
  private readonly api = inject(LibrarianService);

  @Input() orderId!: string;
  @Output() closed = new EventEmitter<void>();

  loading = signal(true);
  data = signal<LibrarianOrderDetails | null>(null);

  // Stores selected book_item IDs for each ISBN
  selected = signal<Record<string, string[]>>({});

  ngOnInit() {
    // Load order details and initialize empty selections
    this.api.getOrderDetails(this.orderId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);

        const init: Record<string, string[]> = {};
        res.books.forEach((b) => {
          init[b.isbn] = new Array(b.quantity).fill('');
        });

        this.selected.set(init);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  // Update dropdown selection for given ISBN and index
  updateSelection(isbn: string, idx: number, value: string) {
    const copy = structuredClone(this.selected());
    copy[isbn][idx] = value;
    this.selected.set(copy);
  }

  // Generate array of indexes for [0..count-1]
  getIndexes(count: number): number[] {
    return Array.from({ length: count }, (_, i) => i);
  }

  // Submit assigned items to backend
  assignItems() {
    const body = {
      items: Object.entries(this.selected()).map(([isbn, ids]) => ({
        isbn,
        book_item_ids: ids.filter((x) => x),
      })),
    };

    this.api.assignItems(this.orderId, body).subscribe({
      next: () => {
        this.closed.emit();
      },
      error: () => {
      },
    });
  }
}
