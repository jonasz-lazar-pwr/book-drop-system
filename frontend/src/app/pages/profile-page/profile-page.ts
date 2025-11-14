import { Component, inject } from '@angular/core';
import { NavbarComponent } from '@shared/navbar/navbar.component';
import { AuthService } from '@services/auth.service';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-profile-page',
  imports: [NavbarComponent, AsyncPipe],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage {
  private readonly auth = inject(AuthService);
  readonly user$ = this.auth.getCurrentUser();
}
