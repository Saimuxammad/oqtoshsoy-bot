from sqlalchemy import Column, String, Float, Text
from app.database.models import Room
import json
from typing import List


# Добавление новых полей к модели Room
# Эти поля нужно добавить в существующую модель через миграцию или обновление модели

def update_room_model():
    """
    Добавляет новые поля к модели Room.
    Эта функция должна быть вызвана во время инициализации приложения.
    """
    # Добавляем новые поля для различных типов цен
    if not hasattr(Room, 'price_with_food'):
        Room.price_with_food = Column(Float, nullable=True)

    if not hasattr(Room, 'price_without_food_weekday'):
        Room.price_without_food_weekday = Column(Float, nullable=True)

    if not hasattr(Room, 'price_without_food_weekend'):
        Room.price_without_food_weekend = Column(Float, nullable=True)

    # Добавляем поля для медиа-контента и дополнительной информации
    if not hasattr(Room, 'photos'):
        Room.photos = Column(Text, nullable=True)  # JSON-массив URL фотографий

    if not hasattr(Room, 'video_url'):
        Room.video_url = Column(String(500), nullable=True)

    if not hasattr(Room, 'amenities'):
        Room.amenities = Column(Text, nullable=True)  # JSON-массив удобств в номере

    if not hasattr(Room, 'check_in_time'):
        Room.check_in_time = Column(String(50), default="14:00")

    if not hasattr(Room, 'check_out_time'):
        Room.check_out_time = Column(String(50), default="12:00")


# Добавляем вспомогательные методы для работы с JSON-полями
def get_photos(room) -> List[str]:
    """Получить список URL фотографий"""
    if not hasattr(room, 'photos') or not room.photos:
        return []
    try:
        return json.loads(room.photos)
    except:
        return []


def set_photos(room, photo_urls: List[str]) -> None:
    """Установить список URL фотографий"""
    if hasattr(room, 'photos'):
        room.photos = json.dumps(photo_urls)


def get_amenities(room) -> List[str]:
    """Получить список удобств"""
    if not hasattr(room, 'amenities') or not room.amenities:
        return []
    try:
        return json.loads(room.amenities)
    except:
        return []


def set_amenities(room, amenities_list: List[str]) -> None:
    """Установить список удобств"""
    if hasattr(room, 'amenities'):
        room.amenities = json.dumps(amenities_list)


# Добавляем эти методы к классу Room
Room.get_photos = get_photos
Room.set_photos = set_photos
Room.get_amenities = get_amenities
Room.set_amenities = set_amenities