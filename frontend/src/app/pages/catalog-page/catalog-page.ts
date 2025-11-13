import { Component, signal, inject, computed, HostListener } from '@angular/core';
import { DatePipe, NgOptimizedImage } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { catchError, finalize, of, Subject, debounceTime } from 'rxjs';
import { Navbar } from '@shared/navbar/navbar';
import { CatalogService } from '@services/catalog.service';
import { Book } from '@models/catalog';
import { BookDetails } from '@pages/catalog-page/components/book-details/book-details';

@Component({
  selector: 'app-catalog-page',
  imports: [Navbar, DatePipe, NgOptimizedImage, FormsModule, BookDetails],
  templateUrl: './catalog-page.html',
  styleUrl: './catalog-page.scss',
})
export class CatalogPage {
  private readonly catalog = inject(CatalogService);
  private bookCache = new Map<string, Book>();
  private searchSubject = new Subject<string>();

  books = signal<Book[]>([]);
  total = signal(0);
  page = signal(1);
  limit = 15;
  search = signal('');
  sort = signal('');
  filters = signal<{ publisher?: string; availableOnly?: boolean; yearFrom?: number; yearTo?: number }>({});
  filterPanelOpen = signal(false);
  loading = signal(true);
  publishers = signal<string[]>([]);
  selectedBook = signal<Book | null>(null);

  totalPages = computed(() => Math.ceil(this.total() / this.limit));

  constructor() {
    this.loadBooks();
    this.loadPublishers();

    // Debounced search (500 ms)
    this.searchSubject.pipe(debounceTime(500)).subscribe((term) => {
      this.search.set(term);
      this.page.set(1);
      this.loadBooks();
    });
  }

  // Load paginated book list
  loadBooks() {
    this.loading.set(true);
    this.catalog
      .getBooks(this.page(), this.limit, this.search(), this.sort(), this.filters())
      .pipe(
        catchError((err) => {
          console.error('Error loading books:', err);
          return of({ items: [], total: 0 });
        }),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((res) => {
        this.books.set(res.items);
        this.total.set(res.total);
      });
  }

  // Load available publishers
  loadPublishers() {
    this.catalog
      .getPublishers()
      .pipe(
        catchError((err) => {
          console.error('Error loading publishers:', err);
          return of([] as string[]);
        }),
      )
      .subscribe((pubs) => this.publishers.set(pubs));
  }

  // Handle search input
  onSearch(event: Event) {
    const target = event.target as HTMLInputElement | null;
    const term = target?.value?.trim() || '';
    this.searchSubject.next(term);
  }

  // Handle sorting change
  onSortChange(event: Event) {
    const target = event.target as HTMLSelectElement | null;
    this.sort.set(target?.value || '');
    this.loadBooks();
  }

  // Apply filters from the filter panel
  toggleFilterPanel() {
    this.filterPanelOpen.update((v) => !v);
  }

  applyFiltersFromPanel(form: NgForm) {
    const values = form.value;
    const publisher = values.publisher || '';
    const availableOnly = !!values.available;
    const yearFrom = values.yearFrom ? Number(values.yearFrom) : undefined;
    const yearTo = values.yearTo ? Number(values.yearTo) : undefined;

    this.filters.set({ publisher, availableOnly, yearFrom, yearTo });
    this.page.set(1);
    this.loadBooks();
    this.filterPanelOpen.set(false);
  }

  // Pagination controls
  nextPage() {
    if (this.page() < this.totalPages()) {
      this.page.update((p) => p + 1);
      this.loadBooks();
    }
  }

  prevPage() {
    if (this.page() > 1) {
      this.page.update((p) => p - 1);
      this.loadBooks();
    }
  }

  // Format author names
  formatAuthors(authors: string): string {
    if (!authors) return '';
    const parts = authors.split(',').map((a) => a.trim());
    if (parts.length <= 2) return parts.join(', ');
    return `${parts.slice(0, 2).join(', ')} i inni`;
  }

  // Open modal with book details
  openBookDetails(book: Book) {
    const cached = this.bookCache.get(book.isbn);
    if (cached) {
      this.selectedBook.set(cached);
      return;
    }

    this.selectedBook.set({ ...book, description: '', available_count: 0 });

    this.catalog
      .getBookDetails(book.isbn)
      .pipe(
        catchError((err) => {
          console.error('Error fetching book details:', err);
          this.selectedBook.set(null);
          return of(null);
        }),
      )
      .subscribe((details) => {
        if (details) {
          this.bookCache.set(book.isbn, details);
          this.selectedBook.set(details);
        }
      });
  }

  closeBookDetails() {
    this.selectedBook.set(null);
  }

  // Simulate adding a book to cart
  addToCart(event: MouseEvent, book: Book) {
    event.stopPropagation();
    console.log(`Added to cart: ${book.title} (${book.isbn})`);
  }

  // Close filter panel on outside click
  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: MouseEvent) {
    if (!this.filterPanelOpen()) return;
    const target = event.target as HTMLElement;
    const insidePanel = target.closest('.filter-panel');
    const button = target.closest('.filter-toggle-btn');
    if (!insidePanel && !button) this.filterPanelOpen.set(false);
  }
}
