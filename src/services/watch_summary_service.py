# -*- coding: utf-8 -*-
"""Watch target summary snapshot generation."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.repositories.stock_repo import StockRepository
from src.repositories.watch_repo import WatchRepository
from src.stock_analyzer import StockTrendAnalyzer
from src.storage import DatabaseManager, WatchTarget, WatchTargetMember


class WatchSummaryService:
    """Build and persist watch target summary snapshots."""

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

    def refresh_target_snapshot(self, target_id: int, summary_window_days: int = 7) -> Dict[str, object]:
        target = self.repo.get_target(target_id)
        if target is None:
            raise ValueError(f"watch target not found: {target_id}")

        try:
            payload = self._build_snapshot_payload(target, summary_window_days=int(summary_window_days))
            self.repo.upsert_target_snapshot(
                target_id=target.id,
                summary_window_days=int(summary_window_days),
                status="ready",
                payload=payload,
            )
            return payload
        except Exception as exc:
            payload = {
                "target_id": target.id,
                "target_kind": target.target_kind,
                "target_key": target.target_key,
                "display_name": target.display_name,
                "summary_window_days": int(summary_window_days),
                "status": "failed",
                "error": str(exc),
                "brief": f"summary_failed: {exc}",
            }
            self.repo.upsert_target_snapshot(
                target_id=target.id,
                summary_window_days=int(summary_window_days),
                status="failed",
                payload=payload,
            )
            return payload

    def _build_snapshot_payload(self, target: WatchTarget, summary_window_days: int) -> Dict[str, object]:
        members = self.repo.list_members(target.id)
        if not members:
            raise ValueError("target has no members")

        updated_at = datetime.now().isoformat()
        member_summaries: List[Dict[str, object]] = []
        for member in members:
            member_summaries.append(self._build_member_summary(member, summary_window_days=summary_window_days))

        if target.target_kind == "theme":
            representative = max(
                member_summaries,
                key=lambda item: (
                    float(item["analysis"].get("signal_score") or 0.0),
                    float(item["metrics"].get("return_pct") or 0.0),
                ),
            )
            avg_return_pct = sum(
                float(item["metrics"].get("return_pct") or 0.0) for item in member_summaries
            ) / max(1, len(member_summaries))
            avg_signal_score = sum(
                float(item["analysis"].get("signal_score") or 0.0) for item in member_summaries
            ) / max(1, len(member_summaries))
            brief = (
                f"{summary_window_days}日主题概览：{target.display_name} 代表标的 "
                f"{representative['member']['member_name']}，均值涨跌 {avg_return_pct:.2f}%"
            )
            return {
                "target_id": target.id,
                "target_kind": target.target_kind,
                "target_key": target.target_key,
                "display_name": target.display_name,
                "summary_window_days": int(summary_window_days),
                "status": "ready",
                "brief": brief,
                "signal_score": representative["analysis"].get("signal_score"),
                "action": representative["analysis"].get("buy_signal"),
                "trend_status": representative["analysis"].get("trend_status"),
                "buy_signal": representative["analysis"].get("buy_signal"),
                "period_return_pct": round(avg_return_pct, 4),
                "updated_at": updated_at,
                "representative_member_code": representative["member"]["member_code"],
                "representative_member_name": representative["member"]["member_name"],
                "member_count": len(member_summaries),
                "aggregate": {
                    "member_count": len(member_summaries),
                    "ready_member_count": len(member_summaries),
                    "avg_return_pct": round(avg_return_pct, 4),
                    "avg_signal_score": round(avg_signal_score, 2),
                },
                "representative_member": representative["member"],
                "members": member_summaries,
            }

        member_summary = member_summaries[0]
        analysis = member_summary["analysis"]
        metrics = member_summary["metrics"]
        brief = (
            f"{summary_window_days}日概览：{target.display_name} "
            f"{analysis.get('buy_signal') or '观望'}，区间涨跌 {float(metrics.get('return_pct') or 0.0):.2f}%"
        )
        return {
            "target_id": target.id,
            "target_kind": target.target_kind,
            "target_key": target.target_key,
            "display_name": target.display_name,
            "summary_window_days": int(summary_window_days),
            "status": "ready",
            "brief": brief,
            "signal_score": analysis.get("signal_score"),
            "action": analysis.get("buy_signal"),
            "trend_status": analysis.get("trend_status"),
            "buy_signal": analysis.get("buy_signal"),
            "period_return_pct": metrics.get("return_pct"),
            "updated_at": updated_at,
            "member_count": 1,
            "member": member_summary["member"],
            "analysis": analysis,
            "metrics": metrics,
        }

    def _build_member_summary(self, member: WatchTargetMember, *, summary_window_days: int) -> Dict[str, object]:
        df = self._load_history(member.member_code)
        if df.empty or len(df) < self.lookback_bars:
            raise ValueError(f"insufficient history for {member.member_code}")

        analysis_result = self.trend_analyzer.analyze(df.copy(), member.member_code)
        analysis = analysis_result.to_dict()

        summary_df = df.tail(int(summary_window_days)).reset_index(drop=True)
        start_close = float(summary_df.iloc[0]["close"])
        end_close = float(summary_df.iloc[-1]["close"])
        high_price = float(summary_df["high"].max())
        low_price = float(summary_df["low"].min())
        return_pct = 0.0 if start_close == 0 else ((end_close - start_close) / start_close) * 100

        return {
            "member": {
                "member_code": member.member_code,
                "member_name": member.member_name,
                "member_kind": member.member_kind,
            },
            "analysis": analysis,
            "metrics": {
                "bar_count": int(len(df)),
                "summary_bar_count": int(len(summary_df)),
                "start_close": round(start_close, 4),
                "end_close": round(end_close, 4),
                "return_pct": round(return_pct, 4),
                "high_price": round(high_price, 4),
                "low_price": round(low_price, 4),
            },
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
