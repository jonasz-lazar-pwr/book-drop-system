import { Component, Input, Output, EventEmitter, signal, OnChanges, inject } from '@angular/core';
import { DatePipe, NgOptimizedImage } from '@angular/common';
import { Book } from '@models/catalog';
import { CartService } from '@services/cart.service';
import { ToastService } from '@services/toast.service';
import { catchError, finalize, of } from 'rxjs';

@Component({
  selector: 'app-book-details',
  imports: [NgOptimizedImage, DatePipe],
  templateUrl: './book-details.html',
  styleUrl: './book-details.scss',
})
export class BookDetails implements OnChanges {
  private readonly cart = inject(CartService);
  private readonly toast = inject(ToastService);

  @Input() book!: Book;
  @Input() cartItems = new Set<string>();
  @Output() closed = new EventEmitter<void>();

  loading = signal(true);
  adding = signal(false);

  ngOnChanges(): void {
    if (this.book) this.loading.set(false);
  }

  addToCart(): void {
    if (!this.book || this.adding() || this.cartItems.has(this.book.isbn)) return;

    this.adding.set(true);
    this.cart
      .addItem({ isbn: this.book.isbn })
      .pipe(
        catchError((err) => {
          console.error('Error adding to cart:', err);
          this.toast.show('Nie udało się dodać książki do koszyka.', 'error');
          return of(null);
        }),
        finalize(() => this.adding.set(false)),
      )
      .subscribe((res) => {
        if (res) {
          this.toast.show(`Dodano "${this.book.title}" do koszyka.`, 'success');
          this.cartItems.add(this.book.isbn);
        }
      });
  }
}
