import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@services/auth.service';

@Component({
  selector: 'app-register-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './register-page.html',
  styleUrl: './register-page.scss',
})
export class RegisterPage {
  email = '';
  password = '';
  first_name = '';
  last_name = '';

  readonly auth = inject(AuthService);
  readonly router = inject(Router);

  onSubmit() {
    this.auth
      .register({
        email: this.email,
        password: this.password,
        first_name: this.first_name,
        last_name: this.last_name,
      })
      .subscribe({
        next: () => {
          setTimeout(() => {
            this.auth.getCurrentUser().subscribe({
              next: (user) => {
                console.log('Zarejestrowano jako:', user.email, 'rola:', user.role);
                this.router.navigate(['/dashboard']);
              },
              error: () => alert('Nie udało się pobrać danych użytkownika po rejestracji.'),
            });
          }, 50);
        },
        error: () => alert('Nie udało się zarejestrować — sprawdź dane i spróbuj ponownie.'),
      });
  }
}
