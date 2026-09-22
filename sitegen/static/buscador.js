/* Buscador del directorio — todo en el navegador, sin servidor.
 *
 * Las filas ya vienen renderizadas en el HTML con data-buscable (texto
 * normalizado, sin tildes), data-cats y data-zona. Filtrar es esconder filas,
 * así que funciona sin conexión y responde al instante: la ruta se hace en la
 * calle, muchas veces con mala señal. */
(function () {
  'use strict';

  var q = document.getElementById('q');
  var qClear = document.getElementById('q-clear');
  var lista = document.getElementById('lista');
  var count = document.getElementById('count');
  var vacio = document.getElementById('vacio');
  if (!q || !lista) return;

  var filas = Array.prototype.slice.call(lista.querySelectorAll('.tienda-row'));
  var total = filas.length;
  var estado = { texto: '', cat: '', zona: '' };

  function normalizar(s) {
    return (s || '')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .trim();
  }

  function plural(n) {
    return n === 1 ? '1 tienda' : n + ' tiendas';
  }

  function aplicar() {
    // Varias palabras = todas tienen que aparecer ("piso ideo", "bano centro").
    var terminos = estado.texto ? estado.texto.split(/\s+/) : [];
    var visibles = 0;

    filas.forEach(function (fila) {
      var ok = true;

      if (estado.cat && fila.dataset.cats.split(' ').indexOf(estado.cat) === -1) ok = false;
      if (ok && estado.zona && fila.dataset.zona !== estado.zona) ok = false;

      if (ok && terminos.length) {
        var texto = fila.dataset.buscable;
        for (var i = 0; i < terminos.length; i++) {
          if (texto.indexOf(terminos[i]) === -1) { ok = false; break; }
        }
      }

      fila.hidden = !ok;
      if (ok) visibles++;
    });

    count.textContent = plural(visibles);
    if (vacio) vacio.hidden = visibles !== 0;
    if (qClear) qClear.hidden = !estado.texto;
  }

  q.addEventListener('input', function () {
    estado.texto = normalizar(q.value);
    aplicar();
  });

  if (qClear) {
    qClear.addEventListener('click', function () {
      q.value = '';
      estado.texto = '';
      aplicar();
      q.focus();
    });
  }

  // Los chips de categoría y de zona son dos grupos independientes: se puede
  // pedir "Baños" y "Solo IDEO" a la vez.
  function grupo(selector, llave) {
    var botones = Array.prototype.slice.call(document.querySelectorAll(selector));
    botones.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var valor = btn.dataset[llave];
        var yaEstaba = estado[llave] === valor && valor !== '';

        estado[llave] = yaEstaba ? '' : valor;

        botones.forEach(function (b) {
          var activo = !yaEstaba && b === btn;
          // El chip "Todas" (valor vacío) se prende cuando no hay filtro.
          if (b.dataset[llave] === '') activo = estado[llave] === '';
          b.classList.toggle('is-on', activo);
        });

        aplicar();
        document.getElementById('buscador').scrollIntoView({ block: 'start', behavior: 'smooth' });
      });
    });
  }

  grupo('[data-cat]', 'cat');
  grupo('[data-zona]', 'zona');

  document.querySelectorAll('[data-reset]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      estado = { texto: '', cat: '', zona: '' };
      q.value = '';
      document.querySelectorAll('.chip-btn').forEach(function (b) {
        b.classList.toggle('is-on', b.dataset.cat === '');
      });
      aplicar();
    });
  });

  // Entrar con #banos desde la portada o el pie deja el filtro puesto.
  function desdeHash() {
    var slug = (location.hash || '').replace('#', '');
    if (!slug) return;
    var btn = document.querySelector('[data-cat="' + slug + '"]');
    if (btn) btn.click();
  }

  window.addEventListener('hashchange', desdeHash);
  desdeHash();
  aplicar();
})();
