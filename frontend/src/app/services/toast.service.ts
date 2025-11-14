import { Injectable, signal } from '@angular/core';
import { Toast } from '@models/toast';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private counter = 0;
  toasts = signal<Toast[]>([]);

  show(message: string, type: Toast['type'] = 'info', duration = 2500) {
    const id = ++this.counter;
    const toast: Toast = { id, message, type };
    this.toasts.update((t) => [...t, toast]);

    setTimeout(() => this.remove(id), duration);
  }

  remove(id: number) {
    this.toasts.update((t) => t.filter((toast) => toast.id !== id));
  }

  clear() {
    this.toasts.set([]);
  }
}
