import os
import json
import redis.asyncio as redis
from typing import Any, Dict, AsyncGenerator

class EventBus:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url)

    async def publish(self, channel: str, event_data: Dict[str, Any]):
        """Publish a JSON event to a specific Redis channel."""
        message = json.dumps(event_data)
        await self.redis.publish(channel, message)
        
    async def subscribe(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield JSON events from a specific Redis channel."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield json.loads(data)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

# Global event bus instance
event_bus = EventBus()
