import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

fetch('/assets/config/app.config.js')
  .then(async (resp) => {
    if (!resp.ok) throw new Error('Failed to load runtime config');

    const jsContent = await resp.text();
    const script = document.createElement('script');
    script.textContent = jsContent;
    document.head.appendChild(script);

    await bootstrapApplication(App, appConfig);
  })
  .catch(async (err) => {
    console.warn('Runtime config not found — using defaults.', err);
    await bootstrapApplication(App, appConfig);
  });
