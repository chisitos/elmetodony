"""Carga el directorio de tiendas y las rutas de remodelación.

Lee data/tiendas.yaml y config/rutas.yaml y devuelve un objeto ya resuelto:
cada parada de una ruta trae los objetos de tienda completos, no slugs, y
cada tienda sabe en qué rutas aparece.

Sólo depende de PyYAML — igual que el resto de `--site-only`, que corre en
CI sin instalar anthropic/feedparser (ver .github/workflows/deploy-pages.yml).
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import yaml

log = logging.getLogger("remodelar.directorio")

ROOT = Path(__file__).resolve().parent.parent
TIENDAS_PATH = ROOT / "data" / "tiendas.yaml"
RUTAS_PATH = ROOT / "config" / "rutas.yaml"

# Etiqueta visible para cada nivel de precio. El dato crudo ("alto") es para
# filtrar; esto es lo que lee el usuario.
NIVELES = {
    "accesible": {"label": "Precio de obra", "short": "$"},
    "medio": {"label": "Precio medio", "short": "$$"},
    "alto": {"label": "Alta gama", "short": "$$$"},
    "especializado": {"label": "Especializado", "short": "◆"},
}

MAPS_SEARCH = "https://www.google.com/maps/search/?api=1&query="
MAPS_DIR = "https://www.google.com/maps/dir/?api=1"


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes — para que el buscador encuentre 'bano' y
    'iluminacion' igual que 'baño' e 'iluminación'."""
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def maps_url(direccion: str) -> str:
    return MAPS_SEARCH + quote_plus(f"{direccion}, Colombia")


def maps_ruta_url(direcciones: list[str]) -> str:
    """Arma un enlace de Google Maps con todas las paradas en orden, para que
    el usuario abra la ruta completa en el celular y arranque a manejar."""
    puntos = [quote_plus(f"{d}, Colombia") for d in direcciones if d]
    if not puntos:
        return ""
    if len(puntos) == 1:
        return f"{MAPS_DIR}&destination={puntos[0]}"
    url = f"{MAPS_DIR}&origin={puntos[0]}&destination={puntos[-1]}"
    if len(puntos) > 2:
        url += "&waypoints=" + "|".join(puntos[1:-1])
    return url


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        log.warning("No existe %s — se omite", path)
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Directorio:
    sitio: dict[str, Any] = field(default_factory=dict)
    ancla: dict[str, Any] = field(default_factory=dict)
    zonas: list[dict[str, Any]] = field(default_factory=list)
    categorias: list[dict[str, Any]] = field(default_factory=list)
    tiendas: list[dict[str, Any]] = field(default_factory=list)
    rutas: list[dict[str, Any]] = field(default_factory=list)

    # índices
    por_slug: dict[str, dict] = field(default_factory=dict)
    zona_por_slug: dict[str, dict] = field(default_factory=dict)
    cat_por_slug: dict[str, dict] = field(default_factory=dict)

    @property
    def tiendas_ideo(self) -> list[dict]:
        return [t for t in self.tiendas if t.get("en_ideo")]

    def tiendas_de(self, categoria: str) -> list[dict]:
        return [t for t in self.tiendas if categoria in t.get("categorias", [])]


def _tienda_view(raw: dict, zona_por_slug: dict, cat_por_slug: dict) -> dict:
    """Enriquece una tienda cruda del YAML con todo lo que la plantilla
    necesita: nombres legibles, enlace a Maps y texto de búsqueda."""
    t = dict(raw)
    zona = zona_por_slug.get(t.get("zona", ""), {})
    t["zona_nombre"] = zona.get("nombre", t.get("zona", ""))
    t["zona_corta"] = zona.get("corta", t.get("zona", ""))
    t["categorias_nombres"] = [
        cat_por_slug.get(c, {}).get("nombre", c) for c in t.get("categorias", [])
    ]
    nivel = NIVELES.get(t.get("nivel", ""), {})
    t["nivel_label"] = nivel.get("label", "")
    t["nivel_short"] = nivel.get("short", "")
    t["url"] = f"directorio/{t['slug']}.html"
    t["maps_url"] = maps_url(t.get("direccion", ""))
    # Dirección con el local, para mostrar de un tiro en la tarjeta.
    t["direccion_completa"] = (
        f"{t.get('direccion', '')} · {t['local']}" if t.get("local") else t.get("direccion", "")
    )
    # Todo lo buscable en un solo campo — el buscador del navegador compara
    # contra esto, ya normalizado, sin tener que recorrer cada llave.
    t["buscable"] = normalizar(
        " ".join(
            [
                t.get("nombre", ""),
                t.get("aporta", ""),
                t.get("direccion", ""),
                t.get("local", "") or "",
                t["zona_nombre"],
                " ".join(t["categorias_nombres"]),
                " ".join(t.get("categorias", [])),
                "ideo" if t.get("en_ideo") else "",
            ]
        )
    )
    t["rutas"] = []  # se llena al resolver las rutas
    return t


def load() -> Directorio:
    cfg = _load_yaml(RUTAS_PATH)
    tiendas_raw = _load_yaml(TIENDAS_PATH).get("tiendas", [])

    zonas = cfg.get("zonas", [])
    categorias = cfg.get("categorias", [])
    zona_por_slug = {z["slug"]: z for z in zonas}
    cat_por_slug = {c["slug"]: c for c in categorias}

    tiendas = [_tienda_view(t, zona_por_slug, cat_por_slug) for t in tiendas_raw]
    por_slug = {t["slug"]: t for t in tiendas}

    # Aviso temprano: un slug mal escrito en rutas.yaml dejaría una parada
    # vacía sin que se note hasta ver el sitio.
    faltantes: set[str] = set()

    rutas = []
    for indice, raw in enumerate(cfg.get("rutas", [])):
        ruta = dict(raw)
        # Posición en el orden del YAML: numera la ruta y elige su trama, para
        # que cada una se reconozca siempre por el mismo par número/patrón.
        ruta["indice"] = indice
        paradas = []
        for i, p_raw in enumerate(raw.get("paradas", []), start=1):
            p = dict(p_raw)
            slugs = p.get("tiendas", [])
            resueltas = []
            for s in slugs:
                if s in por_slug:
                    resueltas.append(por_slug[s])
                else:
                    faltantes.add(s)
            p["numero"] = i
            p["tiendas"] = resueltas
            p["principal"] = resueltas[0] if resueltas else None
            p["alternativas"] = resueltas[1:]
            p["categoria_nombre"] = cat_por_slug.get(p.get("categoria", ""), {}).get(
                "nombre", p.get("categoria", "")
            )
            p["en_ideo"] = bool(resueltas and resueltas[0].get("en_ideo"))
            paradas.append(p)

        ruta["paradas"] = paradas
        ruta["total_paradas"] = len(paradas)
        ruta["paradas_ideo"] = sum(1 for p in paradas if p["en_ideo"])
        ruta["url"] = f"rutas/{ruta['slug']}.html"
        # El enlace "abrir la ruta completa en Google Maps": las direcciones
        # de la tienda principal de cada parada, en orden.
        ruta["maps_ruta_url"] = maps_ruta_url(
            [p["principal"]["direccion"] for p in paradas if p["principal"]]
        )
        rutas.append(ruta)

        # Backlink: cada tienda sabe en qué rutas sale.
        for p in paradas:
            for t in p["tiendas"]:
                entrada = {"slug": ruta["slug"], "nombre": ruta["nombre"], "parada": p["titulo"]}
                if not any(r["slug"] == ruta["slug"] for r in t["rutas"]):
                    t["rutas"].append(entrada)

    if faltantes:
        log.warning(
            "Slugs en config/rutas.yaml que no existen en data/tiendas.yaml: %s",
            ", ".join(sorted(faltantes)),
        )

    return Directorio(
        sitio=cfg.get("sitio", {}),
        ancla=cfg.get("ancla", {}),
        zonas=zonas,
        categorias=categorias,
        tiendas=tiendas,
        rutas=rutas,
        por_slug=por_slug,
        zona_por_slug=zona_por_slug,
        cat_por_slug=cat_por_slug,
    )
