# -*- coding: utf-8 -*-
"""Tests for watch persistence foundation."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime

from src.config import Config
from src.storage import DatabaseManager


class WatchRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_watch.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_target_member_event_and_review_crud(self) -> None:
        from src.repositories.watch_repo import WatchRepository

        repo = WatchRepository(self.db)

        target = repo.create_target(
            target_kind="theme",
            target_key="compute_power",
            display_name="算力",
            status="active",
            theme_id="compute_power",
            source="catalog",
        )
        self.assertIsNotNone(target.id)
        self.assertEqual(target.target_key, "compute_power")

        fetched = repo.get_target(target.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.display_name, "算力")

        repo.replace_target_members(
            target.id,
            [
                {"member_code": "603019", "member_name": "中科曙光", "member_kind": "stock", "weight": 1.0},
                {"member_code": "512720", "member_name": "计算机ETF", "member_kind": "etf", "weight": 1.0},
            ],
        )

        members = repo.list_members(target_id=target.id)
        self.assertEqual([m.member_code for m in members], ["603019", "512720"])

        rows, total = repo.list_targets(limit=20, page=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(total, 1)

        updated = repo.update_target(target.id, {"status": "paused"})
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "paused")

        deleted = repo.delete_target(target.id)
        self.assertTrue(deleted)
        self.assertIsNone(repo.get_target(target.id))

    def test_signal_event_dedupe_key_is_upserted(self) -> None:
        from src.repositories.watch_repo import WatchRepository

        repo = WatchRepository(self.db)
        target = repo.create_target(
            target_kind="stock",
            target_key="600519",
            display_name="贵州茅台",
            status="active",
            source="manual",
        )

        first = repo.upsert_signal_event(
            target_id=target.id,
            member_code="600519",
            signal_date="2026-04-21",
            dedupe_key="600519:2026-04-21:buy_point",
            signal_type="candidate",
            signal_score=68,
            payload={"note": "first"},
        )
        self.assertIsNotNone(first.id)

        second = repo.upsert_signal_event(
            target_id=target.id,
            member_code="600519",
            signal_date="2026-04-21",
            dedupe_key="600519:2026-04-21:buy_point",
            signal_type="candidate",
            signal_score=73,
            payload={"note": "updated"},
        )
        self.assertEqual(second.id, first.id)
        self.assertEqual(second.signal_score, 73)

        events, total = repo.list_signal_events(target_id=target.id)
        self.assertEqual(total, 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload_json, '{"note": "updated"}')

    def test_review_result_is_unique_per_event_round(self) -> None:
        from src.repositories.watch_repo import WatchRepository

        repo = WatchRepository(self.db)
        target = repo.create_target(
            target_kind="stock",
            target_key="000001",
            display_name="平安银行",
            status="active",
            source="manual",
        )
        event = repo.upsert_signal_event(
            target_id=target.id,
            member_code="000001",
            signal_date="2026-04-21",
            dedupe_key="000001:2026-04-21:watch",
            signal_type="candidate",
            signal_score=55,
            payload={"stage": 1},
        )

        review_1 = repo.save_review_result(
            signal_event_id=event.id,
            review_round=1,
            decision="watch_more",
            confidence=0.62,
            summary="first pass",
            payload={"reason": "needs confirmation"},
        )
        self.assertIsNotNone(review_1.id)

        review_2 = repo.save_review_result(
            signal_event_id=event.id,
            review_round=1,
            decision="buyable",
            confidence=0.88,
            summary="updated pass",
            payload={"reason": "confirmed"},
        )
        self.assertEqual(review_2.id, review_1.id)
        self.assertEqual(review_2.decision, "buyable")

        latest = repo.get_latest_review(signal_event_id=event.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.review_round, 1)
        self.assertEqual(latest.decision, "buyable")

        rows, total = repo.list_review_results(signal_event_id=event.id)
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)

    def test_target_snapshot_is_upserted_by_target_and_window(self) -> None:
        from src.repositories.watch_repo import WatchRepository

        repo = WatchRepository(self.db)
        target = repo.create_target(
            target_kind="stock",
            target_key="600519",
            display_name="贵州茅台",
            status="active",
            source="manual",
        )

        pending = repo.upsert_target_snapshot(
            target_id=target.id,
            summary_window_days=7,
            status="pending",
            payload={"brief": "refreshing"},
        )
        self.assertIsNotNone(pending.id)
        self.assertEqual(pending.status, "pending")

        ready = repo.upsert_target_snapshot(
            target_id=target.id,
            summary_window_days=7,
            status="ready",
            payload={"brief": "7日内震荡走强", "return_pct": 3.2},
        )
        self.assertEqual(ready.id, pending.id)
        self.assertEqual(ready.status, "ready")

        failed = repo.upsert_target_snapshot(
            target_id=target.id,
            summary_window_days=30,
            status="failed",
            payload={"brief": "summary_failed", "error": "boom"},
        )
        self.assertIsNotNone(failed.id)
        self.assertNotEqual(failed.id, ready.id)

        summary = repo.get_target_snapshot(target.id, summary_window_days=7)
        self.assertIsNotNone(summary)
        self.assertEqual(summary.status, "ready")
        self.assertEqual(summary.payload["brief"], "7日内震荡走强")

        failed_summary = repo.get_target_snapshot(target.id, summary_window_days=30)
        self.assertIsNotNone(failed_summary)
        self.assertEqual(failed_summary.status, "failed")
        self.assertEqual(failed_summary.payload["error"], "boom")


if __name__ == "__main__":
    unittest.main()
