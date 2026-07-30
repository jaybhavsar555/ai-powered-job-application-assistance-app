"""
Event bus with Redis Pub/Sub and an in-process fallback.

Local queues ensure same-process publishers (LangGraph background task)
are delivered to SSE subscribers even if Redis is down or messages race
ahead of Redis subscribe.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from typing import Any, Dict, Set

import redis.asyncio as redis


class EventBus:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, socket_connect_timeout=2)
        self._local_queues: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._redis_ok: bool | None = None

    async def _ensure_redis(self) -> bool:
        if self._redis_ok is True:
            return True
        try:
            await self.redis.ping()
            self._redis_ok = True
            return True
        except Exception:
            self._redis_ok = False
            return False

    def register(self, channel: str) -> asyncio.Queue:
        """Register a local subscriber immediately (call before publishing)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._local_queues[channel].add(q)
        return q

    def unregister(self, channel: str, q: asyncio.Queue) -> None:
        self._local_queues[channel].discard(q)

    async def publish(self, channel: str, event_data: Dict[str, Any]):
        message = json.dumps(event_data)

        for q in list(self._local_queues.get(channel, set())):
            try:
                q.put_nowait(event_data)
            except asyncio.QueueFull:
                pass

        if await self._ensure_redis():
            try:
                await self.redis.publish(channel, message)
            except Exception:
                self._redis_ok = False


event_bus = EventBus()
