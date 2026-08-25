#!/usr/bin/env python3
"""CLI de Remodelar: corre el pipeline editorial y/o regenera el sitio estático.

Uso:
  python run.py              # pipeline completo (agentes) + sitio
  python run.py --site-only  # sólo regenerar public/ desde data/articles/
  python run.py --pipeline-only  # sólo correr los agentes, sin tocar el sitio
"""
from __future__ import annotations

import argparse
import logging
import sys

from pipeline.config import Config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-only", action="store_true", help="Sólo regenerar el sitio")
    parser.add_argument("--pipeline-only", action="store_true", help="Sólo correr los agentes")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    cfg = Config.load()

    if not args.site_only:
        # Import diferido: esto arrastra anthropic/feedparser/requests, que
        # --site-only no necesita para nada (ver .github/workflows/deploy-pages.yml,
        # que sólo instala lo que usa el generador de sitio).
        from pipeline.orchestrator import run as run_pipeline

        written = run_pipeline(cfg)
        print(f"Artículos nuevos: {len(written)}")
        for p in written:
            print(f"  - {p}")

    if not args.pipeline_only:
        from sitegen.generate import build_site

        out = build_site()
        print(f"Sitio regenerado en: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
