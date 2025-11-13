import { Component, Input, Output, EventEmitter, signal, OnChanges } from '@angular/core';
import { DatePipe, NgOptimizedImage } from '@angular/common';
import { Book } from '@models/catalog';

@Component({
  selector: 'app-book-details',
  imports: [NgOptimizedImage, DatePipe],
  templateUrl: './book-details.html',
  styleUrl: './book-details.scss',
})
export class BookDetails implements OnChanges {
  @Input() book!: Book;
  @Output() closed = new EventEmitter<void>();
  loading = signal(true);

  ngOnChanges(): void {
    if (this.book) this.loading.set(false);
  }

  addToCart(): void {
    console.log(`Added to cart: ${this.book.title}`); // future backend integration
  }
}
