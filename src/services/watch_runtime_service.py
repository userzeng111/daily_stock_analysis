# -*- coding: utf-8 -*-
"""Runtime lifecycle and scan orchestration for watch monitoring."""

from __future__ import annotations

from datetime import datetime
import threading
from typing import Dict, Iterable, Optional

from src.config import get_config
from src.repositories.watch_repo import WatchRepository
from src.services.watch_event_bus import WatchEventBus
from src.services.watch_review_service import WatchReviewService
from src.services.watch_signal_service import WatchSignalService
from src.services.watch_summary_service import WatchSummaryService
from src.storage import DatabaseManager


class WatchRuntimeService:
    """Manage the single-process watch runtime lifecycle."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        signal_service: Optional[WatchSignalService] = None,
        review_service: Optional[WatchReviewService] = None,
        summary_service: Optional[WatchSummaryService] = None,
        event_bus: Optional[WatchEventBus] = None,
        scheduler=None,
        scan_interval_minutes: int = 45,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.signal_service = signal_service or WatchSignalService(self.db, repo=self.repo)
        self.review_service = review_service or WatchReviewService(self.db, repo=self.repo)
        self.summary_service = summary_service or WatchSummaryService(self.db, repo=self.repo)
        self.event_bus = event_bus or WatchEventBus()
        self.scheduler = scheduler
        configured_interval = int(getattr(get_config(), "watchlist_scan_interval_minutes", 45))
        resolved_interval = scan_interval_minutes if scan_interval_minutes != 45 else configured_interval
        self.scan_interval_minutes = max(1, int(resolved_interval))

        self._enabled = False
        self._registered = False
        self._last_scan_at: Optional[str] = None
        self._last_error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

    def ensure_background_registered(self) -> None:
        if self._registered:
            return
        if self.scheduler is not None:
            self.scheduler.add_background_task(
                task=self.run_cycle,
                interval_seconds=self.scan_interval_minutes * 60,
                run_immediately=False,
                name="watch_runtime",
            )
        else:
            self._thread = threading.Thread(
                target=self._background_loop,
                name="watch_runtime_loop",
                daemon=True,
            )
            self._thread.start()
        self._registered = True

    def start(self) -> Dict[str, object]:
        self.ensure_background_registered()
        if self._enabled:
            return self.status()
        self._enabled = True
        self.event_bus.publish("watch.runtime.started", {"enabled": True})
        return self.status()

    def stop(self) -> Dict[str, object]:
        if not self._enabled:
            return self.status()
        self._enabled = False
        self.event_bus.publish("watch.runtime.stopped", {"enabled": False})
        return self.status()

    def status(self) -> Dict[str, object]:
        return {
            "enabled": self._enabled,
            "registered": self._registered,
            "last_scan_at": self._last_scan_at,
            "last_error": self._last_error,
            "scan_interval_minutes": self.scan_interval_minutes,
        }

    def run_cycle(self, *, force: bool = False) -> Dict[str, object]:
        if not self._enabled and not force:
            return {"processed_targets": 0, "emitted_events": 0}

        targets, _ = self.repo.list_targets(page=1, limit=1000, status="active")
        return self._scan_targets(targets)

    def scan_all_targets(self) -> Dict[str, object]:
        targets, _ = self.repo.list_targets(page=1, limit=1000, status="active")
        return self._scan_targets(targets)

    def scan_target(self, target_id: int) -> Dict[str, object]:
        target = self.repo.get_target(int(target_id))
        if target is None:
            raise ValueError(f"watch target not found: {target_id}")
        return self._scan_targets([target], requested_target_id=int(target_id), force_members=True)

    def run_target_cycle(self, target_id: int) -> Dict[str, object]:
        return self.scan_target(target_id)

    def _scan_targets(
        self,
        targets: Iterable,
        *,
        requested_target_id: Optional[int] = None,
        force_members: bool = False,
    ) -> Dict[str, object]:
        processed_targets = 0
        emitted_events = 0
        self._last_error = None

        for target in targets:
            processed_targets += 1
            events = self._scan_one_target(target, force_members=force_members)
            for event in events:
                emitted_events += 1
                self.event_bus.publish(
                    "watch.signal.created",
                    {
                        "target_id": target.id,
                        "event_id": event.id,
                        "member_code": event.member_code,
                        "status": event.status,
                    },
                )
                review = self.review_service.review_event(event.id)
                latest_event = self.repo.get_signal_event(event.id)
                self.event_bus.publish(
                    "watch.review.updated",
                    {
                        "target_id": target.id,
                        "event_id": event.id,
                        "review_id": getattr(review, "id", None),
                        "status": latest_event.status if latest_event is not None else "unknown",
                    },
                )
            try:
                self.summary_service.refresh_target_snapshot(target.id, summary_window_days=7)
            except Exception as exc:
                self._last_error = str(exc)

        self._last_scan_at = datetime.now().isoformat()
        payload = {
            "processed_targets": processed_targets,
            "emitted_events": emitted_events,
            "last_scan_at": self._last_scan_at,
        }
        if requested_target_id is not None:
            payload["target_id"] = requested_target_id
        self.event_bus.publish("watch.scan.completed", payload)
        if self._last_error is not None:
            payload["last_error"] = self._last_error
        return payload

    def _scan_one_target(self, target, *, force_members: bool = False):
        if not force_members:
            return self.signal_service.scan_target(target.id)

        if not hasattr(self.signal_service, "scan_member"):
            original_status = getattr(target, "status", None)
            if original_status != "active":
                self.repo.update_target(target.id, {"status": "active"})
            try:
                return self.signal_service.scan_target(target.id)
            finally:
                if original_status is not None and original_status != "active":
                    self.repo.update_target(target.id, {"status": original_status})

        events = []
        for member in self.repo.list_members(target.id):
            event = self.signal_service.scan_member(target, member)
            if event is not None:
                events.append(event)
        return events

    def shutdown(self) -> None:
        self._shutdown_event.set()

    def _background_loop(self) -> None:
        while not self._shutdown_event.is_set():
            if self._enabled:
                try:
                    self.run_cycle()
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    self._last_error = str(exc)
                wait_seconds = self.scan_interval_minutes * 60
            else:
                wait_seconds = 5
            self._shutdown_event.wait(wait_seconds)
