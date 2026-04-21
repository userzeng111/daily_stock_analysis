# -*- coding: utf-8 -*-
"""Candidate buy-point scanning for watch targets."""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.repositories.stock_repo import StockRepository
from src.repositories.watch_repo import WatchRepository
from src.stock_analyzer import BuySignal, StockTrendAnalyzer, TrendStatus
from src.storage import DatabaseManager, WatchSignalEvent, WatchTarget, WatchTargetMember


class WatchSignalService:
    """Scan tracked securities and emit deduplicated candidate events."""

    SIGNAL_TYPE = "stage_buy_point"
    STRATEGY_VERSION = "v1"

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        stock_repo: Optional[StockRepository] = None,
        trend_analyzer: Optional[StockTrendAnalyzer] = None,
        history_loader: Optional[Callable[[str, int], pd.DataFrame]] = None,
        lookback_bars: int = 30,
        signal_score_threshold: int = 60,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.stock_repo = stock_repo or StockRepository(self.db)
        self.trend_analyzer = trend_analyzer or StockTrendAnalyzer()
        self.history_loader = history_loader
        self.lookback_bars = max(20, int(lookback_bars))
        self.signal_score_threshold = int(signal_score_threshold)

    def scan_target(self, target_id: int) -> List[WatchSignalEvent]:
        target = self.repo.get_target(target_id)
        if target is None or target.status != "active":
            return []

        events: List[WatchSignalEvent] = []
        for member in self.repo.list_members(target.id):
            event = self.scan_member(target, member)
            if event is not None:
                events.append(event)
        return events

    def scan_member(
        self,
        target: WatchTarget,
        member: WatchTargetMember,
    ) -> Optional[WatchSignalEvent]:
        df = self._load_history(member.member_code)
        if df.empty or len(df) < self.lookback_bars:
            return None

        result = self.trend_analyzer.analyze(df.copy(), member.member_code)
        if not self._is_candidate(result):
            return None

        signal_day = self._coerce_signal_day(df.iloc[-1]["date"])
        payload = self._build_payload(target, member, result)
        dedupe_key = self._build_dedupe_key(
            target_id=target.id,
            member_code=member.member_code,
            signal_day=signal_day,
        )

        return self.repo.upsert_signal_event(
            target_id=target.id,
            member_id=member.id,
            member_code=member.member_code,
            member_name=member.member_name,
            signal_date=signal_day,
            dedupe_key=dedupe_key,
            signal_type=self.SIGNAL_TYPE,
            signal_score=float(result.signal_score),
            status="candidate",
            payload=payload,
        )

    def _load_history(self, code: str) -> pd.DataFrame:
        if self.history_loader is not None:
            raw = self.history_loader(code, self.lookback_bars)
            df = raw.copy() if isinstance(raw, pd.DataFrame) else pd.DataFrame()
        else:
            rows = self.stock_repo.get_latest(code, days=max(self.lookback_bars, 40))
            df = pd.DataFrame(
                [
                    {
                        "date": row.date,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "volume": row.volume or 0,
                    }
                    for row in rows
                ]
            )

        if df.empty:
            return df

        normalized = df.copy()
        normalized["date"] = pd.to_datetime(normalized["date"]).dt.date
        for column in ("open", "high", "low", "close", "volume"):
            if column not in normalized.columns:
                normalized[column] = 0
        normalized = normalized.sort_values("date").reset_index(drop=True)
        return normalized.tail(max(self.lookback_bars, 30))

    def _is_candidate(self, result) -> bool:
        if result.buy_signal not in {BuySignal.BUY, BuySignal.STRONG_BUY}:
            return False
        if int(result.signal_score or 0) < self.signal_score_threshold:
            return False
        if result.trend_status in {TrendStatus.BEAR, TrendStatus.STRONG_BEAR}:
            return False
        if any("严禁追高" in str(risk) for risk in (result.risk_factors or [])):
            return False
        return True

    def _build_payload(self, target: WatchTarget, member: WatchTargetMember, result) -> Dict[str, object]:
        return {
            "target_kind": target.target_kind,
            "target_key": target.target_key,
            "theme_id": target.theme_id,
            "theme_name": target.theme_name,
            "member_kind": member.member_kind,
            "buy_signal": result.buy_signal.value,
            "signal_score": result.signal_score,
            "trend_status": result.trend_status.value,
            "volume_status": result.volume_status.value,
            "macd_status": result.macd_status.value,
            "current_price": result.current_price,
            "support_ma5": result.support_ma5,
            "support_ma10": result.support_ma10,
            "signal_reasons": list(result.signal_reasons or []),
            "risk_factors": list(result.risk_factors or []),
        }

    @staticmethod
    def _coerce_signal_day(value) -> date:
        if isinstance(value, date):
            return value
        return pd.to_datetime(value).date()

    def _build_dedupe_key(self, *, target_id: int, member_code: str, signal_day: date) -> str:
        return ":".join(
            [
                str(target_id),
                member_code,
                signal_day.isoformat(),
                self.SIGNAL_TYPE,
                self.STRATEGY_VERSION,
            ]
        )
