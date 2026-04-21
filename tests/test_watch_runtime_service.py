# -*- coding: utf-8 -*-
"""Tests for watch runtime lifecycle, event bus, and review failure handling."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import date

from src.config import Config
from src.storage import DatabaseManager


class _FakeScheduler:
    def __init__(self) -> None:
        self.registrations: list[dict] = []

    def add_background_task(self, **kwargs) -> None:
        self.registrations.append(kwargs)


class _RecordingSignalService:
    def __init__(self, repo) -> None:
        self.repo = repo
        self.calls: list[int] = []

    def scan_target(self, target_id: int):
        self.calls.append(target_id)
        target = self.repo.get_target(target_id)
        members = self.repo.list_members(target_id)
        if target is None or not members:
            return []
        member = members[0]
        event = self.repo.upsert_signal_event(
            target_id=target.id,
            member_id=member.id,
            member_code=member.member_code,
            member_name=member.member_name,
            signal_date=date(2026, 4, 21),
            dedupe_key=f"{target.id}:{member.member_code}:2026-04-21:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=66,
            status="candidate",
            payload={"source": "runtime-test"},
        )
        return [event]


class _RecordingSummaryService:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def refresh_target_snapshot(self, target_id: int, summary_window_days: int = 7):
        self.calls.append(target_id)
        return {"target_id": target_id, "summary_window_days": summary_window_days, "status": "ready"}


class _ExplodingSummaryService(_RecordingSummaryService):
    def refresh_target_snapshot(self, target_id: int, summary_window_days: int = 7):
        super().refresh_target_snapshot(target_id, summary_window_days)
        raise RuntimeError("summary refresh failed")


class WatchRuntimeServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_watch_runtime.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_start_registers_background_task_only_once(self) -> None:
        from src.services.watch_event_bus import WatchEventBus
        from src.services.watch_review_service import WatchReviewService
        from src.services.watch_runtime_service import WatchRuntimeService

        scheduler = _FakeScheduler()
        bus = WatchEventBus()
        runtime = WatchRuntimeService(
            db_manager=self.db,
            scheduler=scheduler,
            event_bus=bus,
            review_service=WatchReviewService(db_manager=self.db),
        )

        queue: asyncio.Queue = asyncio.Queue()
        bus.subscribe(queue)

        runtime.start()
        runtime.start()

        self.assertEqual(len(scheduler.registrations), 1)
        self.assertTrue(runtime.status()["enabled"])

        started = queue.get_nowait()
        self.assertEqual(started["event_type"], "watch.runtime.started")

        runtime.stop()
        stopped = queue.get_nowait()
        self.assertEqual(stopped["event_type"], "watch.runtime.stopped")
        self.assertFalse(runtime.status()["enabled"])

    def test_run_cycle_skips_when_disabled(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_event_bus import WatchEventBus
        from src.services.watch_review_service import WatchReviewService
        from src.services.watch_runtime_service import WatchRuntimeService

        repo = WatchRepository(self.db)
        signal_service = _RecordingSignalService(repo)
        runtime = WatchRuntimeService(
            db_manager=self.db,
            scheduler=_FakeScheduler(),
            signal_service=signal_service,
            review_service=WatchReviewService(db_manager=self.db),
            event_bus=WatchEventBus(),
        )

        result = runtime.run_cycle()

        self.assertEqual(result["processed_targets"], 0)
        self.assertEqual(result["emitted_events"], 0)
        self.assertEqual(signal_service.calls, [])

    def test_run_cycle_scans_only_active_targets(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_event_bus import WatchEventBus
        from src.services.watch_review_service import WatchReviewService
        from src.services.watch_runtime_service import WatchRuntimeService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo)
        active_target = watchlist_service.create_target("600519", display_name="贵州茅台")
        paused_target = watchlist_service.create_target("000001", display_name="平安银行")
        repo.update_target(paused_target.id, {"status": "paused"})

        signal_service = _RecordingSignalService(repo)
        summary_service = _RecordingSummaryService()
        runtime = WatchRuntimeService(
            db_manager=self.db,
            scheduler=_FakeScheduler(),
            signal_service=signal_service,
            review_service=WatchReviewService(db_manager=self.db),
            event_bus=WatchEventBus(),
            summary_service=summary_service,
        )

        runtime.start()
        result = runtime.run_cycle()

        self.assertEqual(signal_service.calls, [active_target.id])
        self.assertEqual(summary_service.calls, [active_target.id])
        self.assertEqual(result["processed_targets"], 1)
        self.assertEqual(result["emitted_events"], 1)

    def test_review_failure_marks_event_and_cycle_continues(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_event_bus import WatchEventBus
        from src.services.watch_review_service import WatchReviewService
        from src.services.watch_runtime_service import WatchRuntimeService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        signal_service = _RecordingSignalService(repo)
        summary_service = _ExplodingSummaryService()
        review_service = WatchReviewService(
            db_manager=self.db,
            reviewer=lambda event: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        bus = WatchEventBus()
        queue: asyncio.Queue = asyncio.Queue()
        bus.subscribe(queue)

        runtime = WatchRuntimeService(
            db_manager=self.db,
            scheduler=_FakeScheduler(),
            signal_service=signal_service,
            review_service=review_service,
            event_bus=bus,
            summary_service=summary_service,
        )

        runtime.start()
        result = runtime.run_cycle()

        self.assertEqual(result["processed_targets"], 1)
        self.assertEqual(result["emitted_events"], 1)
        self.assertEqual(summary_service.calls, [target.id])
        self.assertIn("summary refresh failed", runtime.status()["last_error"] or "")

        events, total = repo.list_signal_events(target_id=target.id)
        self.assertEqual(total, 1)
        self.assertEqual(events[0].status, "review_failed")

        event_types = []
        while not queue.empty():
            event_types.append(queue.get_nowait()["event_type"])
        self.assertIn("watch.signal.created", event_types)
        self.assertIn("watch.review.updated", event_types)
        self.assertIn("watch.scan.completed", event_types)


if __name__ == "__main__":
    unittest.main()
