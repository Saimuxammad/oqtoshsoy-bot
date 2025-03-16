import datetime
from aiogram.types import Message
from app.database.models import User, Room, Booking
from app.database.crud import get_user_by_telegram_id, get_room, create_booking


async def register_user_if_not_exists(db, user_id, username, full_name):
    """Регистрирует пользователя, если он не существует"""
    user = get_user_by_telegram_id(db, user_id)
    if not user:
        user = User(
            telegram_id=user_id,
            username=username,
            full_name=full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def format_booking_info(booking):
    """Форматирует информацию о бронировании для отображения пользователю"""
    check_in = booking.check_in_date.strftime("%d.%m.%Y")
    check_out = booking.check_out_date.strftime("%d.%m.%Y")

    days = (booking.check_out_date - booking.check_in_date).days

    return (
        f"📝 *Бронирование #{booking.id}*\n\n"
        f"🛏️ Номер: {booking.room.name}\n"
        f"📅 Заезд: {check_in}\n"
        f"📅 Выезд: {check_out}\n"
        f"👥 Гостей: {booking.guests_count}\n"
        f"⏱ Количество ночей: {days}\n"
        f"💰 Итоговая стоимость: {booking.total_price}₽\n"
        f"📊 Статус: {booking.status}\n"
    )


async def calculate_booking_price(room_id, check_in, check_out, guests, db):
    """Рассчитывает стоимость бронирования"""
    room = get_room(db, room_id)
    if not room:
        return None

    # Расчет количества ночей
    delta = check_out - check_in
    nights = delta.days

    if nights <= 0:
        return None

    # Базовая стоимость
    base_price = room.price_per_night * nights

    # Наценка за дополнительных гостей (если больше базовой вместимости)
    extra_guests = max(0, guests - room.capacity)
    extra_fee = extra_guests * (room.price_per_night * 0.3) * nights  # 30% от базовой цены за дополнительного гостя

    return base_price + extra_fee


import logging
from app.database.crud import get_room

logger = logging.getLogger(__name__)


async def calculate_booking_price(room_id, check_in, check_out, guests, db):
    """Calculate booking price based on room details and dates"""
    try:
        room = get_room(db, room_id)
        if not room:
            logger.error(f"Room with ID {room_id} not found")
            return None

        # Calculate number of nights
        delta = check_out - check_in
        nights = delta.days

        if nights <= 0:
            logger.error(f"Invalid booking duration: {nights} nights")
            return None

        # Calculate base price
        base_price = room.price_per_night * nights

        # Add surcharge for extra guests if exceeding room capacity
        extra_guests = max(0, guests - room.capacity)
        extra_fee = extra_guests * (room.price_per_night * 0.3) * nights  # 30% surcharge per extra guest

        total_price = base_price + extra_fee
        logger.info(f"Calculated price for room {room_id}: {total_price} for {nights} nights with {guests} guests")

        return total_price
    except Exception as e:
        logger.error(f"Error calculating booking price: {str(e)}")
        return None