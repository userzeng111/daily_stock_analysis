# -*- coding: utf-8 -*-
"""On-demand watch target detail assembly."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.repositories.stock_repo import StockRepository
from src.repositories.watch_repo import WatchRepository
from src.stock_analyzer import StockTrendAnalyzer
from src.storage import DatabaseManager, WatchTarget, WatchTargetMember


class WatchDetailService:
    """Build one target detail payload for the `/watch` detail panel."""

    VALID_TIMEFRAMES = {"intraday", "day", "week", "month"}
    VALID_WINDOWS = {"7", "30", "60", "120", "250", "ytd"}

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        repo: Optional[WatchRepository] = None,
        stock_repo: Optional[StockRepository] = None,
        trend_analyzer: Optional[StockTrendAnalyzer] = None,
        history_loader: Optional[Callable[[str, int], pd.DataFrame]] = None,
        quote_loader: Optional[Callable[[str], object]] = None,
        lookback_bars: int = 30,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = repo or WatchRepository(self.db)
        self.stock_repo = stock_repo or StockRepository(self.db)
        self.trend_analyzer = trend_analyzer or StockTrendAnalyzer()
        self.history_loader = history_loader
        self.quote_loader = quote_loader
        self.lookback_bars = max(30, int(lookback_bars))

    def get_target_detail(
        self,
        target_id: int,
        *,
        timeframe: str = "day",
        window: str | int | None = None,
        window_days: int = 7,
        member_code: Optional[str] = None,
    ) -> Dict[str, object]:
        resolved_timeframe = self._normalize_timeframe(timeframe)
        resolved_window = self._normalize_window(window, legacy_window_days=window_days)

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

        df = self._load_history(
            active_member.member_code,
            required_bars=self._required_history_bars(resolved_timeframe, resolved_window),
        )
        if df.empty:
            raise ValueError(f"no history for member: {active_member.member_code}")

        quote = self._load_quote(active_member.member_code)
        analysis_df = self._build_analysis_frame(df, quote)
        analysis_result = self.trend_analyzer.analyze(analysis_df.copy(), active_member.member_code)
        analysis = self._analysis_to_dict(analysis_result, df)
        kline_df = self._build_display_frame(
            df=analysis_df,
            timeframe=resolved_timeframe,
            window=resolved_window,
            quote=quote,
        )
        overlays = self._build_overlays(kline_df)
        sub_indicators = self._build_sub_indicators(kline_df)
        meta = self._build_meta(
            timeframe=resolved_timeframe,
            window=resolved_window,
            bar_count=len(kline_df),
        )

        return {
            "target": {
                **target.to_dict(),
                "member_count": len(members),
            },
            "summary": summary_payload,
            "member_options": [self._member_to_dict(member) for member in members],
            "active_member": self._member_to_dict(active_member),
            "kline": self._build_kline(kline_df),
            "chart_type": "line" if resolved_timeframe == "intraday" else "candlestick",
            "indicators": self._build_indicators(analysis),
            "strategy_insights": self._build_strategy_insights(analysis),
            "overlays": overlays,
            "sub_indicators": self._build_sub_indicators_legacy(kline_df, sub_indicators),
            "subIndicators": sub_indicators,
            "quote_snapshot": self._build_quote_snapshot(df, kline_df, quote),
            "quoteSnapshot": self._build_quote_snapshot(df, kline_df, quote),
            "meta": meta,
            "latest_review": self._load_latest_review(target.id, active_member.member_code),
        }

    def _load_history(self, code: str, *, required_bars: Optional[int] = None) -> pd.DataFrame:
        lookback = max(self.lookback_bars, int(required_bars or self.lookback_bars))
        if self.history_loader is not None:
            raw = self.history_loader(code, lookback)
            df = raw.copy() if isinstance(raw, pd.DataFrame) else pd.DataFrame()
        else:
            rows = self.stock_repo.get_latest(code, days=max(lookback, 40))
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
        return normalized.tail(lookback).reset_index(drop=True)

    def _load_quote(self, code: str):
        if self.quote_loader is None:
            return None
        try:
            return self.quote_loader(code)
        except Exception:
            return None

    def _normalize_timeframe(self, timeframe: Optional[str]) -> str:
        resolved = str(timeframe or "day").strip().lower()
        if resolved not in self.VALID_TIMEFRAMES:
            raise ValueError("timeframe must be intraday, day, week, or month")
        return resolved

    def _normalize_window(self, window: str | int | None, *, legacy_window_days: Optional[int]) -> str:
        raw_window = str(window).strip().lower() if window is not None else ""
        if raw_window in self.VALID_WINDOWS:
            return raw_window

        if raw_window == "" and legacy_window_days is None:
            return "30"

        if raw_window in {"", "7"} and legacy_window_days is not None:
            legacy = str(int(legacy_window_days))
            if legacy in self.VALID_WINDOWS:
                return legacy

        raise ValueError("window must be one of 7, 30, 60, 120, 250, ytd")

    @staticmethod
    def _required_history_bars(timeframe: str, window: str) -> int:
        if window == "ytd":
            return 320
        bars = int(window)
        if timeframe == "day":
            return max(60, bars + 30)
        if timeframe == "week":
            return max(120, bars * 5)
        if timeframe == "month":
            return max(250, bars * 22)
        return max(30, bars)

    def _build_analysis_frame(self, df: pd.DataFrame, quote) -> pd.DataFrame:
        if quote is None or df.empty:
            return df

        augmented = df.copy()
        latest_close = float(augmented.iloc[-1]["close"])
        current_date = datetime.now().date()
        if augmented.iloc[-1]["date"] == current_date:
            augmented.loc[augmented.index[-1], "close"] = float(getattr(quote, "price", latest_close) or latest_close)
            augmented.loc[augmented.index[-1], "high"] = float(getattr(quote, "high", latest_close) or latest_close)
            augmented.loc[augmented.index[-1], "low"] = float(getattr(quote, "low", latest_close) or latest_close)
            augmented.loc[augmented.index[-1], "open"] = float(getattr(quote, "open_price", latest_close) or latest_close)
            augmented.loc[augmented.index[-1], "volume"] = float(getattr(quote, "volume", 0) or 0)
            return augmented

        pre_close = float(getattr(quote, "pre_close", latest_close) or latest_close)
        close_price = float(getattr(quote, "price", pre_close) or pre_close)
        augmented = pd.concat(
            [
                augmented,
                pd.DataFrame(
                    [
                        {
                            "date": current_date,
                            "open": float(getattr(quote, "open_price", pre_close) or pre_close),
                            "high": float(getattr(quote, "high", close_price) or close_price),
                            "low": float(getattr(quote, "low", close_price) or close_price),
                            "close": close_price,
                            "volume": float(getattr(quote, "volume", 0) or 0),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        return augmented

    def _build_display_frame(
        self,
        *,
        df: pd.DataFrame,
        timeframe: str,
        window: str,
        quote,
    ) -> pd.DataFrame:
        if timeframe == "intraday":
            intraday_df = self._build_intraday_frame(df, quote)
            return intraday_df.reset_index(drop=True)

        base_df = df.copy()
        base_df["date"] = pd.to_datetime(base_df["date"])
        filtered = self._apply_window(base_df, window)
        if timeframe == "day":
            result = filtered.reset_index(drop=True)
            result["date"] = pd.to_datetime(result["date"]).dt.date
            return result
        return self._aggregate_frame(filtered, timeframe=timeframe).reset_index(drop=True)

    @staticmethod
    def _apply_window(df: pd.DataFrame, window: str) -> pd.DataFrame:
        if df.empty:
            return df
        if window == "ytd":
            current_year = int(df["date"].max().year)
            filtered = df[df["date"].dt.year == current_year]
            if not filtered.empty:
                return filtered
            return df
        return df.tail(int(window))

    @staticmethod
    def _aggregate_frame(df: pd.DataFrame, *, timeframe: str) -> pd.DataFrame:
        if df.empty:
            return df

        freq = "W-FRI" if timeframe == "week" else "ME"
        frame = df.copy()
        aggregated = (
            frame.set_index("date")
            .resample(freq)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna(subset=["open", "high", "low", "close"], how="any")
            .reset_index()
        )
        aggregated["date"] = aggregated["date"].dt.date
        return aggregated

    def _build_intraday_frame(self, df: pd.DataFrame, quote) -> pd.DataFrame:
        if quote is not None:
            pre_close = float(getattr(quote, "pre_close", None) or (df.iloc[-1]["close"] if not df.empty else 0) or 0)
            close_price = float(getattr(quote, "price", pre_close) or pre_close)
            return pd.DataFrame(
                [
                    {
                        "date": datetime.now().isoformat(timespec="seconds"),
                        "open": float(getattr(quote, "open_price", pre_close) or pre_close),
                        "high": float(getattr(quote, "high", close_price) or close_price),
                        "low": float(getattr(quote, "low", close_price) or close_price),
                        "close": close_price,
                        "volume": float(getattr(quote, "volume", 0) or 0),
                    }
                ]
            )
        return df.tail(1).reset_index(drop=True)

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

    def _build_overlays(self, df: pd.DataFrame) -> Dict[str, List[Optional[float]]]:
        series = self._numeric_series(df, "close")
        return {
            "ma5": self._to_float_list(series.rolling(5).mean()),
            "ma10": self._to_float_list(series.rolling(10).mean()),
            "ma20": self._to_float_list(series.rolling(20).mean()),
        }

    def _build_sub_indicators(self, df: pd.DataFrame) -> Dict[str, object]:
        close = self._numeric_series(df, "close")
        volume = self._numeric_series(df, "volume")
        dif = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        dea = dif.ewm(span=9, adjust=False).mean()
        bar = dif - dea

        delta = close.diff()
        gains = delta.clip(lower=0)
        losses = (-delta).clip(lower=0)

        def compute_rsi(period: int) -> pd.Series:
            avg_gain = gains.rolling(period).mean()
            avg_loss = losses.rolling(period).mean()
            rs = avg_gain / avg_loss.replace(0, float("nan"))
            rsi = 100 - (100 / (1 + rs))
            bullish_mask = (avg_loss == 0) & (avg_gain > 0)
            flat_mask = (avg_loss == 0) & (avg_gain == 0)
            rsi = rsi.mask(bullish_mask, 100.0)
            rsi = rsi.mask(flat_mask, 50.0)
            return rsi.fillna(0.0)

        return {
            "volMa": self._to_float_list(volume.rolling(5).mean()),
            "macd": {
                "dif": self._to_float_list(dif),
                "dea": self._to_float_list(dea),
                "bar": self._to_float_list(bar),
            },
            "rsi": {
                "rsi6": self._to_float_list(compute_rsi(6)),
                "rsi12": self._to_float_list(compute_rsi(12)),
                "rsi24": self._to_float_list(compute_rsi(24)),
            },
        }

    def _build_sub_indicators_legacy(self, df: pd.DataFrame, modern: Dict[str, object]) -> Dict[str, object]:
        return {
            "volume": {
                "bars": self._to_float_list(self._numeric_series(df, "volume")),
                "ma": list(modern.get("volMa", [])),
            },
            "macd": modern.get("macd", {}),
            "rsi": modern.get("rsi", {}),
        }

    def _build_quote_snapshot(self, raw_df: pd.DataFrame, display_df: pd.DataFrame, quote) -> Dict[str, Optional[float]]:
        reference_df = display_df if not display_df.empty else raw_df
        prev_close = None
        if quote is not None:
            prev_close = getattr(quote, "pre_close", None)
        if prev_close is None and len(raw_df) >= 2:
            prev_close = raw_df.iloc[-2]["close"]
        elif prev_close is None and not raw_df.empty:
            prev_close = raw_df.iloc[-1]["close"]

        current_close = None
        high_price = None
        low_price = None
        if quote is not None:
            current_close = getattr(quote, "price", None)
            high_price = getattr(quote, "high", None)
            low_price = getattr(quote, "low", None)
        if current_close is None and not reference_df.empty:
            current_close = reference_df.iloc[-1]["close"]
        if high_price is None and not reference_df.empty:
            high_price = reference_df.iloc[-1]["high"]
        if low_price is None and not reference_df.empty:
            low_price = reference_df.iloc[-1]["low"]

        change_amount = getattr(quote, "change_amount", None) if quote is not None else None
        if change_amount is None and current_close is not None and prev_close not in (None, 0):
            change_amount = float(current_close) - float(prev_close)

        change_pct = getattr(quote, "change_pct", None) if quote is not None else None
        if change_pct is None and change_amount is not None and prev_close not in (None, 0):
            change_pct = float(change_amount) / float(prev_close) * 100

        amplitude = getattr(quote, "amplitude", None) if quote is not None else None
        if amplitude is None and prev_close not in (None, 0) and high_price is not None and low_price is not None:
            amplitude = (float(high_price) - float(low_price)) / float(prev_close) * 100

        return {
            "prevClose": self._safe_float(prev_close),
            "changeAmount": self._safe_float(change_amount),
            "changePct": self._safe_float(change_pct),
            "amplitude": self._safe_float(amplitude),
        }

    @staticmethod
    def _build_meta(*, timeframe: str, window: str, bar_count: int) -> Dict[str, object]:
        return {
            "timeframe": timeframe,
            "window": window,
            "barCount": int(bar_count),
            "updatedAt": datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def _pad_frame(df: pd.DataFrame, *, window: str) -> pd.DataFrame:
        if df.empty or window == "ytd":
            return df

        target_len = int(window)
        if len(df) >= target_len or "date" not in df.columns:
            return df.tail(target_len)

        first = df.iloc[0]
        first_date = pd.to_datetime(first["date"])
        missing = target_len - len(df)
        pad_rows = []
        for index in range(missing, 0, -1):
            row = first.copy()
            row["date"] = first_date - pd.Timedelta(days=index)
            pad_rows.append(row.to_dict())
        padded = pd.concat([pd.DataFrame(pad_rows), df], ignore_index=True)
        return padded.tail(target_len)

    @staticmethod
    def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
        if column not in df.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(df[column], errors="coerce").astype(float)

    @staticmethod
    def _to_float_list(series: pd.Series) -> List[Optional[float]]:
        values: List[Optional[float]] = []
        for value in series.tolist():
            if pd.isna(value):
                values.append(None)
            else:
                values.append(round(float(value), 4))
        return values

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        return round(float(value), 4)

    def _load_latest_review(self, target_id: int, member_code: str):
        latest_event = self.repo.get_latest_signal_event_for_member(
            target_id=target_id,
            member_code=member_code,
        )
        if latest_event is None:
            return None
        review = self.repo.get_latest_review(latest_event.id)
        return review.to_dict() if review is not None else None
