import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.errors import ServiceError


logger = logging.getLogger(__name__)
RATE_SCRIPT = """
local value = redis.call('INCR', KEYS[1])
if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return value
"""


class RedisEventService:
    def __init__(self, url: str, manager):
        self.client_name = f"copilot:{uuid4()}"
        self.redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=2,
                                    socket_timeout=3, client_name=self.client_name)
        self.manager = manager
        self.task = None
        self.connected = False
        self.ready = asyncio.Event()

    async def start(self) -> None:
        self.task = asyncio.create_task(self.listen())
        try:
            await asyncio.wait_for(self.ready.wait(), timeout=3)
        except TimeoutError:
            logger.warning("redis_subscriber_not_ready")

    async def listen(self) -> None:
        delay = 0.2
        while True:
            try:
                async with self.redis.pubsub() as subscriber:
                    await subscriber.psubscribe("copilot:users:*")
                    async for message in subscriber.listen():
                        if message["type"] == "psubscribe":
                            self.connected = True
                            self.ready.set()
                            delay = 0.2
                        if message["type"] != "pmessage":
                            continue
                        try:
                            payload = json.loads(message["data"])
                            user_id = message["channel"].removeprefix("copilot:users:")
                            if payload["user_id"] != user_id:
                                continue
                            if payload["type"] in {"auth.revoked", "auth.session_revoked"}:
                                session_id = payload["data"].get("session_id") if payload["type"] == "auth.session_revoked" else None
                                await self.manager.close_user(user_id, session_id)
                                continue
                            if payload["user_id"] == user_id and payload["type"] in {
                                "journal.created", "journal.updated", "journal.deleted",
                                "analysis.completed", "recommendation.created", "safety.alert",
                                "tracking.updated",
                            }:
                                await self.manager.broadcast(user_id, payload)
                        except (ValueError, KeyError, TypeError):
                            logger.warning("invalid_internal_event")
            except asyncio.CancelledError:
                raise
            except (RedisError, OSError):
                self.connected = False
                self.ready.clear()
                await self.manager.close_all()
                logger.warning("redis_subscriber_disconnected")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)

    async def publish(self, user_id: str, event_type: str, data: dict) -> bool:
        event = {"id": str(uuid4()), "type": event_type, "user_id": user_id,
                 "occurred_at": datetime.now(timezone.utc).isoformat(), "data": data}
        try:
            await self.redis.publish(f"copilot:users:{user_id}", json.dumps(event))
            return True
        except (RedisError, OSError):
            logger.warning("event_delivery_unavailable")
            return False

    async def rate_limit(self, key: str, limit: int, seconds: int) -> None:
        try:
            count = await self.redis.eval(RATE_SCRIPT, 1, f"copilot:limits:{key}", seconds)
        except (RedisError, OSError):
            raise ServiceError("rate_limiter_unavailable") from None
        if count > limit:
            raise ServiceError("rate_limit_exceeded", 429)

    async def healthy(self) -> bool:
        try:
            return bool(await self.redis.ping()) and self.connected
        except (RedisError, OSError):
            return False

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        await self.manager.close_all()
        await self.redis.aclose()
