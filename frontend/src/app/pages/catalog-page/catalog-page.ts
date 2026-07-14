import { Component, signal, inject, computed, HostListener } from '@angular/core';
import { DatePipe, NgOptimizedImage } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { catchError, finalize, of, Subject, debounceTime } from 'rxjs';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { CatalogService } from '@services/catalog.service';
import { CartService } from '@services/cart.service';
import { Book } from '@models/catalog';
import { BookDetails } from '@pages/catalog-page/components/book-details/book-details';

@Component({
  selector: 'app-catalog-page',
  imports: [NavbarComponent, DatePipe, NgOptimizedImage, FormsModule, BookDetails],
  templateUrl: './catalog-page.html',
  styleUrl: './catalog-page.scss',
})
export class CatalogPage {
  private readonly catalog = inject(CatalogService);
  private readonly cart = inject(CartService);

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
  addingToCart = signal<string | null>(null);
  cartItems = signal<Set<string>>(new Set());

  totalPages = computed(() => Math.ceil(this.total() / this.limit));
  isSearching = computed(() => this.search().trim().length > 0);

  constructor() {
    this.loadBooks();
    this.loadPublishers();
    this.loadCartItems();

    this.searchSubject.pipe(debounceTime(500)).subscribe((term) => {
      this.search.set(term);
      this.page.set(1);
      this.loadBooks();
    });
  }

  private loadCartItems() {
    this.cart.getCart()
      .pipe(catchError(() => of(null)))
      .subscribe((res) => {
        if (res?.items) {
          const isbns = new Set(res.items.map((i) => i.isbn));
          this.cartItems.set(isbns);
        }
      });
  }

  // --- Load paginated book list ---
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

  // --- Load available publishers ---
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

  // --- Handle search input ---
  onSearch(event: Event) {
    const target = event.target as HTMLInputElement | null;
    const term = target?.value?.trim() || '';
    this.searchSubject.next(term);
  }

  // --- Handle sorting change ---
  onSortChange(event: Event) {
    const target = event.target as HTMLSelectElement | null;
    this.sort.set(target?.value || '');
    this.loadBooks();
  }

  // --- Apply filters from panel ---
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

  // --- Pagination controls ---
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

  // --- Format author names ---
  formatAuthors(authors: string): string {
    if (!authors) return '';
    const parts = authors.split(',').map((a) => a.trim());
    if (parts.length <= 2) return parts.join(', ');
    return `${parts.slice(0, 2).join(', ')} i inni`;
  }

  // --- Open modal with book details ---
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

  // --- Add book to cart ---
  addToCart(event: MouseEvent, book: Book) {
    event.stopPropagation();

    if (this.addingToCart() === book.isbn || this.cartItems().has(book.isbn)) {
      return;
    }

    this.addingToCart.set(book.isbn);
    this.cart
      .addItem({ isbn: book.isbn })
      .pipe(
        catchError((err) => {
          console.error('Error adding to cart:', err);
          return of(null);
        }),
        finalize(() => this.addingToCart.set(null)),
      )
      .subscribe((res) => {
        if (res) {
          this.loadCartItems();
        }
      });
  }

  // --- Close filter panel on outside click ---
  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: MouseEvent) {
    if (!this.filterPanelOpen()) return;
    const target = event.target as HTMLElement;
    const insidePanel = target.closest('.filter-panel');
    const button = target.closest('.filter-toggle-btn');
    if (!insidePanel && !button) this.filterPanelOpen.set(false);
  }
}
