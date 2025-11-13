import { Component, inject } from '@angular/core';
import { Navbar } from '@shared/navbar/navbar';
import { AuthService } from '@services/auth.service';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-profile-page',
  imports: [Navbar, AsyncPipe],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage {
  private readonly auth = inject(AuthService);
  readonly user$ = this.auth.getCurrentUser();
}
