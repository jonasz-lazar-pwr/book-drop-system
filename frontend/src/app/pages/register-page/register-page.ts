import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@services/auth.service';

@Component({
  selector: 'app-register-page',
  imports: [FormsModule, RouterLink],
  templateUrl: './register-page.html',
  styleUrl: './register-page.scss',
})
export class RegisterPage {
  email = '';
  password = '';
  first_name = '';
  last_name = '';
  errorMessage = '';

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  onSubmit(): void {
    this.errorMessage = '';

    this.auth
      .register({
        email: this.email,
        password: this.password,
        first_name: this.first_name,
        last_name: this.last_name,
      })
      .subscribe({
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
          this.errorMessage =
            'Rejestracja nie powiodła się. Sprawdź dane i spróbuj ponownie.';
        },
      });
  }
}
