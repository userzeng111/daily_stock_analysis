# -*- coding: utf-8 -*-
"""Watch-specific event bus for SSE-compatible queue subscribers."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class WatchEventBus:
    """Broadcast watch runtime events to subscribed asyncio queues."""

    def __init__(self) -> None:
        self._subscribers: List[Tuple[asyncio.Queue, Optional[asyncio.AbstractEventLoop]]] = []
        self._lock = threading.Lock()

    def subscribe(
        self,
        queue: asyncio.Queue,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        subscriber_loop = loop
        if subscriber_loop is None:
            try:
                subscriber_loop = asyncio.get_running_loop()
            except RuntimeError:
                subscriber_loop = None
        with self._lock:
            self._subscribers.append((queue, subscriber_loop))

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers = [
                (subscriber, loop)
                for subscriber, loop in self._subscribers
                if subscriber is not queue
            ]

    def publish(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event_type": event_type,
            "occurred_at": datetime.now().isoformat(),
            "payload": payload,
        }
        with self._lock:
            subscribers = list(self._subscribers)

        for queue, loop in subscribers:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                queue.put_nowait(event)
        return event
