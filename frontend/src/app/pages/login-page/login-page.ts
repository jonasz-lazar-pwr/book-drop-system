import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@services/auth.service';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  email = '';
  password = '';

  readonly auth = inject(AuthService);
  readonly router = inject(Router);

  onSubmit() {
    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        setTimeout(() => {
          this.auth.getCurrentUser().subscribe({
            next: (user) => {
              console.log('Zalogowano jako:', user.email, 'rola:', user.role);
              this.router.navigate(['/dashboard']);
            },
            error: () => {
              alert('Nie udało się pobrać danych użytkownika.');
            },
          });
        }, 50);
      },
      error: () => {
        alert('Błędny email lub hasło');
      },
    });
  }
}
