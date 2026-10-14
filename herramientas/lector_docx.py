# -*- coding: utf-8 -*-
"""Lectura de .docx conservando la estructura.

Un .docx es un zip con XML adentro, así que se lee sin dependencias. Pero
hay que recorrer el cuerpo EN ORDEN y distinguir párrafos de tablas: la
primera versión de este importador borró las etiquetas de un plumazo y
aplanó las tablas a texto suelto.

Eso no sólo se veía mal. En el artículo de jardines, una tabla de especies
por clima quedó como una lista de nombres y equis sin columna, y ahí
«Palma rafis» —que es de clima medio y caliente— pasó a leerse como de
clima frío y medio. Se publicó un dato falso.
"""
from __future__ import annotations

import re
import unicodedata
import zipfile

PARRAFO = re.compile(r"<w:p[ >].*?</w:p>", re.S)
TABLA = re.compile(r"<w:tbl>.*?</w:tbl>", re.S)
FILA = re.compile(r"<w:tr[ >].*?</w:tr>", re.S)
CELDA = re.compile(r"<w:tc[ >].*?</w:tc>", re.S)
BLOQUE = re.compile(r"<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>", re.S)
ETIQUETA = re.compile(r"<[^>]+>")


def nfc(s: str) -> str:
    """macOS guarda los acentos descompuestos; sin esto no coinciden."""
    return unicodedata.normalize("NFC", s)


def _texto(fragmento: str) -> str:
    return nfc(ETIQUETA.sub("", fragmento)).strip()


def _tabla_markdown(xml: str) -> str:
    filas = []
    for f in FILA.findall(xml):
        celdas = [_texto(c) for c in CELDA.findall(f)]
        if any(celdas):
            filas.append(celdas)
    if not filas:
        return ""

    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]

    # Las marcas de presencia («x») se vuelven un símbolo legible; una celda
    # vacía en una tabla de doble entrada significa «no», no «falta el dato».
    def celda(v: str) -> str:
        return "Sí" if v.strip().lower() in ("x", "✓") else (v or "—")

    cabecera = "| " + " | ".join(filas[0]) + " |"
    sep = "| " + " | ".join("---" for _ in filas[0]) + " |"
    cuerpo = "\n".join("| " + " | ".join(celda(c) for c in f) + " |" for f in filas[1:])
    return "\n".join([cabecera, sep, cuerpo])


def bloques(ruta) -> list[str]:
    """Devuelve el documento como bloques de markdown, en orden."""
    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    cuerpo = xml[xml.index("<w:body>"):] if "<w:body>" in xml else xml

    salida: list[str] = []
    for m in BLOQUE.finditer(cuerpo):
        frag = m.group(0)
        if frag.startswith("<w:tbl>"):
            t = _tabla_markdown(frag)
            if t:
                salida.append(t)
        else:
            t = _texto(frag)
            if t:
                salida.append(t)
    return salida
