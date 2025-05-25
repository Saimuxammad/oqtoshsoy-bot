# 1. Создайте новый файл app/bot/cache.py
"""
Модуль для кеширования данных
"""
import json
from functools import lru_cache
from typing import Optional, List, Dict
import redis.asyncio as redis
from app.config import REDIS_URL

# Инициализация Redis (опционально)
try:
    redis_client = redis.from_url(REDIS_URL or "redis://localhost:6379", decode_responses=True)
except:
    redis_client = None  # Работаем без Redis если недоступен

# Простое in-memory кеширование если Redis недоступен
memory_cache = {}


async def get_cached(key: str, ttl: int = 300) -> Optional[str]:
    """Получить данные из кеша"""
    if redis_client:
        try:
            return await redis_client.get(key)
        except:
            pass

    # Fallback на memory cache
    return memory_cache.get(key)


async def set_cached(key: str, value: str, ttl: int = 300):
    """Сохранить данные в кеш"""
    if redis_client:
        try:
            await redis_client.setex(key, ttl, value)
            return
        except:
            pass

    # Fallback на memory cache
    memory_cache[key] = value


# 2. Обновите app/bot/handlers.py - добавьте в начало:
from app.bot.cache import get_cached, set_cached
import asyncio
from typing import List


# 3. Обновите функцию показа номеров:
@router.message(F.text == "🛏️ Номера")
async def show_rooms(message: Message, session: AsyncSession):
    # Пробуем получить из кеша
    cache_key = "rooms_list"
    cached_data = await get_cached(cache_key)

    if cached_data:
        rooms = json.loads(cached_data)
    else:
        # Загружаем из БД
        rooms_obj = await get_all_rooms(session)
        # Конвертируем в словари для кеширования
        rooms = [
            {
                "id": r.id,
                "name": r.name,
                "room_type": r.room_type,
                "price_per_night": r.price_per_night,
                "weekend_price": getattr(r, "weekend_price", r.price_per_night)
            }
            for r in rooms_obj
        ]
        # Сохраняем в кеш на 5 минут
        await set_cached(cache_key, json.dumps(rooms), ttl=300)

    await message.answer(
        "🛏️ Выберите категорию номера для подробной информации:",
        reply_markup=rooms_keyboard(rooms),
        parse_mode=None
    )