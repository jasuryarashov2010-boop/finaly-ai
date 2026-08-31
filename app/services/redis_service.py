from datetime import datetime, timezone, timedelta
import redis.asyncio as redis
from app.config import get_settings

class RedisService:
    def __init__(self) -> None:
        self.client = redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=5, socket_timeout=5)

    async def close(self):
        await self.client.aclose()

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def get(self, key: str):
        return await self.client.get(key)

    async def setex(self, key: str, seconds: int, value: str):
        return await self.client.setex(key, seconds, value)

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def incr_daily(self, user_id: int, feature: str, units: int = 1) -> int:
        now = datetime.now(timezone.utc)
        key = f"usage:{user_id}:{now.date().isoformat()}:{feature}"
        value = await self.client.incrby(key, units)
        tomorrow = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc)
        ttl = max(60, int((tomorrow - now).total_seconds()) + 60)
        await self.client.expire(key, ttl)
        return int(value)

    async def get_daily(self, user_id: int, feature: str) -> int:
        now = datetime.now(timezone.utc)
        value = await self.client.get(f"usage:{user_id}:{now.date().isoformat()}:{feature}")
        return int(value or 0)

    async def token_bucket(self, key: str, limit: int, window: int) -> bool:
        current = await self.client.incr(key)
        if current == 1:
            await self.client.expire(key, window)
        return int(current) <= limit

    async def lock(self, key: str, seconds: int = 20) -> bool:
        return bool(await self.client.set(f"lock:{key}", "1", ex=seconds, nx=True))

    async def unlock(self, key: str):
        await self.client.delete(f"lock:{key}")
