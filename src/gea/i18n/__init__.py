"""Bilingual UI catalogs for gea (see AGENTS.md — UI multi-idioma).

Usage:
    from gea.i18n import t
    print(t("doctor.title"))

Language resolution order: GEA_LANG env var > ~/gea/config.json["ui_lang"]
> "es" (default/recommended).
"""

from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path

_CATALOG_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGS = ("es", "en")
DEFAULT_LANG = "es"


@cache
def _load_catalog(lang: str) -> dict[str, str]:
    path = _CATALOG_DIR / f"{lang}.json"
    if not path.exists():
        path = _CATALOG_DIR / f"{DEFAULT_LANG}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def current_lang() -> str:
    env_lang = os.environ.get("GEA_LANG")
    if env_lang in SUPPORTED_LANGS:
        return env_lang

    # Import here (not at module load) to avoid a circular import with
    # gea.config, which itself may want to report errors via t().
    from gea import config as gea_config

    configured = gea_config.load_global().get("ui_lang")
    if configured in SUPPORTED_LANGS:
        return configured
    return DEFAULT_LANG


def t(key: str, lang: str | None = None, **variables: object) -> str:
    """Translate `key` for `lang` (or the resolved current language).

    Falls back to the raw key if it's missing from the catalog — never
    raises, so a missing translation degrades gracefully instead of
    crashing the CLI.
    """
    lang = lang or current_lang()
    catalog = _load_catalog(lang)
    template = catalog.get(key, key)
    if variables:
        try:
            return template.format(**variables)
        except (KeyError, IndexError):
            return template
    return template


def catalog_keys(lang: str) -> set[str]:
    return set(_load_catalog(lang).keys())
