# -*- coding: utf-8 -*-
"""Markdown mínimo para el cuerpo de una nota.

Deliberadamente corto: encabezados, negrita, cursiva, enlaces, listas,
tablas y recuadros. Es lo que necesita una nota bien escrita y nada más,
para no arrastrar una dependencia entera por seis marcas.

Todo se escapa ANTES de aplicar formato. El texto viene de agentes y de
archivos de Word: ninguno de los dos debería poder inyectar HTML.
"""
from __future__ import annotations

import html
import re

NEGRITA = re.compile(r"\*\*(.+?)\*\*")
CURSIVA = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
ENLACE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
VINETA = re.compile(r"^\s*[-*]\s+")
NUMERO = re.compile(r"^\s*(\d+)[.)]\s+")
SEPARADOR = re.compile(r"^[\s:|-]+$")


def en_linea(texto: str) -> str:
    s = html.escape(texto)
    s = NEGRITA.sub(r"<strong>\1</strong>", s)
    s = CURSIVA.sub(r"<em>\1</em>", s)
    s = ENLACE.sub(r'<a href="\2">\1</a>', s)
    return s


def _tabla(lineas: list[str]) -> str:
    filas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lineas]
    # La segunda fila de una tabla markdown es el separador ---|---
    cuerpo = [f for f in filas[1:] if not all(SEPARADOR.match(c or "-") for c in f)]
    th = "".join("<th>%s</th>" % en_linea(c) for c in filas[0])
    tr = "".join(
        "<tr>%s</tr>" % "".join("<td>%s</td>" % en_linea(c) for c in f) for f in cuerpo
    )
    # El envoltorio permite desplazar la tabla en pantallas angostas en vez
    # de desbordar la página.
    return (
        '<div class="tabla-env"><table>'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (th, tr)
    )


def _lista(lineas: list[str], numerada: bool) -> str:
    items = []
    for l in lineas:
        texto = NUMERO.sub("", l) if numerada else VINETA.sub("", l)
        items.append("<li>%s</li>" % en_linea(texto.strip()))
    etiqueta = "ol" if numerada else "ul"
    return "<%s>%s</%s>" % (etiqueta, "".join(items), etiqueta)


def _recuadro(lineas: list[str]) -> str:
    """Bloque destacado: `> Título` y debajo su contenido.

    Sirve para los apartes que en la revista impresa iban en recuadro, y
    que sin formato quedaban como un párrafo suelto que no se entendía.
    """
    limpias = [re.sub(r"^>\s?", "", l) for l in lineas]
    titulo, resto = limpias[0], [l for l in limpias[1:] if l.strip()]
    cuerpo = ""
    if resto and all(VINETA.match(l) for l in resto):
        cuerpo = _lista(resto, False)
    elif resto:
        cuerpo = "<p>%s</p>" % en_linea(" ".join(resto))
    return '<aside class="recuadro"><h3>%s</h3>%s</aside>' % (en_linea(titulo), cuerpo)


def a_html(cuerpo_md: str, cita: str = "") -> str:
    partes: list[str] = []

    for bloque in [b.strip() for b in cuerpo_md.split("\n\n") if b.strip()]:
        lineas = bloque.split("\n")
        primera = lineas[0]

        if primera.startswith("### "):
            partes.append("<h3>%s</h3>" % en_linea(primera[4:].strip()))
            resto = "\n".join(lineas[1:]).strip()
            if resto:
                partes.append("<p>%s</p>" % en_linea(" ".join(resto.split("\n"))))

        elif primera.startswith("## "):
            partes.append("<h2>%s</h2>" % en_linea(primera[3:].strip()))
            resto = "\n".join(lineas[1:]).strip()
            if resto:
                partes.append("<p>%s</p>" % en_linea(" ".join(resto.split("\n"))))

        elif primera.startswith(">"):
            partes.append(_recuadro(lineas))

        elif primera.startswith("|") and len(lineas) > 1:
            partes.append(_tabla(lineas))

        elif all(NUMERO.match(l) for l in lineas):
            partes.append(_lista(lineas, True))

        elif all(VINETA.match(l) for l in lineas):
            partes.append(_lista(lineas, False))

        else:
            partes.append("<p>%s</p>" % en_linea(" ".join(lineas)))

    # La cita destacada va a media nota, siempre entre dos párrafos.
    if cita:
        indices = [i for i, x in enumerate(partes) if x.startswith("<p>")]
        if len(indices) >= 2:
            partes.insert(indices[len(indices) // 2],
                          "<blockquote>%s</blockquote>" % html.escape(cita))
    return "\n".join(partes)
