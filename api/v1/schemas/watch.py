# -*- coding: utf-8 -*-
"""Watch API schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WatchTargetCreateRequest(BaseModel):
    input_text: str
    target_kind: Optional[str] = None
    display_name: Optional[str] = None
    source: str = "manual"
    notes: Optional[str] = None


class WatchTargetUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class WatchTargetSummary(BaseModel):
    status: str
    summary_window_days: int = 7
    signal_score: Optional[float] = None
    action: Optional[str] = None
    brief: Optional[str] = None
    trend_status: Optional[str] = None
    buy_signal: Optional[str] = None
    period_return_pct: Optional[float] = None
    updated_at: Optional[str] = None
    representative_member_code: Optional[str] = None
    representative_member_name: Optional[str] = None
    member_count: Optional[int] = None
    error: Optional[str] = None


class WatchMemberOption(BaseModel):
    id: int
    member_code: str
    member_name: str
    member_kind: str


class WatchTargetItem(BaseModel):
    id: int
    target_kind: str
    target_key: str
    display_name: str
    status: str
    theme_id: Optional[str] = None
    theme_name: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    member_count: int = 0
    summary: Optional[WatchTargetSummary] = None


class WatchTargetListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[WatchTargetItem] = Field(default_factory=list)


class WatchReviewSummary(BaseModel):
    id: int
    signal_event_id: int
    review_round: int
    decision: str
    confidence: Optional[float] = None
    summary: Optional[str] = None
    payload: Optional[Dict[str, Any] | str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WatchSignalEventItem(BaseModel):
    id: int
    target_id: int
    member_id: Optional[int] = None
    member_code: str
    member_name: Optional[str] = None
    signal_date: Optional[str] = None
    signal_type: str
    signal_score: Optional[float] = None
    status: str
    dedupe_key: str
    payload: Optional[Dict[str, Any] | str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    latest_review_summary: Optional[WatchReviewSummary] = None


class WatchSignalEventDetail(WatchSignalEventItem):
    latest_review: Optional[WatchReviewSummary] = None


class WatchSignalEventListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[WatchSignalEventItem] = Field(default_factory=list)


class WatchRuntimeStatusResponse(BaseModel):
    enabled: bool
    registered: bool
    last_scan_at: Optional[str] = None
    last_error: Optional[str] = None
    scan_interval_minutes: int


class WatchRuntimeScanResult(BaseModel):
    target_id: Optional[int] = None
    processed_targets: int
    emitted_events: int
    last_scan_at: Optional[str] = None
    last_error: Optional[str] = None


class WatchRuntimeScanResponse(BaseModel):
    target_id: Optional[int] = None
    processed_targets: int
    emitted_events: int
    last_scan_at: Optional[str] = None
    last_error: Optional[str] = None
    runtime: WatchRuntimeStatusResponse
    scan: WatchRuntimeScanResult


class WatchTargetDetailResponse(BaseModel):
    target: WatchTargetItem
    summary: WatchTargetSummary
    member_options: List[WatchMemberOption] = Field(default_factory=list)
    active_member: WatchMemberOption
    kline: List[Dict[str, Any]] = Field(default_factory=list)
    chart_type: Optional[str] = None
    indicators: Dict[str, Any] = Field(default_factory=dict)
    strategy_insights: Dict[str, Any] = Field(default_factory=dict)
    overlays: Dict[str, List[Optional[float]]] = Field(default_factory=dict)
    sub_indicators: Dict[str, Any] = Field(default_factory=dict)
    subIndicators: Dict[str, Any] = Field(default_factory=dict)
    quote_snapshot: Dict[str, Any] = Field(default_factory=dict)
    quoteSnapshot: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    latest_review: Optional[WatchReviewSummary] = None
