#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export standalone daily market data CSV files for simple day-level analysis."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DEFAULT_STOCK_CODE = "000016"
DEFAULT_INDEX_NAME = "sse50"
DEFAULT_STOCK_NAME = "guizhou_maotai"
DEFAULT_START_DATE = "2024-01-01"
DEFAULT_END_DATE = date.today().isoformat()
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "test_exports"
PROFILE_CONFIG = {
    "sse50": {
        "stock_code": "000016",
        "asset_name": DEFAULT_INDEX_NAME,
        "kind": "index",
        "symbol": "sh000016",
    },
    "maotai": {
        "stock_code": "600519",
        "asset_name": DEFAULT_STOCK_NAME,
        "kind": "stock",
        "symbol": "sh600519",
    },
}


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="导出日线市场数据到 CSV（独立测试脚本）"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_CONFIG.keys()),
        default="sse50",
        help="导出预设对象：sse50 或 maotai，默认 sse50",
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help=f"开始日期，格式 YYYY-MM-DD，默认 {DEFAULT_START_DATE}",
    )
    parser.add_argument(
        "--end-date",
        default=DEFAULT_END_DATE,
        help=f"结束日期，格式 YYYY-MM-DD，默认 {DEFAULT_END_DATE}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"输出目录，默认 {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="可选：指定完整输出文件路径，优先级高于 output-dir",
    )
    return parser.parse_args(argv)


def slugify_asset_name(asset_name: str) -> str:
    text = (asset_name or "").strip()
    replacements = (
        ("贵州茅台", "guizhou_maotai"),
        ("上证50", "sse50"),
        ("A股", "a"),
        ("指数", "index"),
    )
    for source_text, replacement in replacements:
        text = text.replace(source_text, replacement)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "asset"


def build_output_path(
    output_dir: Path,
    start_date: str,
    end_date: str,
    stock_code: str = DEFAULT_STOCK_CODE,
    asset_name: str = DEFAULT_INDEX_NAME,
) -> Path:
    asset_slug = slugify_asset_name(asset_name)
    return output_dir / f"{asset_slug}_{stock_code}_{start_date}_to_{end_date}.csv"


def _validate_date(date_text: str) -> str:
    return date.fromisoformat(date_text).isoformat()


def _prepare_export_frame(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()

    if "date" not in export_df.columns:
        raise ValueError("导出失败：数据中缺少 date 列")

    export_df["date"] = pd.to_datetime(export_df["date"]).dt.strftime("%Y-%m-%d")
    return export_df


def _filter_date_range(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    filtered = df.copy()
    filtered["date"] = pd.to_datetime(filtered["date"])
    filtered = filtered.loc[
        (filtered["date"] >= pd.Timestamp(start_date))
        & (filtered["date"] <= pd.Timestamp(end_date))
    ].copy()
    if filtered.empty:
        raise ValueError(f"指定区间内未获取到数据: {start_date} ~ {end_date}")
    return filtered


def _fetch_index_with_akshare(start_date: str, end_date: str, symbol: str) -> tuple[pd.DataFrame, str]:
    import akshare as ak

    raw_df = ak.stock_zh_index_daily(symbol=symbol)
    if raw_df is None or raw_df.empty:
        raise ValueError(f"AkShare 未返回指数历史数据: {symbol}")

    filtered = _filter_date_range(raw_df, start_date, end_date)
    return filtered, "AkShare(stock_zh_index_daily)"


def _fetch_stock_with_akshare(start_date: str, end_date: str, symbol: str) -> tuple[pd.DataFrame, str]:
    import akshare as ak

    raw_df = ak.stock_zh_a_daily(
        symbol=symbol,
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust="",
    )
    if raw_df is None or raw_df.empty:
        raise ValueError(f"AkShare 未返回个股历史数据: {symbol}")

    filtered = _filter_date_range(raw_df, start_date, end_date)
    return filtered, "AkShare(stock_zh_a_daily)"


def export_daily_csv(
    *,
    start_date: str,
    end_date: str,
    output_dir: Optional[Path] = None,
    output_file: Optional[Path] = None,
    stock_code: str = DEFAULT_STOCK_CODE,
    asset_name: str = DEFAULT_INDEX_NAME,
    profile: str = "sse50",
    manager: Optional[Any] = None,
) -> tuple[Path, str, int]:
    normalized_start = _validate_date(start_date)
    normalized_end = _validate_date(end_date)
    if normalized_start > normalized_end:
        raise ValueError("开始日期不能晚于结束日期")

    if manager is None:
        selected = PROFILE_CONFIG[profile]
        stock_code = selected["stock_code"]
        asset_name = selected["asset_name"]
        if selected["kind"] == "index":
            df, source = _fetch_index_with_akshare(
                start_date=normalized_start,
                end_date=normalized_end,
                symbol=selected["symbol"],
            )
        else:
            df, source = _fetch_stock_with_akshare(
                start_date=normalized_start,
                end_date=normalized_end,
                symbol=selected["symbol"],
            )
    else:
        df, source = manager.get_daily_data(
            stock_code,
            start_date=normalized_start,
            end_date=normalized_end,
        )
    export_df = _prepare_export_frame(df)

    target_path = (
        Path(output_file)
        if output_file is not None
        else build_output_path(
            output_dir=output_dir or DEFAULT_OUTPUT_DIR,
            start_date=normalized_start,
            end_date=normalized_end,
            stock_code=stock_code,
            asset_name=asset_name,
        )
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(target_path, index=False, encoding="utf-8-sig")
    return target_path, source, len(export_df)


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv()
    args = parse_args(argv)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_file = (
        Path(args.output_file).expanduser().resolve()
        if args.output_file
        else None
    )

    output_path, source, rows = export_daily_csv(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=output_dir,
        output_file=output_file,
        profile=args.profile,
    )

    print(f"导出完成: {output_path}")
    print(f"数据源: {source}")
    print(f"记录数: {rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
