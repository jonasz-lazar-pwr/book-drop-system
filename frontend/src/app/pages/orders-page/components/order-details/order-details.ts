// order-details.ts
import { Component, Input, Output, EventEmitter, OnInit, inject, signal } from '@angular/core';
import { DatePipe, NgClass, NgOptimizedImage } from '@angular/common';
import { Order, Locker, LockerShipment } from '@models/order';
import { OrderService } from '@services/order.service';
import { StatusLabelPipe } from '@shared/pipes/status-label-pipe';
import { ToastService } from '@services/toast.service';
import QRCode from 'qrcode';

type ReturnStep = 'details' | 'select_locker';

@Component({
  selector: 'app-order-details',
  standalone: true,
  imports: [DatePipe, NgOptimizedImage, StatusLabelPipe, NgClass],
  templateUrl: './order-details.html',
  styleUrl: './order-details.scss',
})
export class OrderDetails implements OnInit {
  private readonly orderService = inject(OrderService);
  private readonly toastService = inject(ToastService);

  @Input({ required: true }) order!: Order;
  @Output() closed = new EventEmitter<void>();
  @Output() orderUpdated = new EventEmitter<void>();

  returnStep = signal<ReturnStep>('details');
  lockers = signal<Locker[]>([]);
  selectedLocker = signal<Locker | null>(null);
  loadingLockers = signal(false);
  processingAction = signal(false);

  pickupQrCode = signal<string>('');
  returnQrCode = signal<string>('');

  ngOnInit(): void {
    console.log('Order:', this.order.id, 'Status:', this.order.status);
    console.log('Shipment:', this.order.shipment);

    if (this.order.shipment?.pickup_code) {
      console.log('Pickup code:', this.order.shipment.pickup_code);
      console.log('Mode:', this.order.shipment.mode);

      if (this.order.shipment.mode === 'return') {
        console.log('🔄 Generating RETURN QR');
        this.generateQRCode(this.order.shipment.pickup_code, 'return');
      } else if (this.order.shipment.mode === 'delivery') {
        console.log('📬 Generating PICKUP QR');
        this.generateQRCode(this.order.shipment.pickup_code, 'pickup');
      } else {
        console.warn('Unknown shipment mode:', this.order.shipment.mode);
      }
    } else {
      console.warn('No shipment or pickup_code available');
    }
  }


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

  formatOrderId(id: string): string {
    return `#${id.slice(-8).toUpperCase()}`;
  }

  getDaysRemaining(dueDate: string): number {
    const now = new Date();
    const due = new Date(dueDate);
    const diff = due.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  isOverdue(dueDate: string): boolean {
    return this.getDaysRemaining(dueDate) < 0;
  }

  getPickupDeadline(placedAt: string | undefined): Date | null {
    if (!placedAt) return null;
    const placed = new Date(placedAt);
    const deadline = new Date(placed);
    deadline.setHours(deadline.getHours() + 48);
    return deadline;
  }

  // ✅ POPRAWIONE - Pokazuj QR/przycisk TYLKO jeśli status = 'created'
  canShowReturnQR(): boolean {
    return (
      this.order.status === 'return_in_progress' &&
      this.order.shipment?.mode === 'return' &&
      this.order.shipment?.status === 'created'  // ✅ ZMIENIONE z !== 'completed'
    );
  }

  generateQRCode(code: string, type: 'pickup' | 'return'): void {
    QRCode.toDataURL(code, {
      width: 200,
      margin: 1,
      color: {
        dark: '#000000',
        light: '#FFFFFF',
      },
    })
      .then((qrDataUrl) => {
        if (type === 'pickup') {
          this.pickupQrCode.set(qrDataUrl);
        } else {
          this.returnQrCode.set(qrDataUrl);
        }
      })
      .catch((err) => {
        console.error('Error generating QR code:', err);
      });
  }

  async copyCode(code: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(code);
      this.toastService.show('Kod skopiowany do schowka!', 'success');
    } catch (err) {
      console.error('Failed to copy:', err);
      this.toastService.show('Nie udało się skopiować kodu', 'error');
    }
  }

  close(): void {
    this.closed.emit();
  }

  confirmPickup(): void {
    if (this.processingAction()) return;

    this.processingAction.set(true);
    this.orderService.confirmPickup(this.order.id).subscribe({
      next: () => {
        this.processingAction.set(false);
        this.toastService.show('Odbiór potwierdzony! Miłej lektury!', 'success');
        this.orderUpdated.emit();
        this.close();
      },
      error: (err) => {
        console.error('Error confirming pickup:', err);
        this.processingAction.set(false);
        this.toastService.show('Wystąpił błąd podczas potwierdzania odbioru', 'error');
      },
    });
  }

  startReturn(): void {
    this.returnStep.set('select_locker');
    this.loadingLockers.set(true);

    this.orderService.getLockers().subscribe({
      next: (lockers) => {
        this.lockers.set(lockers);
        this.loadingLockers.set(false);
      },
      error: (err) => {
        console.error('Error loading lockers:', err);
        this.loadingLockers.set(false);
        this.toastService.show('Nie udało się pobrać listy książkomatów', 'error');
        this.returnStep.set('details');
      },
    });
  }

  selectLocker(locker: Locker): void {
    this.selectedLocker.set(locker);
  }

  confirmLockerSelection(): void {
    const locker = this.selectedLocker();
    if (!locker || this.processingAction()) return;

    this.processingAction.set(true);

    this.orderService.initiateReturn(this.order.id, locker.id).subscribe({
      next: (shipment: LockerShipment) => {
        this.order.shipment = shipment;
        this.order.status = 'return_in_progress';
        this.processingAction.set(false);

        // ✅ ZMIENIONE - toast + zamknij modal + odśwież
        this.toastService.show('Zwrot zainicjowany!', 'success');
        this.orderUpdated.emit();  // Odśwież listę zamówień
        this.close();              // Zamknij modal
      },
      error: (err) => {
        console.error('Error initiating return:', err);
        this.processingAction.set(false);
        this.toastService.show('Wystąpił błąd podczas inicjalizacji zwrotu', 'error');
      },
    });
  }

  cancelLockerSelection(): void {
    this.returnStep.set('details');
    this.selectedLocker.set(null);
  }

  confirmReturn(): void {
    if (this.processingAction()) return;

    this.processingAction.set(true);
    this.orderService.confirmReturn(this.order.id).subscribe({
      next: () => {
        this.processingAction.set(false);
        this.toastService.show('Zwrot potwierdzony! Dziękujemy!', 'success');
        this.orderUpdated.emit();
        this.close();
      },
      error: (err) => {
        console.error('Error confirming return:', err);
        this.processingAction.set(false);
        this.toastService.show('Wystąpił błąd podczas potwierdzania zwrotu', 'error');
      },
    });
  }

  backToDetails(): void {
    this.returnStep.set('details');
  }

  getGroupedItems() {
    const grouped = new Map<string, { item: any; quantity: number }>();

    this.order.items.forEach((item) => {
      const existing = grouped.get(item.isbn);
      if (existing) {
        existing.quantity++;
      } else {
        grouped.set(item.isbn, { item, quantity: 1 });
      }
    });

    return Array.from(grouped.values());
  }
}
