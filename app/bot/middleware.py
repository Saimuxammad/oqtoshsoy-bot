from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        # Create a database session for this request using async context manager
        async with AsyncSessionLocal() as session:
            # Add session to data
            data["session"] = session

            # Pass control to the handler
            return await handler(event, data)

        # Session automatically closed when exiting context manager