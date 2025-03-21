from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Table
from sqlalchemy.orm import relationship
import datetime
import json
from typing import List, Dict, Any, Optional

# Импортируем Base и существующую модель Room
from app.database.models import Base, Room

# Модель для дополнительных услуг
class AdditionalService(Base):
    __tablename__ = "additional_services"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)  # Цена за час/услугу
    is_hourly = Column(Boolean, default=True)  # True если цена за час, False если фиксированная цена
    max_capacity = Column(Integer, nullable=True)  # Максимальное количество человек (для групповых услуг)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)

    bookings = relationship("ServiceBooking", back_populates="service")

    def __repr__(self):
        return f"<AdditionalService {self.name}>"


# Модель для бронирования дополнительных услуг
class ServiceBooking(Base):
    __tablename__ = "service_bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("additional_services.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)  # Связь с основным бронированием (опционально)
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    guests = Column(Integer, default=1)
    total_price = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)

    user = relationship("User", backref="service_bookings")
    service = relationship("AdditionalService", back_populates="bookings")
    booking = relationship("Booking", backref="service_bookings")

    def __repr__(self):
        return f"<ServiceBooking {self.id} - {self.service.name if self.service else 'Unknown'}>"


# Модель для администраторов бота
class BotAdmin(Base):
    __tablename__ = "bot_admins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    is_superadmin = Column(Boolean, default=False)  # Суперадмин имеет полный доступ
    can_manage_rooms = Column(Boolean, default=True)  # Может управлять номерами
    can_manage_bookings = Column(Boolean, default=True)  # Может управлять бронированиями
    can_manage_services = Column(Boolean, default=True)  # Может управлять доп. услугами
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")

    def __repr__(self):
        return f"<BotAdmin {self.user.username if self.user else self.telegram_id}>"


# Модель для хранения информации о платежах
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)  # Для обычных бронирований
    service_booking_id = Column(Integer, ForeignKey("service_bookings.id"), nullable=True)  # Для доп. услуг
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)  # payme, click, cash, etc.
    payment_id = Column(String(255), nullable=True)  # ID платежа в платежной системе
    status = Column(String(50), default="pending")  # pending, completed, failed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)  # JSON с дополнительной информацией

    booking = relationship("Booking", backref="payments")
    service_booking = relationship("ServiceBooking", backref="payments")

    def __repr__(self):
        return f"<Payment {self.id} - {self.amount} - {self.status}>"

    def get_details(self) -> Dict[str, Any]:
        """Получить детали платежа"""
        if not self.details:
            return {}
        try:
            return json.loads(self.details)
        except:
            return {}

    def set_details(self, details: Dict[str, Any]) -> None:
        """Установить детали платежа"""
        self.details = json.dumps(details)


# Вспомогательные методы для работы с существующей моделью Room
def get_photos(room: Room) -> List[str]:
    """Получить список URL фотографий"""
    if not hasattr(room, 'photos') or not room.photos:
        return []
    try:
        return json.loads(room.photos)
    except:
        return []

def set_photos(room: Room, photo_urls: List[str]) -> None:
    """Установить список URL фотографий"""
    if hasattr(room, 'photos'):
        room.photos = json.dumps(photo_urls)

def get_amenities(room: Room) -> List[str]:
    """Получить список удобств"""
    if not hasattr(room, 'amenities') or not room.amenities:
        return []
    try:
        return json.loads(room.amenities)
    except:
        return []

def set_amenities(room: Room, amenities_list: List[str]) -> None:
    """Установить список удобств"""
    if hasattr(room, 'amenities'):
        room.amenities = json.dumps(amenities_list)

# Добавляем эти методы к классу Room
Room.get_photos = get_photos
Room.set_photos = set_photos
Room.get_amenities = get_amenities
Room.set_amenities = set_amenities