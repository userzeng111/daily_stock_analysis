#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the standalone SSE50 CSV export script."""

from pathlib import Path
import sys
import types

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from export_sse50_daily_csv import (
    DEFAULT_END_DATE,
    DEFAULT_INDEX_NAME,
    DEFAULT_START_DATE,
    DEFAULT_STOCK_CODE,
    DEFAULT_STOCK_NAME,
    _fetch_index_with_akshare,
    _fetch_stock_with_akshare,
    build_output_path,
    export_daily_csv,
)


class _FakeManager:
    def __init__(self, frame: pd.DataFrame, source: str = "FakeFetcher") -> None:
        self.frame = frame
        self.source = source
        self.calls = []

    def get_daily_data(self, stock_code: str, start_date: str, end_date: str, days: int = 30):
        self.calls.append(
            {
                "stock_code": stock_code,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
            }
        )
        return self.frame.copy(), self.source


def test_build_output_path_uses_default_naming(tmp_path):
    path = build_output_path(
        output_dir=tmp_path,
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        asset_name=DEFAULT_INDEX_NAME,
    )

    assert path == tmp_path / f"{DEFAULT_INDEX_NAME}_{DEFAULT_STOCK_CODE}_{DEFAULT_START_DATE}_to_{DEFAULT_END_DATE}.csv"


def test_export_daily_csv_with_manager_preserves_raw_columns(tmp_path):
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [2300.0, 2310.0],
            "high": [2320.0, 2330.0],
            "low": [2290.0, 2305.0],
            "close": [2315.0, 2328.0],
            "volume": [123456789, 135792468],
            "amount": [1.23e10, 1.35e10],
            "pct_chg": [0.65, 0.56],
            "ma5": [2315.0, 2321.5],
        }
    )
    manager = _FakeManager(frame)

    output_path, source, rows = export_daily_csv(
        start_date="2024-01-01",
        end_date="2024-01-31",
        output_dir=tmp_path,
        stock_code=DEFAULT_STOCK_CODE,
        asset_name=DEFAULT_INDEX_NAME,
        manager=manager,
    )

    assert manager.calls == [
        {
            "stock_code": DEFAULT_STOCK_CODE,
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "days": 30,
        }
    ]
    assert source == "FakeFetcher"
    assert rows == 2
    assert output_path.exists()

    exported = pd.read_csv(output_path)
    assert list(exported.columns) == list(frame.columns)
    assert exported.to_dict(orient="records") == [
        {
            "date": "2024-01-02",
            "open": 2300.0,
            "high": 2320.0,
            "low": 2290.0,
            "close": 2315.0,
            "volume": 123456789,
            "amount": 12300000000.0,
            "pct_chg": 0.65,
            "ma5": 2315.0,
        },
        {
            "date": "2024-01-03",
            "open": 2310.0,
            "high": 2330.0,
            "low": 2305.0,
            "close": 2328.0,
            "volume": 135792468,
            "amount": 13500000000.0,
            "pct_chg": 0.56,
            "ma5": 2321.5,
        },
    ]


def test_build_output_path_sanitizes_asset_name(tmp_path):
    path = build_output_path(
        output_dir=tmp_path,
        start_date="2024-01-01",
        end_date="2024-01-31",
        stock_code="600519",
        asset_name="贵州茅台 A股",
    )

    assert path == tmp_path / "guizhou_maotai_a_600519_2024-01-01_to_2024-01-31.csv"


def test_fetch_index_with_akshare_uses_sina_index_api(monkeypatch):
    calls = []

    def fake_stock_zh_index_daily(*, symbol):
        calls.append(("stock_zh_index_daily", symbol))
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "open": [2300.0, 2310.0],
                "high": [2320.0, 2330.0],
                "low": [2290.0, 2305.0],
                "close": [2315.0, 2328.0],
                "volume": [123456789, 135792468],
            }
        )

    monkeypatch.setitem(
        sys.modules,
        "akshare",
        types.SimpleNamespace(stock_zh_index_daily=fake_stock_zh_index_daily),
    )

    frame, source = _fetch_index_with_akshare(
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbol="sh000016",
    )

    assert calls == [("stock_zh_index_daily", "sh000016")]
    assert source == "AkShare(stock_zh_index_daily)"
    assert list(frame.columns) == ["date", "open", "high", "low", "close", "volume"]


def test_fetch_stock_with_akshare_uses_sina_a_stock_api(monkeypatch):
    calls = []

    def fake_stock_zh_a_daily(*, symbol, start_date, end_date, adjust):
        calls.append((symbol, start_date, end_date, adjust))
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "open": [1700.0, 1710.0],
                "high": [1720.0, 1730.0],
                "low": [1690.0, 1705.0],
                "close": [1715.0, 1728.0],
                "volume": [3215644.0, 2022929.0],
                "amount": [5440082548.0, 3411400667.0],
            }
        )

    monkeypatch.setitem(
        sys.modules,
        "akshare",
        types.SimpleNamespace(stock_zh_a_daily=fake_stock_zh_a_daily),
    )

    frame, source = _fetch_stock_with_akshare(
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbol="sh600519",
    )

    assert calls == [("sh600519", "20240101", "20240131", "")]
    assert source == "AkShare(stock_zh_a_daily)"
    assert list(frame.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
