/* Service worker — para que la ruta siga abriendo en el parqueadero de IDEO,
 * donde no hay señal.
 *
 * Estrategia: red primero, caché de respaldo. El sitio se regenera cada
 * semana, así que siempre se prefiere lo nuevo; la caché sólo entra cuando la
 * red falla. Nunca se sirve algo viejo teniendo conexión. */
var CACHE = 'remodelar-v1';

// Sólo el casco: lo demás se cachea solo a medida que se visita.
var ESENCIALES = [
  './',
  './index.html',
  './rutas/index.html',
  './directorio/index.html',
  './static/style.css',
  './static/buscador.js'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      // addAll falla entero si un archivo falla; acá cada uno va por su lado
      // para que un 404 no deje el sitio sin service worker.
      return Promise.all(ESENCIALES.map(function (u) {
        return c.add(u).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (nombres) {
      return Promise.all(nombres.map(function (n) {
        return n === CACHE ? null : caches.delete(n);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;

  var url = new URL(req.url);
  if (url.origin !== location.origin) return;  // fuentes, mapas: que pasen directo

  e.respondWith(
    fetch(req)
      .then(function (res) {
        if (res && res.status === 200) {
          var copia = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copia); });
        }
        return res;
      })
      .catch(function () {
        return caches.match(req).then(function (hit) {
          if (hit) return hit;
          // Navegación sin caché: al menos devolver la portada.
          if (req.mode === 'navigate') return caches.match('./index.html');
          return new Response('', { status: 504, statusText: 'Sin conexión' });
        });
      })
  );
});
