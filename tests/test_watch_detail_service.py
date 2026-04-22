# -*- coding: utf-8 -*-
"""Tests for on-demand watch target detail payloads."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

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


def _make_daily_df(*, start_close: float, slope: float, days: int = 260) -> pd.DataFrame:
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


def _make_quote(
    *,
    code: str,
    price: float,
    pre_close: float,
    open_price: float,
    high: float,
    low: float,
    volume: int,
    change_pct: float,
    change_amount: float,
    amplitude: float,
):
    return SimpleNamespace(
        code=code,
        price=price,
        pre_close=pre_close,
        open_price=open_price,
        high=high,
        low=low,
        volume=volume,
        change_pct=change_pct,
        change_amount=change_amount,
        amplitude=amplitude,
    )


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

    def test_detail_supports_extended_timeframes_and_contract_fields(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        history_map = {"600519": _make_daily_df(start_close=10.0, slope=0.15, days=320)}
        analyzer = _FakeTrendAnalyzer({"600519": _make_result("600519", signal_score=88)})
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")

        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
            quote_loader=lambda code: _make_quote(
                code=code,
                price=58.0,
                pre_close=57.0,
                open_price=57.4,
                high=58.6,
                low=56.8,
                volume=2_500_000,
                change_pct=1.75,
                change_amount=1.0,
                amplitude=3.16,
            ),
        )

        detail_day = detail_service.get_target_detail(target.id, timeframe="day", window="60")
        self.assertEqual(detail_day["meta"]["timeframe"], "day")
        self.assertEqual(detail_day["meta"]["window"], "60")
        self.assertEqual(detail_day["meta"]["barCount"], 60)
        self.assertEqual(len(detail_day["kline"]), 60)
        self.assertEqual(len(detail_day["overlays"]["ma5"]), 60)
        self.assertEqual(len(detail_day["overlays"]["ma10"]), 60)
        self.assertEqual(len(detail_day["overlays"]["ma20"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["volMa"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["macd"]["dif"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["macd"]["dea"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["macd"]["bar"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["rsi"]["rsi6"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["rsi"]["rsi12"]), 60)
        self.assertEqual(len(detail_day["subIndicators"]["rsi"]["rsi24"]), 60)
        self.assertEqual(detail_day["quoteSnapshot"]["prevClose"], 57.0)
        self.assertEqual(detail_day["quoteSnapshot"]["changeAmount"], 1.0)
        self.assertEqual(detail_day["quoteSnapshot"]["changePct"], 1.75)
        self.assertEqual(detail_day["quoteSnapshot"]["amplitude"], 3.16)
        self.assertTrue(detail_day["meta"]["updatedAt"])

        detail_week = detail_service.get_target_detail(target.id, timeframe="week", window="30")
        self.assertEqual(detail_week["meta"]["timeframe"], "week")
        self.assertEqual(detail_week["meta"]["window"], "30")
        self.assertGreater(detail_week["meta"]["barCount"], 0)
        self.assertLessEqual(detail_week["meta"]["barCount"], 30)

        detail_month = detail_service.get_target_detail(target.id, timeframe="month", window="ytd")
        self.assertEqual(detail_month["meta"]["timeframe"], "month")
        self.assertEqual(detail_month["meta"]["window"], "ytd")
        self.assertGreater(detail_month["meta"]["barCount"], 0)

        detail_intraday = detail_service.get_target_detail(target.id, timeframe="intraday", window="250")
        self.assertEqual(detail_intraday["meta"]["timeframe"], "intraday")
        self.assertEqual(detail_intraday["meta"]["window"], "250")
        self.assertGreaterEqual(detail_intraday["meta"]["barCount"], 1)
        self.assertEqual(len(detail_intraday["kline"]), detail_intraday["meta"]["barCount"])

        with self.assertRaises(ValueError):
            detail_service.get_target_detail(target.id, timeframe="year", window="30")

        with self.assertRaises(ValueError):
            detail_service.get_target_detail(target.id, timeframe="day", window="14")

    def test_stock_target_detail_supports_timeframes_windows_and_series_payloads(self) -> None:
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

        detail_30 = detail_service.get_target_detail(
            target.id,
            timeframe="day",
            window="30",
        )
        self.assertEqual(len(detail_30["kline"]), 30)
        self.assertEqual(detail_30["active_member"]["member_code"], "600519")
        self.assertEqual(detail_30["latest_review"]["decision"], "buyable")
        self.assertEqual(detail_30["meta"]["timeframe"], "day")
        self.assertEqual(detail_30["meta"]["window"], "30")
        self.assertEqual(len(detail_30["overlays"]["ma5"]), 30)
        self.assertEqual(len(detail_30["sub_indicators"]["volume"]["bars"]), 30)
        self.assertEqual(len(detail_30["sub_indicators"]["macd"]["dif"]), 30)
        self.assertEqual(len(detail_30["sub_indicators"]["rsi"]["rsi6"]), 30)
        self.assertIn("quote_snapshot", detail_30)

        detail_250 = detail_service.get_target_detail(
            target.id,
            timeframe="day",
            window="250",
        )
        self.assertEqual(len(detail_250["kline"]), 250)

        detail_week = detail_service.get_target_detail(
            target.id,
            timeframe="week",
            window="60",
        )
        self.assertEqual(detail_week["meta"]["timeframe"], "week")
        self.assertGreaterEqual(len(detail_week["kline"]), 1)

        detail_month = detail_service.get_target_detail(
            target.id,
            timeframe="month",
            window="120",
        )
        self.assertEqual(detail_month["meta"]["timeframe"], "month")
        self.assertGreaterEqual(len(detail_month["kline"]), 1)

        detail_intraday = detail_service.get_target_detail(
            target.id,
            timeframe="intraday",
            window="30",
        )
        self.assertEqual(detail_intraday["meta"]["timeframe"], "intraday")
        self.assertEqual(detail_intraday["chart_type"], "line")

        with self.assertRaises(ValueError):
            detail_service.get_target_detail(target.id, timeframe="day", window="14")
        with self.assertRaises(ValueError):
            detail_service.get_target_detail(target.id, timeframe="year", window="30")

    def test_display_frame_applies_live_quote_to_day_week_and_month_payloads(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        today = date.today()
        start = today - timedelta(days=119)
        close = 20.0
        rows = []
        for index in range(100):
            current = start + timedelta(days=index)
            close += 0.3
            rows.append(
                {
                    "date": current,
                    "open": close - 0.2,
                    "high": close + 0.4,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 2_000_000 + index * 15_000,
                }
            )
        history_map = {"600519": pd.DataFrame(rows)}
        latest_close = float(history_map["600519"].iloc[-1]["close"])
        quote = _make_quote(
            code="600519",
            price=latest_close + 3.0,
            pre_close=latest_close,
            open_price=latest_close + 0.8,
            high=latest_close + 3.6,
            low=latest_close - 0.4,
            volume=3_600_000,
            change_pct=5.0,
            change_amount=3.0,
            amplitude=6.1,
        )
        analyzer = _FakeTrendAnalyzer({"600519": _make_result("600519", signal_score=80)})
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
            quote_loader=lambda code: quote,
        )

        detail_day = detail_service.get_target_detail(target.id, timeframe="day", window="30")
        self.assertEqual(detail_day["kline"][-1]["date"], today.isoformat())
        self.assertEqual(detail_day["kline"][-1]["open"], quote.open_price)
        self.assertEqual(detail_day["kline"][-1]["high"], quote.high)
        self.assertEqual(detail_day["kline"][-1]["low"], quote.low)
        self.assertEqual(detail_day["kline"][-1]["close"], quote.price)

        detail_week = detail_service.get_target_detail(target.id, timeframe="week", window="30")
        self.assertEqual(detail_week["kline"][-1]["close"], quote.price)

        detail_month = detail_service.get_target_detail(target.id, timeframe="month", window="120")
        self.assertEqual(detail_month["kline"][-1]["close"], quote.price)

    def test_rsi_subindicator_preserves_100_when_window_has_no_losses(self) -> None:
        from src.repositories.watch_repo import WatchRepository
        from src.services.watch_detail_service import WatchDetailService
        from src.services.watch_summary_service import WatchSummaryService
        from src.services.watchlist_service import WatchlistService

        repo = WatchRepository(self.db)
        history_map = {"600519": _make_daily_df(start_close=10.0, slope=1.0, days=80)}
        analyzer = _FakeTrendAnalyzer({"600519": _make_result("600519", signal_score=96)})
        summary_service = WatchSummaryService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
        )
        watchlist_service = WatchlistService(db_manager=self.db, repo=repo, summary_service=summary_service)
        target = watchlist_service.create_target("600519", display_name="贵州茅台")
        detail_service = WatchDetailService(
            db_manager=self.db,
            repo=repo,
            trend_analyzer=analyzer,
            history_loader=lambda code, lookback_bars: history_map[code].tail(lookback_bars).copy(),
        )

        detail = detail_service.get_target_detail(target.id, timeframe="day", window="30")
        self.assertEqual(detail["subIndicators"]["rsi"]["rsi6"][-1], 100.0)
        self.assertEqual(detail["subIndicators"]["rsi"]["rsi12"][-1], 100.0)
        self.assertEqual(detail["subIndicators"]["rsi"]["rsi24"][-1], 100.0)

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

        default_detail = detail_service.get_target_detail(target.id, timeframe="day", window="30")
        self.assertEqual(default_detail["active_member"]["member_code"], "000977")
        self.assertEqual(default_detail["latest_review"]["decision"], "buyable")
        self.assertGreaterEqual(len(default_detail["member_options"]), 4)

        switched_detail = detail_service.get_target_detail(
            target.id,
            timeframe="day",
            window="60",
            member_code="603019",
        )
        self.assertEqual(switched_detail["active_member"]["member_code"], "603019")
        self.assertEqual(switched_detail["latest_review"]["decision"], "watch_more")
        self.assertEqual(switched_detail["meta"]["window"], "60")

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

        switched_detail = detail_service.get_target_detail(
            target.id,
            timeframe="day",
            window="30",
            member_code="603019",
        )
        self.assertEqual(switched_detail["active_member"]["member_code"], "603019")
        self.assertEqual(switched_detail["latest_review"]["decision"], "watch_more")


if __name__ == "__main__":
    unittest.main()
