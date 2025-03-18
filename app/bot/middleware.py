from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.database import SessionLocal, USE_ASYNC

class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        if USE_ASYNC:
            # Use async session
            async with SessionLocal() as session:
                data["session"] = session
                return await handler(event, data)
        else:
            # Use sync session
            session = SessionLocal()
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                session.close()