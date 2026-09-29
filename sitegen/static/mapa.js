/* Mapa de una ruta: paradas numeradas y el trazado entre ellas.
 *
 * Leaflet + OpenStreetMap: sin llave de API y sin costo. Los datos de cada
 * parada vienen incrustados en la página (#datos-ruta), así que el mapa no
 * pide nada al servidor: abre igual con mala señal, que es la situación
 * real de quien está haciendo la ruta. */
(function () {
  'use strict';

  var nodo = document.getElementById('mapa');
  var datos = document.getElementById('datos-ruta');
  if (!nodo || !datos || typeof L === 'undefined') return;

  var paradas = JSON.parse(datos.textContent);
  if (paradas.length < 2) return;

  var mapa = L.map(nodo, { scrollWheelZoom: false, zoomControl: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(mapa);

  var capa = L.layerGroup().addTo(mapa);
  var orden = paradas.slice();

  function icono(n, enIdeo) {
    return L.divIcon({
      className: '',
      html: '<span class="pin' + (enIdeo ? ' pin--ideo' : '') + '">' + n + '</span>',
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    });
  }

  function pintar() {
    capa.clearLayers();
    var puntos = [];
    orden.forEach(function (p, i) {
      var ll = [p.lat, p.lng];
      puntos.push(ll);
      L.marker(ll, { icon: icono(i + 1, p.ideo) })
        .bindPopup('<strong>' + p.nombre + '</strong><br>' + p.direccion +
                   '<br><a href="' + p.maps + '" target="_blank" rel="noopener">Cómo llegar</a>')
        .addTo(capa);
    });
    L.polyline(puntos, { color: '#e4007c', weight: 3, opacity: 0.9, dashArray: '1 8', lineCap: 'round' }).addTo(capa);
    mapa.fitBounds(L.latLngBounds(puntos).pad(0.15));
  }

  // Distancia en km entre dos puntos (Haversine). Suficiente: sirve para
  // ordenar, no para calcular un recorrido real de manejo.
  function dist(a, b) {
    var R = 6371, dLat = (b[0] - a[0]) * Math.PI / 180, dLon = (b[1] - a[1]) * Math.PI / 180;
    var la1 = a[0] * Math.PI / 180, la2 = b[0] * Math.PI / 180;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(la1) * Math.cos(la2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  /* Reordena empezando por la parada más cercana a quien mira, y de ahí
   * encadena por vecino más próximo. Ojo: el orden editorial existe por algo
   * — el enchape antes que el sanitario — así que esto NO es el modo por
   * defecto; se activa a pedido y se puede deshacer. */
  function porCercania(yo) {
    var quedan = paradas.slice(), ruta = [], actual = yo;
    while (quedan.length) {
      var mejor = 0, mejorD = Infinity;
      quedan.forEach(function (p, i) {
        var d = dist(actual, [p.lat, p.lng]);
        if (d < mejorD) { mejorD = d; mejor = i; }
      });
      actual = [quedan[mejor].lat, quedan[mejor].lng];
      ruta.push(quedan.splice(mejor, 1)[0]);
    }
    return ruta;
  }

  pintar();

  var btn = document.getElementById('mapa-cerca');
  var aviso = document.getElementById('mapa-aviso');
  if (btn && navigator.geolocation) {
    btn.addEventListener('click', function () {
      if (btn.dataset.activo === '1') {           // volver al orden de la obra
        orden = paradas.slice();
        btn.dataset.activo = '0';
        btn.textContent = 'Empezar por lo más cercano';
        aviso.textContent = 'Orden de la obra: lo que hay que decidir primero va primero.';
        pintar();
        return;
      }
      btn.disabled = true;
      btn.textContent = 'Buscando tu ubicación…';
      navigator.geolocation.getCurrentPosition(function (pos) {
        var yo = [pos.coords.latitude, pos.coords.longitude];
        orden = porCercania(yo);
        L.marker(yo, { icon: L.divIcon({ className: '', html: '<span class="pin pin--yo">•</span>', iconSize: [22, 22], iconAnchor: [11, 11] }) })
          .bindPopup('Estás acá').addTo(capa);
        btn.disabled = false;
        btn.dataset.activo = '1';
        btn.textContent = 'Volver al orden de la obra';
        aviso.textContent = 'Ordenado desde donde estás. Ojo: se pierde el orden de la obra.';
        pintar();
      }, function () {
        btn.disabled = false;
        btn.textContent = 'Empezar por lo más cercano';
        aviso.textContent = 'No se pudo obtener tu ubicación. Revisá los permisos del navegador.';
      }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
    });
  } else if (btn) {
    btn.hidden = true;
  }
})();
