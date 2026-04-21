# -*- coding: utf-8 -*-
"""Tests for watch summary snapshot refresh and immediate availability."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta

import pandas as pd

from src.config import Config
from src.stock_analyzer import (
    BuySignal,
    MACDStatus,
    RSIStatus,
    TrendAnalysisResult,
    TrendStatus,
    VolumeStatus,
)
from src.storage import DatabaseManager


def _make_daily_df(*, start_close: float, slope: float, days: int = 35) -> pd.DataFrame:
    start = date(2026, 3, 1)
    rows = []
    close = start_close
    for index in range(days):
        current = start + timedelta(days=index)
        close += slope
        rows.append(
            {
                "date": current,
                "open": close - 0.12,
                "high": close + 0.2,
                "low": close - 0.25,
                "close": close,
                "volume": 1_000_000 + index * 12_000,
            }
        )
    return pd.DataFrame(rows)


def _make_result(code: str, *, signal_score: int, buy_signal: BuySignal = BuySignal.BUY) -> TrendAnalysisResult:
    return TrendAnalysisResult(
        code=code,
        trend_status=TrendStatus.BULL,
        ma_alignment="多头排列",
        trend_strength=70.0 + signal_score / 10.0,
        ma5=10.0,
        ma10=9.8,
        ma20=9.4,
        ma60=9.0,
        current_price=10.2,
        bias_ma5=1.2,
        bias_ma10=0.8,
        bias_ma20=2.1,
        volume_status=VolumeStatus.SHRINK_VOLUME_DOWN,
        volume_ratio_5d=0.72,
        volume_trend="缩量回调",
        support_ma5=True,
        support_ma10=False,
        macd_status=MACDStatus.GOLDEN_CROSS,
        macd_signal="金叉",
        rsi_6=56.0,
        rsi_12=58.0,
        rsi_24=53.0,
        rsi_status=RSIStatus.STRONG_BUY,
        rsi_signal="强势买入",
        buy_signal=buy_signal,
        signal_score=signal_score,
        signal_reasons=["回踩 5 日线", "成交量温和收缩"],
        risk_factors=["需要确认量能回补"],
    )


class _FakeTrendAnalyzer:
    def __init__(self, result_by_code: dict[str, TrendAnalysisResult]) -> None:
        self.result_by_code = result_by_code
        self.calls: list[str] = []

    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        self.calls.append(code)
        result = self.result_by_code[code]
        cloned = _make_result(code, signal_score=result.signal_score, buy_signal=result.buy_signal)
        cloned.signal_reasons = list(result.signal_reasons)
        cloned.risk_factors = list(result.risk_factors)
        cloned.trend_status = result.trend_status
        cloned.volume_status = result.volume_status
        cloned.macd_status = result.macd_status
        cloned.current_price = float(df.iloc[-1]["close"])
        return cloned


class _ExplodingSummaryService:
    def __init__(self, repo) -> None:
        self.repo = repo
        self.calls: list[int] = []

    def refresh_target_snapshot(self, target_id: int, summary_window_days: int = 7):
        self.calls.append(target_id)
        raise RuntimeError("summary loader unavailable")


class WatchSummaryServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_watch_summary.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_refresh_target_snapshot_builds_ready_stock_summary_from_30_bars(self) -> None:
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        result = _make_result("600519", signal_score=81)
        analyzer = _FakeTrendAnalyzer({"600519": result})
        history_map = {"600519": _make_daily_df(start_close=10.0, slope=0.2)}

        service = WatchSummaryService(
            db_manager=self.db,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")

        snapshot = service.refresh_target_snapshot(target.id)

        self.assertEqual(snapshot["status"], "ready")
        self.assertEqual(snapshot["target_id"], target.id)
        self.assertEqual(snapshot["summary_window_days"], 7)
        self.assertEqual(snapshot["signal_score"], 81)
        self.assertEqual(snapshot["action"], "买入")
        self.assertEqual(snapshot["buy_signal"], "买入")
        self.assertEqual(snapshot["trend_status"], "多头排列")
        self.assertGreater(snapshot["period_return_pct"], 0.0)
        self.assertEqual(snapshot["member_count"], 1)
        self.assertIsNotNone(snapshot["updated_at"])
        self.assertEqual(snapshot["member"]["member_code"], "600519")
        self.assertEqual(snapshot["analysis"]["buy_signal"], "买入")
        self.assertEqual(snapshot["metrics"]["bar_count"], 30)
        self.assertEqual(snapshot["metrics"]["summary_bar_count"], 7)
        self.assertGreater(snapshot["metrics"]["return_pct"], 0.0)
        self.assertIn("7日", snapshot["brief"])

        saved = service.repo.get_target_snapshot(target.id, summary_window_days=7)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.status, "ready")
        self.assertEqual(saved.payload["member"]["member_code"], "600519")
        self.assertEqual(analyzer.calls, ["600519"])

    def test_refresh_target_snapshot_aggregates_theme_members_and_selects_representative(self) -> None:
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        history_map = {
            "000977": _make_daily_df(start_close=20.0, slope=0.35),
            "603019": _make_daily_df(start_close=18.0, slope=0.12),
            "002230": _make_daily_df(start_close=15.0, slope=0.05),
            "512720": _make_daily_df(start_close=8.0, slope=0.08),
        }
        analyzer = _FakeTrendAnalyzer(
            {
                "000977": _make_result("000977", signal_score=92, buy_signal=BuySignal.STRONG_BUY),
                "603019": _make_result("603019", signal_score=78),
                "002230": _make_result("002230", signal_score=66),
                "512720": _make_result("512720", signal_score=71),
            }
        )

        service = WatchSummaryService(
            db_manager=self.db,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db)
        target = watchlist_service.create_target("算力", target_kind="theme")

        snapshot = service.refresh_target_snapshot(target.id)

        self.assertEqual(snapshot["status"], "ready")
        self.assertEqual(snapshot["target_kind"], "theme")
        self.assertEqual(snapshot["signal_score"], 92)
        self.assertEqual(snapshot["action"], "强烈买入")
        self.assertEqual(snapshot["buy_signal"], "强烈买入")
        self.assertEqual(snapshot["trend_status"], "多头排列")
        self.assertEqual(snapshot["representative_member_code"], "000977")
        self.assertEqual(snapshot["representative_member_name"], "浪潮信息")
        self.assertEqual(snapshot["member_count"], 4)
        self.assertEqual(snapshot["representative_member"]["member_code"], "000977")
        self.assertEqual(snapshot["aggregate"]["member_count"], 4)
        self.assertEqual(snapshot["aggregate"]["ready_member_count"], 4)
        self.assertEqual(len(snapshot["members"]), 4)
        self.assertGreater(snapshot["aggregate"]["avg_return_pct"], 0.0)

        saved = service.repo.get_target_snapshot(target.id, summary_window_days=7)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.payload["representative_member"]["member_code"], "000977")

    def test_create_target_refreshes_summary_immediately_and_exposes_failed_snapshot(self) -> None:
        from src.services.watchlist_service import WatchlistService

        service = WatchlistService(
            db_manager=self.db,
            summary_service=_ExplodingSummaryService(repo=None),
        )

        target = service.create_target("600519", display_name="贵州茅台")
        items, total = service.list_targets(page=1, limit=20)

        self.assertEqual(total, 1)
        self.assertEqual(items[0]["id"], target.id)
        self.assertIn("summary", items[0])
        self.assertEqual(items[0]["summary"]["status"], "failed")
        self.assertEqual(items[0]["summary"]["summary_window_days"], 7)
        self.assertIn("summary loader unavailable", items[0]["summary"]["error"])


if __name__ == "__main__":
    unittest.main()
