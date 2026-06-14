// src/app/shared/services/toast.service.ts
import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  message: string;
  type: ToastType;
  id: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  private toastSignal = signal<Toast | null>(null);
  toast = this.toastSignal.asReadonly();

  private idCounter = 0;

  show(message: string, type: ToastType = 'info'): void {
    const id = ++this.idCounter;
    this.toastSignal.set({ message, type, id });

    // Auto-hide po 3.5s
    setTimeout(() => {
      if (this.toastSignal()?.id === id) {
        this.hide();
      }
    }, 3500);
  }

  hide(): void {
    this.toastSignal.set(null);
  }
}
