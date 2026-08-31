from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from collections.abc import Awaitable, Callable
from typing import Any
from app.config import get_settings

class BlockedMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]):
        user = getattr(event, "from_user", None)
        if user and user.id not in get_settings().admin_id_set:
            db_user = data.get("db_user")
            if db_user and db_user.is_blocked:
                return None
        return await handler(event, data)
