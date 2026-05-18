// Service Worker para PWA - Monitor IoT
const CACHE_NAME = 'monitor-iot-v1.0.0';
const urlsToCache = [
  '/',
  '/index.html',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
  'https://esm.sh/@supabase/supabase-js@2.45.0'
];

// Instalación del Service Worker
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Cache abierto');
        return cache.addAll(urlsToCache);
      })
      .catch((error) => {
        console.error('[Service Worker] Error al cachear:', error);
      })
  );
  self.skipWaiting(); // Activar inmediatamente el nuevo service worker
});

// Activación del Service Worker
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activando...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Eliminando cache antigua:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim(); // Tomar control de todas las páginas
});

// Estrategia: Network First, fallback a Cache
self.addEventListener('fetch', (event) => {
  // Solo cachear requests GET
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clonar la respuesta porque solo se puede usar una vez
        const responseToCache = response.clone();

        // Cachear recursos estáticos
        if (event.request.url.includes('.html') || 
            event.request.url.includes('.js') || 
            event.request.url.includes('.css') ||
            event.request.url.includes('icons/')) {
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }

        return response;
      })
      .catch(() => {
        // Si falla la red, buscar en cache
        return caches.match(event.request).then((response) => {
          if (response) {
            return response;
          }
          
          // Si es una página HTML y no está en cache, devolver index.html
          const acceptHeader = event.request.headers.get('accept');
          if (acceptHeader && acceptHeader.includes('text/html')) {
            return caches.match('/index.html');
          }
        });
      })
  );
});

// Notificaciones push (para uso futuro)
self.addEventListener('push', (event) => {
  console.log('[Service Worker] Push recibido:', event);
  // Aquí se pueden agregar notificaciones push en el futuro
});

