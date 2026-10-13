/* Botones de compartir de una nota.
 *
 * En celular usa la hoja nativa del sistema, que es la única vía para que
 * aparezca Instagram; en escritorio ofrece los enlaces directos. */
(function () {
  'use strict';
  var caja = document.querySelector('.compartir');
  if (!caja) return;

  var titulo = caja.dataset.titulo, url = caja.dataset.url, bajada = caja.dataset.bajada;
  var pin = caja.dataset.pin;

  var wa = caja.querySelector('[data-accion="wa"]');
  if (wa) wa.href = 'https://wa.me/?text=' + encodeURIComponent(titulo + ' — ' + url);

  var pi = caja.querySelector('[data-accion="pinterest"]');
  if (pi && pin) {
    // Pinterest conserva el enlace: cada pin devuelve tráfico durante meses,
    // a diferencia de una publicación de Instagram.
    pi.href = 'https://pinterest.com/pin/create/button/?url=' + encodeURIComponent(url) +
              '&media=' + encodeURIComponent(pin) +
              '&description=' + encodeURIComponent(titulo + ' · ' + bajada);
  }

  var nativo = caja.querySelector('[data-accion="nativo"]');
  if (nativo && navigator.share) {
    nativo.hidden = false;
    nativo.addEventListener('click', function () {
      navigator.share({ title: titulo, text: bajada, url: url }).catch(function () {});
    });
  }

  var copiar = caja.querySelector('[data-accion="copiar"]');
  if (copiar) {
    copiar.addEventListener('click', function () {
      var listo = function () {
        var antes = copiar.textContent;
        copiar.textContent = 'Copiado';
        setTimeout(function () { copiar.textContent = antes; }, 1800);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(listo, listo);
      } else {
        var t = document.createElement('textarea');
        t.value = url; document.body.appendChild(t); t.select();
        try { document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(t); listo();
      }
    });
  }
})();
