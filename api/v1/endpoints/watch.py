# -*- coding: utf-8 -*-
"""Watch endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.deps import (
    get_watch_detail_service,
    get_watch_event_bus,
    get_watch_runtime_service,
    get_watchlist_service,
)
from api.v1.schemas.common import ErrorResponse, SuccessResponse
from api.v1.schemas.watch import (
    WatchRuntimeStatusResponse,
    WatchTargetDetailResponse,
    WatchSignalEventDetail,
    WatchSignalEventItem,
    WatchSignalEventListResponse,
    WatchTargetSummary,
    WatchMemberOption,
    WatchReviewSummary,
    WatchTargetCreateRequest,
    WatchTargetItem,
    WatchTargetListResponse,
    WatchTargetUpdateRequest,
)
from src.repositories.watch_repo import WatchRepository
from src.services.watch_event_bus import WatchEventBus
from src.services.watch_detail_service import WatchDetailService
from src.services.watch_runtime_service import WatchRuntimeService
from src.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)

router = APIRouter()


def _target_to_item(repo: WatchRepository, row) -> WatchTargetItem:
    summary = None
    if isinstance(row, dict):
        summary_payload = row.get("summary")
        if isinstance(summary_payload, dict):
            summary = WatchTargetSummary(**summary_payload)
        payload = {key: value for key, value in row.items() if key != "summary"}
        return WatchTargetItem(
            **payload,
            summary=summary,
        )

    return WatchTargetItem(
        **row.to_dict(),
        member_count=len(repo.list_members(row.id)),
    )


def _review_to_summary(review) -> Optional[WatchReviewSummary]:
    if review is None:
        return None
    if isinstance(review, dict):
        return WatchReviewSummary(**review)
    return WatchReviewSummary(**review.to_dict())


def _event_to_item(repo: WatchRepository, row) -> WatchSignalEventItem:
    return WatchSignalEventItem(
        **row.to_dict(),
        latest_review_summary=_review_to_summary(repo.get_latest_review(row.id)),
    )


@router.post(
    "/targets",
    response_model=WatchTargetItem,
    responses={500: {"description": "服务器错误", "model": ErrorResponse}},
)
def create_watch_target(
    request: WatchTargetCreateRequest,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchTargetItem:
    target = service.create_target(
        request.input_text,
        target_kind=request.target_kind,
        display_name=request.display_name,
        source=request.source,
        notes=request.notes,
    )
    return _target_to_item(service.repo, target)


@router.get(
    "/targets",
    response_model=WatchTargetListResponse,
    responses={500: {"description": "服务器错误", "model": ErrorResponse}},
)
def list_watch_targets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    target_kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchTargetListResponse:
    rows, total = service.list_targets(page=page, limit=limit, target_kind=target_kind, status=status)
    items = [_target_to_item(service.repo, row) for row in rows]
    if query:
        needle = query.strip().lower()
        items = [
            item for item in items
            if needle in item.display_name.lower()
            or needle in item.target_key.lower()
            or (item.theme_name or "").lower().find(needle) >= 0
        ]
        total = len(items)
    return WatchTargetListResponse(total=total, page=page, limit=limit, items=items)


@router.get(
    "/targets/{target_id}",
    response_model=WatchTargetItem,
    responses={404: {"description": "未找到", "model": ErrorResponse}},
)
def get_watch_target(
    target_id: int,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchTargetItem:
    target = service.repo.get_target(target_id)
    if target is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "watch target not found"})
    return _target_to_item(service.repo, target)


@router.get(
    "/targets/{target_id}/detail",
    response_model=WatchTargetDetailResponse,
    responses={404: {"description": "未找到", "model": ErrorResponse}},
)
def get_watch_target_detail(
    target_id: int,
    window: int = Query(7, ge=7, le=30),
    member_code: Optional[str] = Query(None),
    detail_service: WatchDetailService = Depends(get_watch_detail_service),
) -> WatchTargetDetailResponse:
    if window not in {7, 30}:
        raise HTTPException(
            status_code=422,
            detail={"error": "validation_error", "message": "window must be 7 or 30"},
        )
    try:
        detail = detail_service.get_target_detail(target_id, window_days=window, member_code=member_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": str(exc)})

    target = WatchTargetItem(**detail["target"], summary=WatchTargetSummary(**detail["summary"]))
    summary = WatchTargetSummary(**detail["summary"])
    member_options = [WatchMemberOption(**item) for item in detail["member_options"]]
    active_member = WatchMemberOption(**detail["active_member"])
    latest_review = _review_to_summary(detail["latest_review"]) if detail["latest_review"] else None
    return WatchTargetDetailResponse(
        target=target,
        summary=summary,
        member_options=member_options,
        active_member=active_member,
        kline=detail["kline"],
        indicators=detail["indicators"],
        strategy_insights=detail["strategy_insights"],
        latest_review=latest_review,
    )


@router.patch(
    "/targets/{target_id}",
    response_model=WatchTargetItem,
    responses={404: {"description": "未找到", "model": ErrorResponse}},
)
def update_watch_target(
    target_id: int,
    request: WatchTargetUpdateRequest,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchTargetItem:
    fields = request.model_dump(exclude_none=True)
    target = service.repo.update_target(target_id, fields)
    if target is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "watch target not found"})
    return _target_to_item(service.repo, target)


@router.delete(
    "/targets/{target_id}",
    response_model=SuccessResponse,
    responses={404: {"description": "未找到", "model": ErrorResponse}},
)
def delete_watch_target(
    target_id: int,
    service: WatchlistService = Depends(get_watchlist_service),
) -> SuccessResponse:
    deleted = service.repo.delete_target(target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "watch target not found"})
    return SuccessResponse(success=True, message="deleted", data={"target_id": target_id})


@router.get("/runtime/status", response_model=WatchRuntimeStatusResponse)
def get_watch_runtime_status(
    runtime: WatchRuntimeService = Depends(get_watch_runtime_service),
) -> WatchRuntimeStatusResponse:
    return WatchRuntimeStatusResponse(**runtime.status())


@router.post("/runtime/start", response_model=WatchRuntimeStatusResponse)
def start_watch_runtime(
    runtime: WatchRuntimeService = Depends(get_watch_runtime_service),
) -> WatchRuntimeStatusResponse:
    return WatchRuntimeStatusResponse(**runtime.start())


@router.post("/runtime/stop", response_model=WatchRuntimeStatusResponse)
def stop_watch_runtime(
    runtime: WatchRuntimeService = Depends(get_watch_runtime_service),
) -> WatchRuntimeStatusResponse:
    return WatchRuntimeStatusResponse(**runtime.stop())


@router.get("/events", response_model=WatchSignalEventListResponse)
def list_watch_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    target_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchSignalEventListResponse:
    rows, total = service.repo.list_signal_events(
        page=page,
        limit=limit,
        target_id=target_id,
        status=status,
        signal_type=signal_type,
    )
    items = [_event_to_item(service.repo, row) for row in rows]
    return WatchSignalEventListResponse(total=total, page=page, limit=limit, items=items)


@router.get(
    "/events/{event_id}",
    response_model=WatchSignalEventDetail,
    responses={404: {"description": "未找到", "model": ErrorResponse}},
)
def get_watch_event_detail(
    event_id: int,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchSignalEventDetail:
    row = service.repo.get_signal_event(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "watch event not found"})
    latest_review = service.repo.get_latest_review(row.id)
    return WatchSignalEventDetail(
        **row.to_dict(),
        latest_review_summary=_review_to_summary(latest_review),
        latest_review=_review_to_summary(latest_review),
    )


@router.get(
    "/stream",
    responses={200: {"description": "SSE 事件流", "content": {"text/event-stream": {}}}},
)
async def watch_stream(
    bus: WatchEventBus = Depends(get_watch_event_bus),
):
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        bus.subscribe(queue)
        yield _format_sse_event("watch.connected", {"message": "Connected to watch stream"})
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield _format_sse_event(event["event_type"], event)
                except asyncio.TimeoutError:
                    yield _format_sse_event("watch.heartbeat", {"timestamp": asyncio.get_running_loop().time()})
        except asyncio.CancelledError:
            logger.debug("watch stream disconnected")
            raise
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
