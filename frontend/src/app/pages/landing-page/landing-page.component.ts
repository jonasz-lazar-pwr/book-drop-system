import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '@services/auth.service';

@Component({
  selector: 'app-landing-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss'],
})
export class LandingPageComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  // ngOnInit(): void {
  //   // if (this.authService.isAuthenticated()) {
  //   //   this.router.navigate(['/dashboard']);
  //   // }
  // }
}
