# -*- coding: utf-8 -*-
"""Repository helpers for watch persistence."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, select

from src.storage import (
    DatabaseManager,
    WatchReviewResult,
    WatchSignalEvent,
    WatchTarget,
    WatchTargetMember,
    WatchTargetSnapshot,
)

logger = logging.getLogger(__name__)


class WatchRepository:
    """DB access layer for watch targets, candidate events, and reviews."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    # ------------------------------------------------------------------
    # Target CRUD
    # ------------------------------------------------------------------
    def create_target(
        self,
        *,
        target_kind: str,
        target_key: str,
        display_name: str,
        status: str = "active",
        theme_id: Optional[str] = None,
        theme_name: Optional[str] = None,
        source: str = "manual",
        notes: Optional[str] = None,
    ) -> WatchTarget:
        with self.db.get_session() as session:
            row = WatchTarget(
                target_kind=target_kind,
                target_key=target_key,
                display_name=display_name,
                status=status,
                theme_id=theme_id,
                theme_name=theme_name,
                source=source,
                notes=notes,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def get_target(self, target_id: int) -> Optional[WatchTarget]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchTarget).where(WatchTarget.id == target_id).limit(1)
            ).scalar_one_or_none()

    def get_target_by_key(self, target_kind: str, target_key: str) -> Optional[WatchTarget]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchTarget)
                .where(
                    and_(
                        WatchTarget.target_kind == target_kind,
                        WatchTarget.target_key == target_key,
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

    def update_target(self, target_id: int, fields: Dict[str, Any]) -> Optional[WatchTarget]:
        with self.db.get_session() as session:
            row = session.execute(
                select(WatchTarget).where(WatchTarget.id == target_id).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return None

            for key, value in fields.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.now()
            session.commit()
            session.refresh(row)
            return row

    def delete_target(self, target_id: int) -> bool:
        with self.db.get_session() as session:
            row = session.execute(
                select(WatchTarget).where(WatchTarget.id == target_id).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return False

            session.execute(delete(WatchTargetMember).where(WatchTargetMember.target_id == target_id))
            session.execute(delete(WatchSignalEvent).where(WatchSignalEvent.target_id == target_id))
            session.delete(row)
            session.commit()
            return True

    def list_targets(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        target_kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[WatchTarget], int]:
        page = max(1, int(page))
        limit = max(1, int(limit))
        offset = (page - 1) * limit

        with self.db.get_session() as session:
            conditions = []
            if target_kind:
                conditions.append(WatchTarget.target_kind == target_kind)
            if status:
                conditions.append(WatchTarget.status == status)

            where_clause = and_(*conditions) if conditions else True
            total = session.execute(
                select(func.count(WatchTarget.id)).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(WatchTarget)
                .where(where_clause)
                .order_by(desc(WatchTarget.updated_at), desc(WatchTarget.id))
                .offset(offset)
                .limit(limit)
            ).scalars().all()
            return list(rows), int(total)

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------
    def replace_target_members(
        self,
        target_id: int,
        members: Iterable[Dict[str, Any]],
    ) -> List[WatchTargetMember]:
        member_rows: List[WatchTargetMember] = []
        with self.db.get_session() as session:
            session.execute(delete(WatchTargetMember).where(WatchTargetMember.target_id == target_id))
            for item in members:
                if not isinstance(item, dict):
                    continue
                member_code = str(item.get("member_code") or "").strip()
                member_name = str(item.get("member_name") or "").strip()
                member_kind = str(item.get("member_kind") or "stock").strip() or "stock"
                if not member_code or not member_name:
                    continue
                row = WatchTargetMember(
                    target_id=target_id,
                    member_kind=member_kind,
                    member_code=member_code,
                    member_name=member_name,
                    weight=float(item.get("weight", 1.0) or 1.0),
                    source=str(item.get("source") or "catalog").strip() or "catalog",
                )
                session.add(row)
                member_rows.append(row)
            session.commit()
            for row in member_rows:
                session.refresh(row)
            return member_rows

    def list_members(self, target_id: int) -> List[WatchTargetMember]:
        with self.db.get_session() as session:
            rows = session.execute(
                select(WatchTargetMember)
                .where(WatchTargetMember.target_id == target_id)
                .order_by(WatchTargetMember.id.asc())
            ).scalars().all()
            return list(rows)

    # ------------------------------------------------------------------
    # Summary snapshots
    # ------------------------------------------------------------------
    def upsert_target_snapshot(
        self,
        *,
        target_id: int,
        summary_window_days: int,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> WatchTargetSnapshot:
        payload_json = self._dump_payload(payload)

        with self.db.get_session() as session:
            row = session.execute(
                select(WatchTargetSnapshot)
                .where(
                    and_(
                        WatchTargetSnapshot.target_id == target_id,
                        WatchTargetSnapshot.summary_window_days == int(summary_window_days),
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                row = WatchTargetSnapshot(
                    target_id=target_id,
                    summary_window_days=int(summary_window_days),
                    status=status,
                    payload_json=payload_json,
                )
                session.add(row)
            else:
                row.status = status
                row.payload_json = payload_json
                row.updated_at = datetime.now()

            session.commit()
            session.refresh(row)
            return row

    def get_target_snapshot(
        self,
        target_id: int,
        *,
        summary_window_days: int,
    ) -> Optional[WatchTargetSnapshot]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchTargetSnapshot)
                .where(
                    and_(
                        WatchTargetSnapshot.target_id == target_id,
                        WatchTargetSnapshot.summary_window_days == int(summary_window_days),
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

    def list_target_snapshots(
        self,
        target_ids: Iterable[int],
        *,
        summary_window_days: int,
    ) -> Dict[int, WatchTargetSnapshot]:
        ids = [int(target_id) for target_id in target_ids]
        if not ids:
            return {}

        with self.db.get_session() as session:
            rows = session.execute(
                select(WatchTargetSnapshot)
                .where(
                    and_(
                        WatchTargetSnapshot.target_id.in_(ids),
                        WatchTargetSnapshot.summary_window_days == int(summary_window_days),
                    )
                )
            ).scalars().all()
            return {int(row.target_id): row for row in rows}

    # ------------------------------------------------------------------
    # Signal events
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value[:10])
        raise ValueError(f"Invalid date value: {value!r}")

    @staticmethod
    def _dump_payload(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False, default=str)

    def upsert_signal_event(
        self,
        *,
        target_id: int,
        member_code: str,
        signal_date: Any,
        dedupe_key: str,
        signal_type: str,
        signal_score: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
        member_id: Optional[int] = None,
        member_name: Optional[str] = None,
        status: str = "candidate",
    ) -> WatchSignalEvent:
        signal_day = self._coerce_date(signal_date)
        payload_json = self._dump_payload(payload)

        with self.db.get_session() as session:
            row = session.execute(
                select(WatchSignalEvent)
                .where(WatchSignalEvent.dedupe_key == dedupe_key)
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                row = WatchSignalEvent(
                    target_id=target_id,
                    member_id=member_id,
                    member_code=member_code,
                    member_name=member_name,
                    signal_date=signal_day,
                    signal_type=signal_type,
                    signal_score=signal_score,
                    status=status,
                    dedupe_key=dedupe_key,
                    payload_json=payload_json,
                )
                session.add(row)
            else:
                row.target_id = target_id
                row.member_id = member_id
                row.member_code = member_code
                row.member_name = member_name
                row.signal_date = signal_day
                row.signal_type = signal_type
                row.signal_score = signal_score
                row.status = status
                row.payload_json = payload_json
                row.updated_at = datetime.now()

            session.commit()
            session.refresh(row)
            return row

    def get_signal_event(self, event_id: int) -> Optional[WatchSignalEvent]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchSignalEvent).where(WatchSignalEvent.id == event_id).limit(1)
            ).scalar_one_or_none()

    def get_signal_event_by_dedupe_key(self, dedupe_key: str) -> Optional[WatchSignalEvent]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchSignalEvent).where(WatchSignalEvent.dedupe_key == dedupe_key).limit(1)
            ).scalar_one_or_none()

    def list_signal_events(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        target_id: Optional[int] = None,
        status: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> Tuple[List[WatchSignalEvent], int]:
        page = max(1, int(page))
        limit = max(1, int(limit))
        offset = (page - 1) * limit

        with self.db.get_session() as session:
            conditions = []
            if target_id is not None:
                conditions.append(WatchSignalEvent.target_id == target_id)
            if status:
                conditions.append(WatchSignalEvent.status == status)
            if signal_type:
                conditions.append(WatchSignalEvent.signal_type == signal_type)

            where_clause = and_(*conditions) if conditions else True
            total = session.execute(
                select(func.count(WatchSignalEvent.id)).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(WatchSignalEvent)
                .where(where_clause)
                .order_by(desc(WatchSignalEvent.signal_date), desc(WatchSignalEvent.updated_at), desc(WatchSignalEvent.id))
                .offset(offset)
                .limit(limit)
            ).scalars().all()
            return list(rows), int(total)

    def get_latest_signal_event_for_member(
        self,
        *,
        target_id: int,
        member_code: str,
    ) -> Optional[WatchSignalEvent]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchSignalEvent)
                .where(
                    and_(
                        WatchSignalEvent.target_id == target_id,
                        WatchSignalEvent.member_code == member_code,
                    )
                )
                .order_by(
                    desc(WatchSignalEvent.signal_date),
                    desc(WatchSignalEvent.updated_at),
                    desc(WatchSignalEvent.id),
                )
                .limit(1)
            ).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    def save_review_result(
        self,
        *,
        signal_event_id: int,
        review_round: int,
        decision: str,
        confidence: Optional[float] = None,
        summary: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> WatchReviewResult:
        payload_json = self._dump_payload(payload)

        with self.db.get_session() as session:
            row = session.execute(
                select(WatchReviewResult)
                .where(
                    and_(
                        WatchReviewResult.signal_event_id == signal_event_id,
                        WatchReviewResult.review_round == int(review_round),
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                row = WatchReviewResult(
                    signal_event_id=signal_event_id,
                    review_round=int(review_round),
                    decision=decision,
                    confidence=confidence,
                    summary=summary,
                    payload_json=payload_json,
                )
                session.add(row)
            else:
                row.decision = decision
                row.confidence = confidence
                row.summary = summary
                row.payload_json = payload_json
                row.updated_at = datetime.now()

            session.commit()
            session.refresh(row)
            return row

    def get_review_result(self, signal_event_id: int, review_round: int) -> Optional[WatchReviewResult]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchReviewResult)
                .where(
                    and_(
                        WatchReviewResult.signal_event_id == signal_event_id,
                        WatchReviewResult.review_round == int(review_round),
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

    def get_latest_review(self, signal_event_id: int) -> Optional[WatchReviewResult]:
        with self.db.get_session() as session:
            return session.execute(
                select(WatchReviewResult)
                .where(WatchReviewResult.signal_event_id == signal_event_id)
                .order_by(desc(WatchReviewResult.review_round), desc(WatchReviewResult.updated_at), desc(WatchReviewResult.id))
                .limit(1)
            ).scalar_one_or_none()

    def list_review_results(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        signal_event_id: Optional[int] = None,
    ) -> Tuple[List[WatchReviewResult], int]:
        page = max(1, int(page))
        limit = max(1, int(limit))
        offset = (page - 1) * limit

        with self.db.get_session() as session:
            conditions = []
            if signal_event_id is not None:
                conditions.append(WatchReviewResult.signal_event_id == signal_event_id)

            where_clause = and_(*conditions) if conditions else True
            total = session.execute(
                select(func.count(WatchReviewResult.id)).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(WatchReviewResult)
                .where(where_clause)
                .order_by(desc(WatchReviewResult.review_round), desc(WatchReviewResult.updated_at), desc(WatchReviewResult.id))
                .offset(offset)
                .limit(limit)
            ).scalars().all()
            return list(rows), int(total)
