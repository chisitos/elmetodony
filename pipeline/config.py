"""Carga de configuración editorial (config/*.yaml) con overrides por env var."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Config:
    raw: dict[str, Any] = field(default_factory=dict)
    feeds: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Config":
        editorial = _load_yaml("editorial.yaml")
        feeds = _load_yaml("feeds.yaml").get("feeds", [])
        return cls(raw=editorial, feeds=feeds)

    # -- accesos convenientes -------------------------------------------------
    @property
    def publication_name(self) -> str:
        return self.raw.get("publication", {}).get("name", "ALBA")

    @property
    def tagline(self) -> str:
        return self.raw.get("publication", {}).get("tagline", "")

    @property
    def language(self) -> str:
        return self.raw.get("publication", {}).get("language", "es")

    def model(self, role: str) -> str:
        """role in {'research', 'curator', 'editor'} — override con
        ANTHROPIC_MODEL_RESEARCH / ANTHROPIC_MODEL_CURATOR / ANTHROPIC_MODEL_EDITOR."""
        env_key = f"ANTHROPIC_MODEL_{role.upper()}"
        if os.environ.get(env_key):
            return os.environ[env_key]
        return self.raw.get("models", {}).get(role, "claude-sonnet-5")

    @property
    def lookback_days(self) -> int:
        return int(self.raw.get("run", {}).get("lookback_days", 6))

    @property
    def max_rss_per_feed(self) -> int:
        return int(self.raw.get("run", {}).get("max_rss_per_feed", 12))

    @property
    def max_web_queries(self) -> int:
        return int(self.raw.get("run", {}).get("max_web_queries", 4))

    @property
    def max_selected_per_run(self) -> int:
        return int(self.raw.get("run", {}).get("max_selected_per_run", 6))

    @property
    def min_score_to_select(self) -> float:
        return float(self.raw.get("run", {}).get("min_score_to_select", 6.5))

    @property
    def include_keywords(self) -> list[str]:
        return [k.lower() for k in self.raw.get("scope", {}).get("include_keywords", [])]

    @property
    def exclude_keywords(self) -> list[str]:
        return [k.lower() for k in self.raw.get("scope", {}).get("exclude_keywords", [])]

    @property
    def rubric_weights(self) -> dict[str, float]:
        return self.raw.get("rubric", {}).get("weights", {})

    @property
    def voice_principles(self) -> list[str]:
        return self.raw.get("voice", {}).get("principles", [])

    @property
    def forbidden_phrases(self) -> list[str]:
        return self.raw.get("voice", {}).get("forbidden_phrases", [])

    @property
    def target_length_words(self) -> tuple[int, int]:
        lo, hi = self.raw.get("voice", {}).get("target_length_words", [280, 480])
        return int(lo), int(hi)
