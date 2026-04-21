# -*- coding: utf-8 -*-
"""Structured review persistence for watch candidate events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from sqlalchemy import select

from src.repositories.watch_repo import WatchRepository
from src.storage import DatabaseManager, WatchSignalEvent


class WatchReviewService:
    """Review watch signal events and persist the latest structured outcome."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        reviewer: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.reviewer = reviewer or self._default_reviewer

    def review_event(self, event_id: int, review_round: int = 1):
        event = self.repo.get_signal_event(event_id)
        if event is None:
            raise ValueError(f"watch signal event not found: {event_id}")

        self._set_event_status(event_id, "reviewing")
        try:
            result = self.reviewer(event.to_dict())
            decision = str(result.get("decision") or "watch_more").strip() or "watch_more"
            review = self.repo.save_review_result(
                signal_event_id=event_id,
                review_round=int(review_round),
                decision=decision,
                confidence=result.get("confidence"),
                summary=result.get("summary"),
                payload=result.get("payload"),
            )
            self._set_event_status(event_id, self._map_decision_to_status(decision))
            return review
        except Exception as exc:
            self._set_event_status(event_id, "review_failed")
            self.repo.save_review_result(
                signal_event_id=event_id,
                review_round=int(review_round),
                decision="watch_more",
                confidence=0.0,
                summary=f"review_failed: {exc}",
                payload={"error": str(exc)},
            )
            return None

    @staticmethod
    def _default_reviewer(event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "decision": "watch_more",
            "confidence": 0.5,
            "summary": "baseline review pending richer LLM integration",
            "payload": {"source": "baseline_stub", "event_id": event_payload.get("id")},
        }

    @staticmethod
    def _map_decision_to_status(decision: str) -> str:
        normalized = (decision or "").strip().lower()
        if normalized == "buyable":
            return "accepted"
        if normalized == "reject":
            return "rejected"
        return "reviewed"

    def _set_event_status(self, event_id: int, status: str) -> None:
        with self.db.get_session() as session:
            row = session.execute(
                select(WatchSignalEvent).where(WatchSignalEvent.id == event_id).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return
            row.status = status
            row.updated_at = datetime.now()
            session.commit()
