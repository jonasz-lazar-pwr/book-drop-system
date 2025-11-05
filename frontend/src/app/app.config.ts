import { ApplicationConfig, EnvironmentInjector, inject, runInInjectionContext } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { authInterceptor } from '@interceptors/auth-interceptor';
import { TokenMonitorService } from '@services/token-monitor.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    {
      provide: 'APP_INITIALIZER',
      multi: true,
      useFactory: () => {
        const injector = inject(EnvironmentInjector);
        return () => {
          runInInjectionContext(injector, () => inject(TokenMonitorService));
        };
      },
    },
  ],
};
