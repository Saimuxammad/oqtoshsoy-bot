import datetime
import logging
from aiogram.types import Message
from app.database.models import User, Room, Booking
from app.database.crud import get_user_by_telegram_id, get_room, create_booking

logger = logging.getLogger(__name__)

async def register_user_if_not_exists(db, user_id, username, first_name, last_name):
    """Registers user if they don't exist"""
    user = await get_user_by_telegram_id(db, user_id)
    if not user:
        user = User(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def format_booking_info(booking):
    """Formats booking information for display to user"""
    check_in = booking.check_in.strftime("%d.%m.%Y")
    check_out = booking.check_out.strftime("%d.%m.%Y")
    days = (booking.check_out - booking.check_in).days

    return (
        f"📝 *Бронирование #{booking.id}*\n\n"
        f"🛏️ Номер: {booking.room.name}\n"
        f"📅 Заезд: {check_in}\n"
        f"📅 Выезд: {check_out}\n"
        f"👥 Гостей: {booking.guests}\n"
        f"⏱ Количество ночей: {days}\n"
        f"💰 Итоговая стоимость: {booking.total_price}₽\n"
        f"📊 Статус: {booking.status}\n"
    )


async def calculate_booking_price(db, room_id, check_in, check_out, guests):
    """Calculate booking price based on room details and dates"""
    try:
        room = await get_room(db, room_id)
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