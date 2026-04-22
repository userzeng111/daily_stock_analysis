# -*- coding: utf-8 -*-
"""
===================================
API 依赖注入模块
===================================

职责：
1. 提供数据库 Session 依赖
2. 提供配置依赖
3. 提供服务层依赖
"""

from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from src.storage import DatabaseManager
from src.config import get_config, Config
from src.services.system_config_service import SystemConfigService
from src.services.watch_event_bus import WatchEventBus
from src.services.watch_detail_service import WatchDetailService
from src.services.watch_review_service import WatchReviewService
from src.services.watch_runtime_service import WatchRuntimeService
from src.services.watch_signal_service import WatchSignalService
from src.services.watch_summary_service import WatchSummaryService
from src.services.watchlist_service import WatchlistService
from data_provider.base import DataFetcherManager


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库 Session 依赖
    
    使用 FastAPI 依赖注入机制，确保请求结束后自动关闭 Session
    
    Yields:
        Session: SQLAlchemy Session 对象
        
    Example:
        @router.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            ...
    """
    db_manager = DatabaseManager.get_instance()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def get_config_dep() -> Config:
    """
    获取配置依赖
    
    Returns:
        Config: 配置单例对象
    """
    return get_config()


def get_database_manager() -> DatabaseManager:
    """
    获取数据库管理器依赖
    
    Returns:
        DatabaseManager: 数据库管理器单例对象
    """
    return DatabaseManager.get_instance()


def get_system_config_service(request: Request) -> SystemConfigService:
    """Get app-lifecycle shared SystemConfigService instance."""
    service = getattr(request.app.state, "system_config_service", None)
    if service is None:
        service = SystemConfigService()
        request.app.state.system_config_service = service
    return service


def get_watch_event_bus(request: Request) -> WatchEventBus:
    """Get shared watch event bus instance."""
    bus = getattr(request.app.state, "watch_event_bus", None)
    if bus is None:
        bus = WatchEventBus()
        request.app.state.watch_event_bus = bus
    return bus


def get_watch_review_service(request: Request) -> WatchReviewService:
    """Get shared watch review service instance."""
    service = getattr(request.app.state, "watch_review_service", None)
    if service is None:
        service = WatchReviewService(db_manager=get_database_manager())
        request.app.state.watch_review_service = service
    return service


def get_watch_runtime_service(request: Request) -> WatchRuntimeService:
    """Get shared watch runtime service instance."""
    service = getattr(request.app.state, "watch_runtime_service", None)
    if service is None:
        event_bus = get_watch_event_bus(request)
        review_service = get_watch_review_service(request)
        db_manager = get_database_manager()
        signal_service = WatchSignalService(db_manager=db_manager)
        summary_service = get_watch_summary_service(request)
        service = WatchRuntimeService(
            db_manager=db_manager,
            signal_service=signal_service,
            review_service=review_service,
            summary_service=summary_service,
            event_bus=event_bus,
        )
        request.app.state.watch_runtime_service = service
    return service


def get_watchlist_service(request: Request) -> WatchlistService:
    """Get shared watchlist service instance."""
    service = getattr(request.app.state, "watchlist_service", None)
    if service is None:
        service = WatchlistService(
            db_manager=get_database_manager(),
            summary_service=get_watch_summary_service(request),
        )
        request.app.state.watchlist_service = service
    return service


def get_watch_summary_service(request: Request) -> WatchSummaryService:
    """Get shared watch summary service instance."""
    service = getattr(request.app.state, "watch_summary_service", None)
    if service is None:
        service = WatchSummaryService(db_manager=get_database_manager())
        request.app.state.watch_summary_service = service
    return service


def get_watch_detail_service(request: Request) -> WatchDetailService:
    """Get shared watch detail service instance."""
    service = getattr(request.app.state, "watch_detail_service", None)
    if service is None:
        fetcher = DataFetcherManager()
        service = WatchDetailService(
            db_manager=get_database_manager(),
            repo=get_watchlist_service(request).repo,
            quote_loader=lambda code: fetcher.get_realtime_quote(code),
        )
        request.app.state.watch_detail_service = service
    return service
