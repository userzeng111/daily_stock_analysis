# -*- coding: utf-8 -*-
"""Watch target creation and basket expansion service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from data_provider.base import ETF_PREFIXES, canonical_stock_code, normalize_stock_code

from src.repositories.watch_repo import WatchRepository
from src.services.watch_theme_catalog_service import WatchThemeCatalogService
from src.storage import DatabaseManager, WatchTarget


def _is_etf_code(code: str) -> bool:
    normalized = normalize_stock_code(code)
    return normalized.isdigit() and len(normalized) == 6 and normalized.startswith(ETF_PREFIXES)


class WatchlistService:
    """Create and refresh watch targets for stocks, ETFs, and curated themes."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        theme_catalog: Optional[WatchThemeCatalogService] = None,
        summary_service=None,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.theme_catalog = theme_catalog or WatchThemeCatalogService()
        if summary_service is None:
            from src.services.watch_summary_service import WatchSummaryService

            summary_service = WatchSummaryService(db_manager=self.db, repo=self.repo)
        self.summary_service = summary_service

    def create_target(
        self,
        input_text: str,
        *,
        target_kind: Optional[str] = None,
        display_name: Optional[str] = None,
        source: str = "manual",
        notes: Optional[str] = None,
    ) -> WatchTarget:
        candidate_text = (input_text or "").strip()
        if not candidate_text:
            raise ValueError("input_text is required")

        resolved_kind = self._resolve_target_kind(candidate_text, explicit_kind=target_kind)
        if resolved_kind == "theme":
            return self._create_theme_target(
                candidate_text,
                display_name=display_name,
                source=source,
                notes=notes,
            )
        return self._create_security_target(
            candidate_text,
            target_kind=resolved_kind,
            display_name=display_name,
            source=source,
            notes=notes,
        )

    def _resolve_target_kind(self, input_text: str, explicit_kind: Optional[str]) -> str:
        kind = (explicit_kind or "").strip().lower()
        if kind in {"stock", "etf", "theme"}:
            return kind

        normalized = normalize_stock_code(input_text)
        if normalized.isdigit() and len(normalized) == 6:
            return "etf" if _is_etf_code(normalized) else "stock"

        return "theme"

    def _create_security_target(
        self,
        input_text: str,
        *,
        target_kind: str,
        display_name: Optional[str],
        source: str,
        notes: Optional[str],
    ) -> WatchTarget:
        normalized = canonical_stock_code(normalize_stock_code(input_text))
        existing = self.repo.get_target_by_key(target_kind, normalized)
        resolved_display_name = (display_name or input_text or normalized).strip() or normalized

        if existing is None:
            target = self.repo.create_target(
                target_kind=target_kind,
                target_key=normalized,
                display_name=resolved_display_name,
                status="active",
                source=source,
                notes=notes,
            )
        else:
            target = self.repo.update_target(
                existing.id,
                {
                    "display_name": resolved_display_name,
                    "status": "active",
                    "source": source,
                    "notes": notes,
                },
            ) or existing

        self.repo.replace_target_members(
            target.id,
            [
                {
                    "member_code": normalized,
                    "member_name": resolved_display_name,
                    "member_kind": target_kind,
                    "weight": 1.0,
                    "source": source,
                }
            ],
        )
        self._refresh_summary_snapshot(target.id)
        return target

    def _create_theme_target(
        self,
        input_text: str,
        *,
        display_name: Optional[str],
        source: str,
        notes: Optional[str],
    ) -> WatchTarget:
        resolution = self.theme_catalog.resolve_theme(input_text)
        resolved_display_name = (
            resolution.display_name
            or (display_name or input_text).strip()
            or input_text.strip()
        )
        target_key = resolution.theme_id or input_text.strip()
        existing = self.repo.get_target_by_key("theme", target_key)

        status = "active" if resolution.supported else "unsupported"
        theme_id = resolution.theme_id
        theme_name = resolution.display_name or resolved_display_name

        if existing is None:
            target = self.repo.create_target(
                target_kind="theme",
                target_key=target_key,
                display_name=resolved_display_name,
                status=status,
                theme_id=theme_id,
                theme_name=theme_name,
                source=source,
                notes=notes,
            )
        else:
            target = self.repo.update_target(
                existing.id,
                {
                    "display_name": resolved_display_name,
                    "status": status,
                    "theme_id": theme_id,
                    "theme_name": theme_name,
                    "source": source,
                    "notes": notes,
                },
            ) or existing

        members = []
        if resolution.supported:
            for item in resolution.members:
                members.append(
                    {
                        "member_code": item.code,
                        "member_name": item.name,
                        "member_kind": "stock",
                        "weight": 1.0,
                        "source": "catalog",
                    }
                )
            for item in resolution.etfs:
                members.append(
                    {
                        "member_code": item.code,
                        "member_name": item.name,
                        "member_kind": "etf",
                        "weight": 1.0,
                        "source": "catalog",
                    }
                )
        self.repo.replace_target_members(target.id, members)
        self._refresh_summary_snapshot(target.id)
        return target

    def list_targets(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        target_kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        rows, total = self.repo.list_targets(
            page=page,
            limit=limit,
            target_kind=target_kind,
            status=status,
        )
        snapshots = self.repo.list_target_snapshots(
            [row.id for row in rows],
            summary_window_days=7,
        )
        items: List[Dict[str, Any]] = []
        for row in rows:
            item = row.to_dict()
            item["member_count"] = len(self.repo.list_members(row.id))
            snapshot = snapshots.get(int(row.id))
            item["summary"] = self._build_summary_payload(snapshot.payload if snapshot is not None else None)
            items.append(item)
        return items, total

    @staticmethod
    def _build_summary_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(payload, dict) and payload:
            merged = dict(payload)
            merged.setdefault("status", "ready")
            merged.setdefault("summary_window_days", 7)
            merged.setdefault("brief", "摘要已生成")
            return merged
        return {
            "status": "pending",
            "summary_window_days": 7,
            "signal_score": None,
            "action": None,
            "brief": "摘要生成中",
        }

    def _refresh_summary_snapshot(self, target_id: int) -> None:
        try:
            self.summary_service.refresh_target_snapshot(target_id)
        except Exception as exc:
            self.repo.upsert_target_snapshot(
                target_id=target_id,
                summary_window_days=7,
                status="failed",
                payload={
                    "target_id": target_id,
                    "summary_window_days": 7,
                    "status": "failed",
                    "brief": "摘要生成失败",
                    "error": str(exc),
                },
            )
