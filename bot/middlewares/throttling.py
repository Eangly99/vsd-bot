import time
from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit_seconds: float = 3.0):
        super().__init__()
        self.rate_limit_seconds = rate_limit_seconds
        self.user_last_message: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            now = time.time()
            last_time = self.user_last_message.get(user_id, 0)
            
            if now - last_time < self.rate_limit_seconds:
                await event.answer("⚠️ Please wait a few seconds before sending another link!")
                return
            
            self.user_last_message[user_id] = now
        
        return await handler(event, data)
