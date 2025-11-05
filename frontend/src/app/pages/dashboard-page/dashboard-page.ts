import { Component, inject, OnInit } from '@angular/core';
import { AuthService } from '@services/auth.service';
import { UserInfo } from '@models/auth';
import { Router } from '@angular/router';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage implements OnInit {
  user?: UserInfo;
  readonly auth = inject(AuthService);
  readonly router = inject(Router);

  ngOnInit() {
    this.auth.getCurrentUser().subscribe({
      next: (res) => (this.user = res),
    });
  }

  logout() {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/']),
      error: () => this.router.navigate(['/']),
    });
  }
}
