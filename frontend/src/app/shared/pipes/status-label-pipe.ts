import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'statusLabel',
  standalone: true,
})
export class StatusLabelPipe implements PipeTransform {
  transform(value: string): string {
    switch (value) {
      case 'new':
        return 'Nowe';
      case 'prepared':
        return 'Przygotowane';
      case 'in_transit':
        return 'W drodze';
      case 'ready_for_pickup':
        return 'Gotowe do odbioru';
      case 'picked_up':
        return 'Odebrane';
      case 'return_in_progress':
        return 'Zwrot w toku';
      case 'returned':
        return 'Zwrócone';
      case 'canceled':
        return 'Anulowane';
      default:
        return value;
    }
  }
}
