# -*- coding: utf-8 -*-
"""Tests for watchlist target resolution and candidate signal scanning."""

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


def _make_daily_df(days: int = 35) -> pd.DataFrame:
    start = date(2026, 3, 1)
    rows = []
    close = 10.0
    for index in range(days):
        current = start + timedelta(days=index)
        close += 0.08
        rows.append(
            {
                "date": current,
                "open": close - 0.12,
                "high": close + 0.18,
                "low": close - 0.2,
                "close": close,
                "volume": 1_000_000 + index * 10_000,
            }
        )
    return pd.DataFrame(rows)


def _make_signal_result(
    *,
    code: str,
    buy_signal: BuySignal,
    score: float,
    risk_factors: list[str] | None = None,
) -> TrendAnalysisResult:
    result = TrendAnalysisResult(
        code=code,
        trend_status=TrendStatus.BULL,
        ma_alignment="多头排列",
        trend_strength=76.0,
        ma5=10.0,
        ma10=9.8,
        ma20=9.5,
        ma60=9.2,
        current_price=10.1,
        bias_ma5=1.0,
        bias_ma10=0.0,
        bias_ma20=0.0,
        volume_status=VolumeStatus.SHRINK_VOLUME_DOWN,
        volume_ratio_5d=0.65,
        volume_trend="缩量回调",
        support_ma5=True,
        support_ma10=False,
        macd_status=MACDStatus.GOLDEN_CROSS,
        macd_signal="金叉",
        rsi_6=55.0,
        rsi_12=58.0,
        rsi_24=54.0,
        rsi_status=RSIStatus.STRONG_BUY,
        rsi_signal="强势",
        buy_signal=buy_signal,
        signal_score=int(score),
        signal_reasons=["测试信号"],
        risk_factors=risk_factors or [],
    )
    return result


class _FakeTrendAnalyzer:
    def __init__(self, result: TrendAnalysisResult):
        self._result = result
        self.calls: list[str] = []

    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        self.calls.append(code)
        result = _make_signal_result(
            code=code,
            buy_signal=self._result.buy_signal,
            score=self._result.signal_score,
            risk_factors=list(self._result.risk_factors),
        )
        result.signal_reasons = list(self._result.signal_reasons)
        result.support_ma5 = self._result.support_ma5
        result.support_ma10 = self._result.support_ma10
        result.volume_status = self._result.volume_status
        result.volume_trend = self._result.volume_trend
        result.macd_status = self._result.macd_status
        result.macd_signal = self._result.macd_signal
        result.trend_status = self._result.trend_status
        result.trend_strength = self._result.trend_strength
        result.bias_ma5 = self._result.bias_ma5
        return result


class WatchSignalServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_watch_signal.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_watchlist_service_creates_stock_etf_and_theme_targets(self) -> None:
        from src.services.watchlist_service import WatchlistService

        service = WatchlistService(db_manager=self.db)

        stock_target = service.create_target("SH600519", display_name="贵州茅台")
        self.assertEqual(stock_target.target_kind, "stock")
        self.assertEqual(stock_target.target_key, "600519")
        stock_members = service.repo.list_members(stock_target.id)
        self.assertEqual(len(stock_members), 1)
        self.assertEqual(stock_members[0].member_kind, "stock")
        self.assertEqual(stock_members[0].member_code, "600519")

        etf_target = service.create_target("512720", display_name="计算机ETF")
        self.assertEqual(etf_target.target_kind, "etf")
        self.assertEqual(etf_target.target_key, "512720")
        etf_members = service.repo.list_members(etf_target.id)
        self.assertEqual(len(etf_members), 1)
        self.assertEqual(etf_members[0].member_kind, "etf")

        theme_target = service.create_target("算力", target_kind="theme")
        self.assertEqual(theme_target.target_kind, "theme")
        self.assertEqual(theme_target.target_key, "compute_power")
        self.assertEqual(theme_target.status, "active")
        theme_members = service.repo.list_members(theme_target.id)
        self.assertGreaterEqual(len(theme_members), 2)
        self.assertTrue(any(member.member_kind == "etf" for member in theme_members))

    def test_unknown_theme_creates_unsupported_target(self) -> None:
        from src.services.watchlist_service import WatchlistService

        service = WatchlistService(db_manager=self.db)
        target = service.create_target("不存在的主题", target_kind="theme")

        self.assertEqual(target.target_kind, "theme")
        self.assertEqual(target.status, "unsupported")
        self.assertEqual(service.repo.list_members(target.id), [])

    def test_signal_scan_creates_candidate_and_reuses_dedupe(self) -> None:
        from src.services.watchlist_service import WatchlistService
        from src.services.watch_signal_service import WatchSignalService

        watchlist_service = WatchlistService(db_manager=self.db)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        expected = _make_signal_result(code="600519", buy_signal=BuySignal.BUY, score=68)
        analyzer = _FakeTrendAnalyzer(expected)
        history_df = _make_daily_df()

        signal_service = WatchSignalService(
            db_manager=self.db,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_df.copy(),
        )

        first_batch = signal_service.scan_target(target.id)
        self.assertEqual(len(first_batch), 1)
        first = first_batch[0]
        self.assertEqual(first.member_code, "600519")
        self.assertEqual(first.signal_type, "stage_buy_point")

        second_batch = signal_service.scan_target(target.id)
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(second_batch[0].id, first.id)

        rows, total = watchlist_service.repo.list_signal_events(target_id=target.id)
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(analyzer.calls, ["600519", "600519"])

    def test_signal_scan_skips_non_candidate_result(self) -> None:
        from src.services.watchlist_service import WatchlistService
        from src.services.watch_signal_service import WatchSignalService

        watchlist_service = WatchlistService(db_manager=self.db)
        target = watchlist_service.create_target("000001", display_name="平安银行")
        expected = _make_signal_result(
            code="000001",
            buy_signal=BuySignal.WAIT,
            score=42,
            risk_factors=["❌ 乖离率过高(8.0%>5.0%)，严禁追高！"],
        )
        analyzer = _FakeTrendAnalyzer(expected)

        signal_service = WatchSignalService(
            db_manager=self.db,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: _make_daily_df(),
        )

        events = signal_service.scan_target(target.id)
        self.assertEqual(events, [])

        rows, total = watchlist_service.repo.list_signal_events(target_id=target.id)
        self.assertEqual(total, 0)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
