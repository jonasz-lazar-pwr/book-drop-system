import { Component, inject } from '@angular/core';
import { NgClass } from '@angular/common';
import { ToastService } from '@services/toast.service';

@Component({
  selector: 'app-toast',
  imports: [NgClass],
  templateUrl: './toast.component.html',
  styleUrl: './toast.component.scss',
})
export class ToastComponent {
  readonly toastService = inject(ToastService);
}
