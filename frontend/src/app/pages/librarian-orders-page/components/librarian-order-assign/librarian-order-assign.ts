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
import { ToastService } from '@services/toast.service';  // ✅ DODAJ
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
  private readonly toastService = inject(ToastService);  // ✅ DODAJ

  @Input() orderId!: string;
  @Output() closed = new EventEmitter<void>();

  loading = signal(true);
  submitting = signal(false);  // ✅ DODAJ
  data = signal<LibrarianOrderDetails | null>(null);
  selected = signal<Record<string, string[]>>({});

  ngOnInit() {
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
      error: (err) => {
        console.error('Error loading order details:', err);
        this.loading.set(false);
        this.toastService.show('Nie udało się pobrać szczegółów zamówienia', 'error');
        this.closed.emit();  // Zamknij modal przy błędzie
      },
    });
  }

  updateSelection(isbn: string, idx: number, value: string) {
    const copy = structuredClone(this.selected());
    copy[isbn][idx] = value;
    this.selected.set(copy);
  }

  getIndexes(count: number): number[] {
    return Array.from({ length: count }, (_, i) => i);
  }

  // ✅ SPRAWDŹ CZY WSZYSTKIE EGZEMPLARZE WYBRANE
  canSubmit(): boolean {
    const sel = this.selected();
    return Object.values(sel).every(ids => ids.every(id => id !== ''));
  }

  assignItems() {
    if (this.submitting() || !this.canSubmit()) return;

    const body = {
      items: Object.entries(this.selected()).map(([isbn, ids]) => ({
        isbn,
        book_item_ids: ids.filter((x) => x),
      })),
    };

    this.submitting.set(true);

    this.api.assignItems(this.orderId, body).subscribe({
      next: () => {
        this.submitting.set(false);
        this.toastService.show('Egzemplarze przypisane! Zamówienie gotowe do odbioru', 'success');
        this.closed.emit();
      },
      error: (err) => {
        console.error('Error assigning items:', err);
        this.submitting.set(false);

        // ✅ Obsługa specyficznych błędów
        const errorMsg = err.error?.detail || 'Nie udało się przypisać egzemplarzy';
        this.toastService.show(errorMsg, 'error');
      },
    });
  }
}
