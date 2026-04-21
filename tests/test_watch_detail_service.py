# -*- coding: utf-8 -*-
"""Tests for on-demand watch target detail payloads."""

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
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.25,
                "close": close,
                "volume": 1_000_000 + index * 10_000,
            }
        )
    return pd.DataFrame(rows)


def _make_result(code: str, *, signal_score: int, buy_signal: BuySignal = BuySignal.BUY) -> TrendAnalysisResult:
    return TrendAnalysisResult(
        code=code,
        trend_status=TrendStatus.BULL,
        ma_alignment="多头排列",
        trend_strength=75.0,
        ma5=10.0,
        ma10=9.8,
        ma20=9.5,
        ma60=9.2,
        current_price=10.2,
        bias_ma5=1.0,
        bias_ma10=0.5,
        bias_ma20=1.5,
        volume_status=VolumeStatus.SHRINK_VOLUME_DOWN,
        volume_ratio_5d=0.7,
        volume_trend="缩量回调",
        support_ma5=True,
        support_ma10=False,
        macd_status=MACDStatus.GOLDEN_CROSS,
        macd_signal="金叉",
        rsi_6=56.0,
        rsi_12=58.0,
        rsi_24=54.0,
        rsi_status=RSIStatus.STRONG_BUY,
        rsi_signal="强势买入",
        buy_signal=buy_signal,
        signal_score=signal_score,
        signal_reasons=["回踩 5 日线"],
        risk_factors=["等待放量确认"],
    )


class _FakeTrendAnalyzer:
    def __init__(self, result_map: dict[str, TrendAnalysisResult]) -> None:
        self.result_map = result_map

    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        result = self.result_map[code]
        cloned = _make_result(code, signal_score=result.signal_score, buy_signal=result.buy_signal)
        cloned.signal_reasons = list(result.signal_reasons)
        cloned.risk_factors = list(result.risk_factors)
        cloned.current_price = float(df.iloc[-1]["close"])
        return cloned


class WatchDetailServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_watch_detail.db")
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_stock_target_detail_supports_7_and_30_day_windows(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        history_map = {"600519": _make_daily_df(start_close=10.0, slope=0.2)}
        analyzer = _FakeTrendAnalyzer({"600519": _make_result("600519", signal_score=82)})
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        event = repo.upsert_signal_event(
            target_id=target.id,
            member_id=repo.list_members(target.id)[0].id,
            member_code="600519",
            member_name="贵州茅台",
            signal_date="2026-04-21",
            dedupe_key=f"{target.id}:600519:2026-04-21:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=82,
            status="accepted",
            payload={"source": "detail-test"},
        )
        repo.save_review_result(
            signal_event_id=event.id,
            review_round=1,
            decision="buyable",
            confidence=0.9,
            summary="近期可跟踪",
            payload={"source": "detail-test"},
        )
        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )

        detail_7 = detail_service.get_target_detail(target.id, window_days=7)
        self.assertEqual(len(detail_7["kline"]), 7)
        self.assertEqual(detail_7["active_member"]["member_code"], "600519")
        self.assertEqual(detail_7["latest_review"]["decision"], "buyable")

        detail_30 = detail_service.get_target_detail(target.id, window_days=30)
        self.assertEqual(len(detail_30["kline"]), 30)
        self.assertEqual(detail_30["summary"]["status"], "ready")
        self.assertEqual(detail_30["indicators"]["buy_signal"], "买入")
        self.assertTrue(detail_30["indicators"]["support_levels"])
        self.assertTrue(detail_30["indicators"]["resistance_levels"])

        with self.assertRaises(ValueError):
            detail_service.get_target_detail(target.id, window_days=14)

    def test_theme_detail_uses_selected_member_and_member_scoped_latest_review(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        history_map = {
            "000977": _make_daily_df(start_close=20.0, slope=0.25),
            "603019": _make_daily_df(start_close=18.0, slope=0.08),
            "002230": _make_daily_df(start_close=15.0, slope=0.05),
            "512720": _make_daily_df(start_close=8.0, slope=0.03),
        }
        analyzer = _FakeTrendAnalyzer(
            {
                "000977": _make_result("000977", signal_score=90, buy_signal=BuySignal.STRONG_BUY),
                "603019": _make_result("603019", signal_score=71),
                "002230": _make_result("002230", signal_score=66),
                "512720": _make_result("512720", signal_score=62),
            }
        )
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("算力", target_kind="theme")
        members = {member.member_code: member for member in repo.list_members(target.id)}

        event_1 = repo.upsert_signal_event(
            target_id=target.id,
            member_id=members["000977"].id,
            member_code="000977",
            member_name=members["000977"].member_name,
            signal_date="2026-04-21",
            dedupe_key=f"{target.id}:000977:2026-04-21:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=90,
            status="accepted",
            payload={"source": "detail-test"},
        )
        repo.save_review_result(
            signal_event_id=event_1.id,
            review_round=1,
            decision="buyable",
            confidence=0.95,
            summary="代表成员可跟踪",
            payload={"source": "detail-test"},
        )

        event_2 = repo.upsert_signal_event(
            target_id=target.id,
            member_id=members["603019"].id,
            member_code="603019",
            member_name=members["603019"].member_name,
            signal_date="2026-04-22",
            dedupe_key=f"{target.id}:603019:2026-04-22:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=71,
            status="accepted",
            payload={"source": "detail-test"},
        )
        repo.save_review_result(
            signal_event_id=event_2.id,
            review_round=1,
            decision="watch_more",
            confidence=0.68,
            summary="次级成员继续观察",
            payload={"source": "detail-test"},
        )

        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )

        default_detail = detail_service.get_target_detail(target.id, window_days=7)
        self.assertEqual(default_detail["active_member"]["member_code"], "000977")
        self.assertEqual(default_detail["latest_review"]["decision"], "buyable")
        self.assertGreaterEqual(len(default_detail["member_options"]), 4)

        switched_detail = detail_service.get_target_detail(target.id, window_days=30, member_code="603019")
        self.assertEqual(switched_detail["active_member"]["member_code"], "603019")
        self.assertEqual(switched_detail["latest_review"]["decision"], "watch_more")
        self.assertEqual(len(switched_detail["kline"]), 30)

    def test_latest_review_lookup_is_member_scoped_without_page_truncation(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        history_map = {
            "000977": _make_daily_df(start_close=20.0, slope=0.25),
            "603019": _make_daily_df(start_close=18.0, slope=0.08),
            "002230": _make_daily_df(start_close=15.0, slope=0.05),
            "512720": _make_daily_df(start_close=8.0, slope=0.03),
        }
        analyzer = _FakeTrendAnalyzer(
            {
                "000977": _make_result("000977", signal_score=90, buy_signal=BuySignal.STRONG_BUY),
                "603019": _make_result("603019", signal_score=71),
                "002230": _make_result("002230", signal_score=66),
                "512720": _make_result("512720", signal_score=62),
            }
        )
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("算力", target_kind="theme")
        members = {member.member_code: member for member in repo.list_members(target.id)}

        review_event = repo.upsert_signal_event(
            target_id=target.id,
            member_id=members["603019"].id,
            member_code="603019",
            member_name=members["603019"].member_name,
            signal_date="2026-01-01",
            dedupe_key=f"{target.id}:603019:2026-01-01:stage_buy_point:v1",
            signal_type="stage_buy_point",
            signal_score=71,
            status="accepted",
            payload={"source": "detail-test"},
        )
        repo.save_review_result(
            signal_event_id=review_event.id,
            review_round=1,
            decision="watch_more",
            confidence=0.68,
            summary="次级成员继续观察",
            payload={"source": "detail-test"},
        )

        for index in range(205):
            repo.upsert_signal_event(
                target_id=target.id,
                member_id=members["000977"].id,
                member_code="000977",
                member_name=members["000977"].member_name,
                signal_date=f"2026-04-{(index % 28) + 1:02d}",
                dedupe_key=f"{target.id}:000977:2026-04-{(index % 28) + 1:02d}:stage_buy_point:v{index}",
                signal_type="stage_buy_point",
                signal_score=90,
                status="accepted",
                payload={"source": "detail-test", "index": index},
            )

        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].copy(),
        )

        switched_detail = detail_service.get_target_detail(target.id, window_days=7, member_code="603019")
        self.assertEqual(switched_detail["active_member"]["member_code"], "603019")
        self.assertEqual(switched_detail["latest_review"]["decision"], "watch_more")


if __name__ == "__main__":
    unittest.main()
