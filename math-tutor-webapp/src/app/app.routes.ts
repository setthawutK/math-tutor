import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'chat',
    loadComponent: () => import('./modules/chat-page/chat-page').then((m) => m.ChatPage),
  },
  {
    path: '',
    redirectTo: 'chat',
    pathMatch: 'full',
  },
];
