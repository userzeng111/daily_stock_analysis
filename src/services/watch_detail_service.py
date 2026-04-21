# -*- coding: utf-8 -*-
"""On-demand watch target detail assembly."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import pandas as pd

from src.repositories.stock_repo import StockRepository
from src.repositories.watch_repo import WatchRepository
from src.stock_analyzer import StockTrendAnalyzer
from src.storage import DatabaseManager, WatchTarget, WatchTargetMember


class WatchDetailService:
    """Build one target detail payload for the `/watch` detail panel."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        stock_repo: Optional[StockRepository] = None,
        trend_analyzer: Optional[StockTrendAnalyzer] = None,
        history_loader: Optional[Callable[[str, int], pd.DataFrame]] = None,
        lookback_bars: int = 30,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.stock_repo = stock_repo or StockRepository(self.db)
        self.trend_analyzer = trend_analyzer or StockTrendAnalyzer()
        self.history_loader = history_loader
        self.lookback_bars = max(30, int(lookback_bars))

    def get_target_detail(
        self,
        target_id: int,
        *,
        window_days: int = 7,
        member_code: Optional[str] = None,
    ) -> Dict[str, object]:
        resolved_window = int(window_days)
        if resolved_window not in {7, 30}:
            raise ValueError("window_days must be 7 or 30")

        target = self.repo.get_target(target_id)
        if target is None:
            raise ValueError(f"watch target not found: {target_id}")

        members = self.repo.list_members(target.id)
        if not members:
            raise ValueError(f"watch target has no members: {target_id}")

        snapshot = self.repo.get_target_snapshot(target.id, summary_window_days=7)
        summary_payload = self._summary_payload(snapshot.payload if snapshot is not None else None)
        active_member = self._select_active_member(
            target=target,
            members=members,
            summary_payload=summary_payload,
            requested_member_code=member_code,
        )

        df = self._load_history(active_member.member_code)
        if df.empty:
            raise ValueError(f"no history for member: {active_member.member_code}")

        analysis_result = self.trend_analyzer.analyze(df.copy(), active_member.member_code)
        analysis = self._analysis_to_dict(analysis_result, df)
        kline_df = df.tail(resolved_window).reset_index(drop=True)

        return {
            "target": {
                **target.to_dict(),
                "member_count": len(members),
            },
            "summary": summary_payload,
            "member_options": [self._member_to_dict(member) for member in members],
            "active_member": self._member_to_dict(active_member),
            "kline": self._build_kline(kline_df),
            "indicators": self._build_indicators(analysis),
            "strategy_insights": self._build_strategy_insights(analysis),
            "latest_review": self._load_latest_review(target.id, active_member.member_code),
        }

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
        return normalized.tail(self.lookback_bars)

    @staticmethod
    def _member_to_dict(member: WatchTargetMember) -> Dict[str, object]:
        return {
            "id": member.id,
            "member_code": member.member_code,
            "member_name": member.member_name,
            "member_kind": member.member_kind,
        }

    @staticmethod
    def _summary_payload(payload: Optional[Dict[str, object]]) -> Dict[str, object]:
        if isinstance(payload, dict) and payload:
            merged = dict(payload)
            merged.setdefault("status", "ready")
            return merged
        return {
            "status": "pending",
            "summary_window_days": 7,
            "brief": "摘要生成中",
            "signal_score": None,
            "action": None,
        }

    def _select_active_member(
        self,
        *,
        target: WatchTarget,
        members: List[WatchTargetMember],
        summary_payload: Dict[str, object],
        requested_member_code: Optional[str],
    ) -> WatchTargetMember:
        if requested_member_code:
            for member in members:
                if member.member_code == requested_member_code:
                    return member

        representative_code = None
        if target.target_kind == "theme":
            representative = summary_payload.get("representative_member") if isinstance(summary_payload, dict) else None
            if isinstance(representative, dict):
                representative_code = representative.get("member_code")
            representative_code = representative_code or summary_payload.get("representative_member_code")
        if representative_code:
            for member in members:
                if member.member_code == representative_code:
                    return member

        return members[0]

    @staticmethod
    def _analysis_to_dict(analysis_result, df: pd.DataFrame) -> Dict[str, object]:
        analysis = analysis_result.to_dict()
        support_levels = [round(float(level), 4) for level in getattr(analysis_result, "support_levels", [])]
        resistance_levels = [round(float(level), 4) for level in getattr(analysis_result, "resistance_levels", [])]

        if not support_levels:
            support_levels = [
                round(float(level), 4)
                for level in (
                    getattr(analysis_result, "ma5", 0),
                    getattr(analysis_result, "ma10", 0),
                    getattr(analysis_result, "ma20", 0),
                )
                if float(level or 0) > 0
            ]
        if not resistance_levels and not df.empty:
            resistance_levels = [round(float(df["high"].max()), 4)]

        analysis["support_levels"] = support_levels
        analysis["resistance_levels"] = resistance_levels
        return analysis

    @staticmethod
    def _build_kline(df: pd.DataFrame) -> List[Dict[str, object]]:
        return [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            for _, row in df.iterrows()
        ]

    @staticmethod
    def _build_indicators(analysis: Dict[str, object]) -> Dict[str, object]:
        return {
            "trend_status": analysis.get("trend_status"),
            "signal_score": analysis.get("signal_score"),
            "buy_signal": analysis.get("buy_signal"),
            "ma5": analysis.get("ma5"),
            "ma10": analysis.get("ma10"),
            "ma20": analysis.get("ma20"),
            "macd_status": analysis.get("macd_status"),
            "rsi_status": analysis.get("rsi_status"),
            "volume_status": analysis.get("volume_status"),
            "support_levels": analysis.get("support_levels", []),
            "resistance_levels": analysis.get("resistance_levels", []),
        }

    @staticmethod
    def _build_strategy_insights(analysis: Dict[str, object]) -> Dict[str, object]:
        return {
            "signal_reasons": analysis.get("signal_reasons", []),
            "risk_factors": analysis.get("risk_factors", []),
            "action": analysis.get("buy_signal"),
        }

    def _load_latest_review(self, target_id: int, member_code: str):
        latest_event = self.repo.get_latest_signal_event_for_member(
            target_id=target_id,
            member_code=member_code,
        )
        if latest_event is None:
            return None
        review = self.repo.get_latest_review(latest_event.id)
        return review.to_dict() if review is not None else None
