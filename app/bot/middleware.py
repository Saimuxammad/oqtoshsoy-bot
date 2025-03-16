from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.database import SessionLocal


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        # Create a database session for this request
        session = SessionLocal()
        data["session"] = session

        try:
            # Pass control to the handler
            return await handler(event, data)
        finally:
            # Always close the session
            session.close()