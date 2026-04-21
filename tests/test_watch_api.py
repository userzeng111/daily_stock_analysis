# -*- coding: utf-8 -*-
"""Integration tests for watch API endpoints."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
from fastapi.testclient import TestClient

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from api.app import create_app
from src.config import Config
from src.repositories.watch_repo import WatchRepository
from src.services.watchlist_service import WatchlistService
from src.storage import DatabaseManager


class WatchApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.env_path = self.data_dir / ".env"
        self.db_path = self.data_dir / "watch_api_test.db"
        self.env_path.write_text(
            "\n".join(
                [
                    "STOCK_LIST=600519",
                    "GEMINI_API_KEY=test",
                    "ADMIN_AUTH_ENABLED=false",
                    f"DATABASE_PATH={self.db_path}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ["DATABASE_PATH"] = str(self.db_path)
        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.app = create_app(static_dir=self.data_dir / "empty-static")
        self.client = TestClient(self.app)
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        os.environ.pop("ENV_FILE", None)
        os.environ.pop("DATABASE_PATH", None)
        self.temp_dir.cleanup()

    def _save_history(self, symbol: str, *, start_close: float = 10.0, slope: float = 0.2, days: int = 35) -> None:
        start = date(2026, 3, 1)
        rows = []
        close = start_close
        for index in range(days):
            current = start + timedelta(days=index)
            close += slope
            rows.append(
                {
                    "date": current,
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.25,
                    "close": close,
                    "volume": 1_000_000 + index * 10_000,
                    "amount": close * 1000,
                    "pct_chg": 0.0,
                }
            )
        self.db.save_daily_data(pd.DataFrame(rows), code=symbol, data_source="watch-api-test")

    def _seed_event(self):
        watchlist_service = WatchlistService(db_manager=self.db)
        self._save_history("600519")
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        repo = WatchRepository(self.db)
        member = repo.list_members(target.id)[0]
        event = repo.upsert_signal_event(
            target_id=target.id,
            member_id=member.id,
            member_code=member.member_code,
            member_name=member.member_name,
            signal_date=date(2026, 4, 21),
            dedupe_key=f"{target.id}:{member.member_code}:2026-04-21:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=68,
            status="accepted",
            payload={"source": "api-test"},
        )
        repo.save_review_result(
            signal_event_id=event.id,
            review_round=1,
            decision="buyable",
            confidence=0.91,
            summary="review ok",
            payload={"source": "api-test"},
        )
        return target, event

    def test_target_and_runtime_endpoints(self) -> None:
        create_resp = self.client.post(
            "/api/v1/watch/targets",
            json={"input_text": "600519", "display_name": "贵州茅台"},
        )
        self.assertEqual(create_resp.status_code, 200)
        created = create_resp.json()
        self.assertEqual(created["target_kind"], "stock")

        target_id = created["id"]
        list_resp = self.client.get("/api/v1/watch/targets", params={"page": 1, "limit": 20})
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.json()["total"], 1)
        self.assertIn("summary", list_resp.json()["items"][0])
        self.assertIn(list_resp.json()["items"][0]["summary"]["status"], {"ready", "failed", "pending"})

        detail_resp = self.client.get(f"/api/v1/watch/targets/{target_id}")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()["id"], target_id)

        patch_resp = self.client.patch(
            f"/api/v1/watch/targets/{target_id}",
            json={"status": "paused"},
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.json()["status"], "paused")

        start_resp = self.client.post("/api/v1/watch/runtime/start")
        self.assertEqual(start_resp.status_code, 200)
        self.assertTrue(start_resp.json()["enabled"])

        status_resp = self.client.get("/api/v1/watch/runtime/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertTrue(status_resp.json()["enabled"])

        stop_resp = self.client.post("/api/v1/watch/runtime/stop")
        self.assertEqual(stop_resp.status_code, 200)
        self.assertFalse(stop_resp.json()["enabled"])

        delete_resp = self.client.delete(f"/api/v1/watch/targets/{target_id}")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertTrue(delete_resp.json()["success"])

    def test_first_parallel_watch_requests_do_not_hit_database_init_race(self) -> None:
        statuses: list[int] = []
        start_barrier = threading.Barrier(2)
        lock = threading.Lock()

        def _request(path: str) -> None:
            start_barrier.wait()
            response = self.client.get(path)
            with lock:
                statuses.append(response.status_code)

        threads = [
            threading.Thread(target=_request, args=("/api/v1/watch/targets",)),
            threading.Thread(target=_request, args=("/api/v1/watch/runtime/status",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertCountEqual(statuses, [200, 200])

    def test_event_detail_and_stream_endpoints(self) -> None:
        from api.v1.endpoints.watch import watch_stream
        from src.services.watch_event_bus import WatchEventBus

        target, event = self._seed_event()

        list_resp = self.client.get(
            "/api/v1/watch/events",
            params={"page": 1, "limit": 20, "target_id": target.id},
        )
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["id"], event.id)
        self.assertEqual(payload["items"][0]["latest_review_summary"]["decision"], "buyable")

        detail_resp = self.client.get(f"/api/v1/watch/events/{event.id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["id"], event.id)
        self.assertEqual(detail["latest_review"]["decision"], "buyable")

        target_detail_resp = self.client.get(f"/api/v1/watch/targets/{target.id}/detail", params={"window": 7})
        self.assertEqual(target_detail_resp.status_code, 200)
        target_detail = target_detail_resp.json()
        self.assertEqual(target_detail["target"]["id"], target.id)
        self.assertEqual(len(target_detail["kline"]), 7)
        self.assertEqual(target_detail["latest_review"]["decision"], "buyable")

        async def _read_first_chunk():
            response = await watch_stream(bus=WatchEventBus())
            return await response.body_iterator.__anext__()

        chunk = asyncio.run(_read_first_chunk())
        self.assertIn("event: watch.connected", chunk)

    def test_list_targets_exposes_flattened_summary_contract(self) -> None:
        watchlist_service = WatchlistService(db_manager=self.db)
        self._save_history("600519")
        watchlist_service.create_target("600519", display_name="贵州茅台")

        response = self.client.get("/api/v1/watch/targets", params={"page": 1, "limit": 20})
        self.assertEqual(response.status_code, 200)
        summary = response.json()["items"][0]["summary"]
        self.assertEqual(summary["status"], "ready")
        self.assertIsNotNone(summary["signal_score"])
        self.assertIsNotNone(summary["action"])
        self.assertIsNotNone(summary["trend_status"])
        self.assertIsNotNone(summary["buy_signal"])
        self.assertIsNotNone(summary["period_return_pct"])
        self.assertIsNotNone(summary["updated_at"])
        self.assertEqual(summary["member_count"], 1)

    def test_watch_detail_accepts_bare_target_code_when_history_uses_market_suffix(self) -> None:
        watchlist_service = WatchlistService(db_manager=self.db)
        self._save_history("600519.SH")
        target = watchlist_service.create_target("600519", display_name="贵州茅台")

        list_resp = self.client.get("/api/v1/watch/targets", params={"page": 1, "limit": 20})
        self.assertEqual(list_resp.status_code, 200)
        summary = next(item["summary"] for item in list_resp.json()["items"] if item["id"] == target.id)
        self.assertEqual(summary["status"], "ready")

        detail_resp = self.client.get(
            f"/api/v1/watch/targets/{target.id}/detail",
            params={"window": 7},
        )
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(len(detail_resp.json()["kline"]), 7)

    def test_theme_target_detail_supports_member_code(self) -> None:
        watchlist_service = WatchlistService(db_manager=self.db)
        self._save_history("603019", start_close=18.0, slope=0.1)
        target = watchlist_service.create_target("算力", target_kind="theme")

        detail_resp = self.client.get(
            f"/api/v1/watch/targets/{target.id}/detail",
            params={"window": 30, "member_code": "603019"},
        )
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["target"]["id"], target.id)
        self.assertEqual(detail["active_member"]["member_code"], "603019")
        self.assertGreaterEqual(len(detail["member_options"]), 1)

        invalid_resp = self.client.get(
            f"/api/v1/watch/targets/{target.id}/detail",
            params={"window": 14},
        )
        self.assertEqual(invalid_resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
