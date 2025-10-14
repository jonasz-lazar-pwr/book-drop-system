import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';

fetch('/assets/config/app.config.js')
  .then((resp) => {
    if (!resp.ok) throw new Error('Failed to load runtime config');
    return resp.text();
  })
  .then((jsContent) => {
    const script = document.createElement('script');
    script.textContent = jsContent;
    document.head.appendChild(script);

    return bootstrapApplication(AppComponent, {
      providers: [provideHttpClient(withInterceptorsFromDi()), provideRouter(routes)],
    });
  })
  .catch(() => {
    bootstrapApplication(AppComponent, {
      providers: [provideHttpClient(withInterceptorsFromDi()), provideRouter(routes)],
    });
  });
