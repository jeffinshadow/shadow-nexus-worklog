// Service Worker minimo: habilita a instalacao como PWA sem cache offline.
// Um handler de 'fetch' (mesmo pass-through) satisfaz o criterio de
// instalabilidade do Chrome; nao interceptamos nada, entao tudo vai pela rede
// normalmente e nao ha risco de servir versao obsoleta (cache continua no nginx).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => { /* pass-through: sem cache */ });
