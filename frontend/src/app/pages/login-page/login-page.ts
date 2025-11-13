import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@services/auth.service';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  email = '';
  password = '';
  errorMessage = '';

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  onSubmit(): void {
    this.errorMessage = '';

    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.auth.getCurrentUser().subscribe({
          next: (user) => {
            const target = this.auth.getRedirectPathForRole(user.role);
            this.router.navigate([target]);
          },
          error: () => {
            this.errorMessage = 'Nie udało się pobrać danych użytkownika.';
          },
        });
      },
      error: () => {
        this.errorMessage = 'Nieprawidłowy adres e-mail lub hasło.';
      },
    });
  }
}
