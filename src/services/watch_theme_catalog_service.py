# -*- coding: utf-8 -*-
"""Curated watch theme catalog loader and resolver."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "watch_theme_catalog.json"


@dataclass(frozen=True)
class WatchThemeMember:
    code: str
    name: str
    kind: str = "stock"


@dataclass(frozen=True)
class WatchThemeCatalogEntry:
    theme_id: str
    display_name: str
    description: str
    aliases: List[str] = field(default_factory=list)
    members: List[WatchThemeMember] = field(default_factory=list)
    etfs: List[WatchThemeMember] = field(default_factory=list)

    def matches(self, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return False
        haystacks = [self.theme_id, self.display_name, self.description, *self.aliases]
        return any(q in str(item).strip().lower() for item in haystacks if item)


@dataclass(frozen=True)
class WatchThemeResolution:
    status: str
    supported: bool
    theme_id: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    members: List[WatchThemeMember] = field(default_factory=list)
    etfs: List[WatchThemeMember] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load_raw_catalog() -> List[Dict[str, Any]]:
    if not _CATALOG_PATH.exists():
        raise FileNotFoundError(f"watch theme catalog not found: {_CATALOG_PATH}")

    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("watch theme catalog must be a JSON array")
    return data


class WatchThemeCatalogService:
    """Load and resolve curated watch themes from local JSON catalog."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = Path(catalog_path) if catalog_path else _CATALOG_PATH
        self._catalog = self._load_catalog()

    def _load_catalog(self) -> List[WatchThemeCatalogEntry]:
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"watch theme catalog not found: {self.catalog_path}")

        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("watch theme catalog must be a JSON array")

        entries: List[WatchThemeCatalogEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            theme_id = str(item.get("theme_id") or "").strip()
            display_name = str(item.get("display_name") or "").strip()
            description = str(item.get("description") or "").strip()
            if not theme_id or not display_name or not description:
                continue
            aliases = [str(v).strip() for v in item.get("aliases", []) if str(v).strip()]
            members = [
                WatchThemeMember(
                    code=str(member.get("code") or "").strip(),
                    name=str(member.get("name") or "").strip(),
                    kind=str(member.get("kind") or "stock").strip() or "stock",
                )
                for member in item.get("members", [])
                if isinstance(member, dict) and str(member.get("code") or "").strip() and str(member.get("name") or "").strip()
            ]
            etfs = [
                WatchThemeMember(
                    code=str(member.get("code") or "").strip(),
                    name=str(member.get("name") or "").strip(),
                    kind=str(member.get("kind") or "etf").strip() or "etf",
                )
                for member in item.get("etfs", [])
                if isinstance(member, dict) and str(member.get("code") or "").strip() and str(member.get("name") or "").strip()
            ]
            entries.append(
                WatchThemeCatalogEntry(
                    theme_id=theme_id,
                    display_name=display_name,
                    description=description,
                    aliases=aliases,
                    members=members,
                    etfs=etfs,
                )
            )

        logger.info("Loaded %d watch themes from %s", len(entries), self.catalog_path)
        return entries

    def list_themes(self) -> List[WatchThemeCatalogEntry]:
        return list(self._catalog)

    def get_theme(self, theme_key: str) -> Optional[WatchThemeCatalogEntry]:
        key = (theme_key or "").strip().lower()
        if not key:
            return None

        for theme in self._catalog:
            if key in {theme.theme_id.lower(), theme.display_name.lower(), *(alias.lower() for alias in theme.aliases)}:
                return theme
        return None

    def search_themes(self, query: str) -> List[WatchThemeCatalogEntry]:
        q = (query or "").strip().lower()
        if not q:
            return []
        return [theme for theme in self._catalog if theme.matches(q)]

    def resolve_theme(self, theme_key: str) -> WatchThemeResolution:
        theme = self.get_theme(theme_key)
        if theme is None:
            return WatchThemeResolution(
                status="unsupported",
                supported=False,
            )

        return WatchThemeResolution(
            status="ok",
            supported=True,
            theme_id=theme.theme_id,
            display_name=theme.display_name,
            description=theme.description,
            aliases=list(theme.aliases),
            members=list(theme.members),
            etfs=list(theme.etfs),
        )
