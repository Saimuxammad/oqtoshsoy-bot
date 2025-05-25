# 4. Создайте app/bot/batch_sender.py для массовых рассылок:
"""
Модуль для оптимизированной отправки сообщений
"""
import asyncio
from typing import List, Tuple, Dict, Any
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)


class BatchMessageSender:
    """Отправка сообщений батчами"""

    def __init__(self, bot: Bot, batch_size: int = 30, delay: float = 0.05):
        self.bot = bot
        self.batch_size = batch_size
        self.delay = delay  # Задержка между сообщениями
        self.queue: List[Tuple[int, str, Dict[str, Any]]] = []

    async def add_message(self, chat_id: int, text: str, **kwargs):
        """Добавить сообщение в очередь"""
        self.queue.append((chat_id, text, kwargs))

        if len(self.queue) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """Отправить все сообщения из очереди"""
        if not self.queue:
            return

        success_count = 0

        # Отправляем по одному с небольшой задержкой
        for chat_id, text, kwargs in self.queue:
            try:
                await self.bot.send_message(chat_id, text, **kwargs)
                success_count += 1
                await asyncio.sleep(self.delay)  # Защита от rate limit
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")

        logger.info(f"Sent {success_count}/{len(self.queue)} messages")
        self.queue.clear()

        return success_count