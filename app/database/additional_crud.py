from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func, desc, update, delete
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Any, Tuple
import logging

from app.database.models import User, Room, Booking, Review
from app.database.additional_models import AdditionalService, ServiceBooking, BotAdmin, Payment

logger = logging.getLogger(__name__)


# ============== Функции для работы с дополнительными услугами ==============

async def get_all_services(db: AsyncSession) -> List[AdditionalService]:
    """Получить все дополнительные услуги"""
    result = await db.execute(select(AdditionalService).order_by(AdditionalService.name))
    return result.scalars().all()


async def get_available_services(db: AsyncSession) -> List[AdditionalService]:
    """Получить все активные дополнительные услуги"""
    result = await db.execute(
        select(AdditionalService)
        .where(AdditionalService.is_available == True)
        .order_by(AdditionalService.name)
    )
    return result.scalars().all()


async def get_service(db: AsyncSession, service_id: int) -> Optional[AdditionalService]:
    """Получить дополнительную услугу по ID"""
    result = await db.execute(select(AdditionalService).where(AdditionalService.id == service_id))
    return result.scalars().first()


async def create_service(
        db: AsyncSession,
        name: str,
        price: float,
        is_hourly: bool = True,
        description: Optional[str] = None,
        max_capacity: Optional[int] = None,
        image_url: Optional[str] = None
) -> AdditionalService:
    """Создать новую дополнительную услугу"""
    service = AdditionalService(
        name=name,
        description=description,
        price=price,
        is_hourly=is_hourly,
        max_capacity=max_capacity,
        image_url=image_url,
        is_available=True
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


async def update_service(
        db: AsyncSession,
        service_id: int,
        **kwargs
) -> Optional[AdditionalService]:
    """Обновить данные дополнительной услуги"""
    service = await get_service(db, service_id)
    if not service:
        return None

    for key, value in kwargs.items():
        if hasattr(service, key):
            setattr(service, key, value)

    await db.commit()
    await db.refresh(service)
    return service


async def delete_service(db: AsyncSession, service_id: int) -> bool:
    """Удалить дополнительную услугу"""
    service = await get_service(db, service_id)
    if not service:
        return False

    await db.delete(service)
    await db.commit()
    return True


# ============== Функции для работы с бронированием услуг ==============

async def check_service_availability(
        db: AsyncSession,
        service_id: int,
        date: str,
        start_time: str,
        end_time: str
) -> bool:
    """Проверить доступность дополнительной услуги на указанную дату и время"""
    service = await get_service(db, service_id)
    if not service or not service.is_available:
        return False

    # Преобразуем строки в datetime
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    start_datetime = datetime.combine(date_obj, datetime.strptime(start_time, "%H:%M").time())
    end_datetime = datetime.combine(date_obj, datetime.strptime(end_time, "%H:%M").time())

    # Проверяем пересечение с существующими бронированиями
    result = await db.execute(
        select(ServiceBooking).where(
            and_(
                ServiceBooking.service_id == service_id,
                ServiceBooking.status != "cancelled",
                ServiceBooking.date == date_obj,
                or_(
                    # Новое начало во время существующего бронирования
                    and_(
                        ServiceBooking.start_time <= start_datetime,
                        ServiceBooking.end_time > start_datetime
                    ),
                    # Новый конец во время существующего бронирования
                    and_(
                        ServiceBooking.start_time < end_datetime,
                        ServiceBooking.end_time >= end_datetime
                    ),
                    # Новое бронирование полностью охватывает существующее
                    and_(
                        ServiceBooking.start_time >= start_datetime,
                        ServiceBooking.end_time <= end_datetime
                    )
                )
            )
        )
    )

    # Если есть пересечения, услуга недоступна
    return result.scalars().first() is None


async def create_service_booking(
        db: AsyncSession,
        user_id: int,
        service_id: int,
        date: str,
        start_time: str,
        end_time: str,
        guests: int = 1,
        booking_id: Optional[int] = None,
        notes: Optional[str] = None
) -> ServiceBooking:
    """Создать бронирование дополнительной услуги"""
    # Проверяем доступность услуги
    is_available = await check_service_availability(db, service_id, date, start_time, end_time)
    if not is_available:
        raise ValueError("Услуга недоступна на указанное время")

    # Получаем услугу для расчета стоимости
    service = await get_service(db, service_id)
    if not service:
        raise ValueError("Услуга не найдена")

    # Проверяем количество гостей
    if service.max_capacity and guests > service.max_capacity:
        raise ValueError(f"Максимальное количество человек для этой услуги: {service.max_capacity}")

    # Преобразуем строки в datetime
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    start_datetime = datetime.combine(date_obj, datetime.strptime(start_time, "%H:%M").time())
    end_datetime = datetime.combine(date_obj, datetime.strptime(end_time, "%H:%M").time())

    # Рассчитываем стоимость
    if service.is_hourly:
        duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
        total_price = service.price * duration_hours
    else:
        total_price = service.price

    # Создаем бронирование
    service_booking = ServiceBooking(
        user_id=user_id,
        service_id=service_id,
        booking_id=booking_id,
        date=date_obj,
        start_time=start_datetime,
        end_time=end_datetime,
        guests=guests,
        total_price=total_price,
        status="pending",
        notes=notes
    )

    db.add(service_booking)
    await db.commit()
    await db.refresh(service_booking)
    return service_booking


async def get_user_service_bookings(db: AsyncSession, user_id: int) -> List[ServiceBooking]:
    """Получить все бронирования дополнительных услуг пользователя"""
    result = await db.execute(
        select(ServiceBooking)
        .where(ServiceBooking.user_id == user_id)
        .order_by(desc(ServiceBooking.created_at))
    )
    return result.scalars().all()


async def get_service_booking(db: AsyncSession, booking_id: int) -> Optional[ServiceBooking]:
    """Получить бронирование дополнительной услуги по ID"""
    result = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    return result.scalars().first()


async def update_service_booking_status(
        db: AsyncSession,
        booking_id: int,
        status: str
) -> Optional[ServiceBooking]:
    """Обновить статус бронирования дополнительной услуги"""
    booking = await get_service_booking(db, booking_id)
    if not booking:
        return None

    booking.status = status
    await db.commit()
    await db.refresh(booking)
    return booking


async def cancel_service_booking(db: AsyncSession, booking_id: int) -> Optional[ServiceBooking]:
    """Отменить бронирование дополнительной услуги"""
    return await update_service_booking_status(db, booking_id, "cancelled")


# ============== Функции для работы с календарем занятости ==============

async def get_room_occupancy(
        db: AsyncSession,
        room_id: int,
        start_date: str,
        end_date: str
) -> List[Dict[str, Any]]:
    """Получить данные о занятости номера за период"""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    result = await db.execute(
        select(Booking)
        .where(
            and_(
                Booking.room_id == room_id,
                Booking.status != "cancelled",
                or_(
                    # Бронирование начинается в указанный период
                    and_(
                        Booking.check_in >= start,
                        Booking.check_in <= end
                    ),
                    # Бронирование заканчивается в указанный период
                    and_(
                        Booking.check_out >= start,
                        Booking.check_out <= end
                    ),
                    # Бронирование охватывает весь указанный период
                    and_(
                        Booking.check_in <= start,
                        Booking.check_out >= end
                    )
                )
            )
        )
    )

    bookings = result.scalars().all()
    occupancy_data = []

    for booking in bookings:
        occupancy_data.append({
            "booking_id": booking.id,
            "room_id": booking.room_id,
            "check_in": booking.check_in.strftime("%Y-%m-%d"),
            "check_out": booking.check_out.strftime("%Y-%m-%d"),
            "status": booking.status,
            "guest_name": f"{booking.user.first_name} {booking.user.last_name}" if booking.user else "Неизвестный",
            "guests": booking.guests
        })

    return occupancy_data


async def get_all_rooms_occupancy(
        db: AsyncSession,
        start_date: str,
        end_date: str
) -> Dict[int, List[Dict[str, Any]]]:
    """Получить данные о занятости всех номеров за период"""
    from app.database.crud import get_all_rooms

    rooms = await get_all_rooms(db)
    result = {}

    for room in rooms:
        room_occupancy = await get_room_occupancy(db, room.id, start_date, end_date)
        result[room.id] = room_occupancy

    return result


async def get_service_occupancy(
        db: AsyncSession,
        service_id: int,
        date: str
) -> List[Dict[str, Any]]:
    """Получить данные о занятости дополнительной услуги на указанную дату"""
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    result = await db.execute(
        select(ServiceBooking)
        .where(
            and_(
                ServiceBooking.service_id == service_id,
                ServiceBooking.status != "cancelled",
                ServiceBooking.date == date_obj
            )
        )
        .order_by(ServiceBooking.start_time)
    )

    bookings = result.scalars().all()
    occupancy_data = []

    for booking in bookings:
        occupancy_data.append({
            "booking_id": booking.id,
            "service_id": booking.service_id,
            "date": booking.date.strftime("%Y-%m-%d"),
            "start_time": booking.start_time.strftime("%H:%M"),
            "end_time": booking.end_time.strftime("%H:%M"),
            "status": booking.status,
            "guest_name": f"{booking.user.first_name} {booking.user.last_name}" if booking.user else "Неизвестный",
            "guests": booking.guests
        })

    return occupancy_data


# ============== Функции для работы с администраторами бота ==============

async def get_bot_admin(db: AsyncSession, telegram_id: int) -> Optional[BotAdmin]:
    """Получить администратора бота по Telegram ID"""
    result = await db.execute(select(BotAdmin).where(BotAdmin.telegram_id == telegram_id))
    return result.scalars().first()


async def create_bot_admin(
        db: AsyncSession,
        user_id: int,
        telegram_id: int,
        is_superadmin: bool = False
) -> BotAdmin:
    """Создать нового администратора бота"""
    admin = BotAdmin(
        user_id=user_id,
        telegram_id=telegram_id,
        is_superadmin=is_superadmin,
        can_manage_rooms=True,
        can_manage_bookings=True,
        can_manage_services=True
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def update_bot_admin(
        db: AsyncSession,
        telegram_id: int,
        **kwargs
) -> Optional[BotAdmin]:
    """Обновить данные администратора бота"""
    admin = await get_bot_admin(db, telegram_id)
    if not admin:
        return None

    for key, value in kwargs.items():
        if hasattr(admin, key):
            setattr(admin, key, value)

    await db.commit()
    await db.refresh(admin)
    return admin


async def delete_bot_admin(db: AsyncSession, telegram_id: int) -> bool:
    """Удалить администратора бота"""
    admin = await get_bot_admin(db, telegram_id)
    if not admin:
        return False

    await db.delete(admin)
    await db.commit()
    return True


async def check_admin_permissions(db: AsyncSession, telegram_id: int, permission: str) -> bool:
    """Проверить наличие у администратора определенных прав"""
    admin = await get_bot_admin(db, telegram_id)
    if not admin:
        return False

    if admin.is_superadmin:
        return True

    permission_map = {
        "rooms": admin.can_manage_rooms,
        "bookings": admin.can_manage_bookings,
        "services": admin.can_manage_services
    }

    return permission_map.get(permission, False)


# ============== Функции для работы с платежами ==============

async def create_payment(
        db: AsyncSession,
        amount: float,
        payment_method: str,
        booking_id: Optional[int] = None,
        service_booking_id: Optional[int] = None,
        payment_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
) -> Payment:
    """Создать новую запись о платеже"""
    if not booking_id and not service_booking_id:
        raise ValueError("Необходимо указать booking_id или service_booking_id")

    payment = Payment(
        booking_id=booking_id,
        service_booking_id=service_booking_id,
        amount=amount,
        payment_method=payment_method,
        payment_id=payment_id,
        status="pending"
    )

    if details:
        payment.set_details(details)

    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def update_payment_status(
        db: AsyncSession,
        payment_id: int,
        status: str,
        payment_system_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
) -> Optional[Payment]:
    """Обновить статус платежа"""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalars().first()

    if not payment:
        return None

    payment.status = status
    payment.updated_at = datetime.utcnow()

    if payment_system_id:
        payment.payment_id = payment_system_id

    if details:
        current_details = payment.get_details()
        current_details.update(details)
        payment.set_details(current_details)

    await db.commit()
    await db.refresh(payment)
    return payment


async def get_payment(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Получить платеж по ID"""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalars().first()


async def get_booking_payments(db: AsyncSession, booking_id: int) -> List[Payment]:
    """Получить все платежи для бронирования"""
    result = await db.execute(
        select(Payment)
        .where(Payment.booking_id == booking_id)
        .order_by(desc(Payment.created_at))
    )
    return result.scalars().all()


async def get_service_booking_payments(db: AsyncSession, service_booking_id: int) -> List[Payment]:
    """Получить все платежи для бронирования дополнительной услуги"""
    result = await db.execute(
        select(Payment)
        .where(Payment.service_booking_id == service_booking_id)
        .order_by(desc(Payment.created_at))
    )
    return result.scalars().all()


# ============== Улучшенная функция расчета цены ==============

async def calculate_booking_price_enhanced(
        db: AsyncSession,
        room_id: int,
        check_in: str,
        check_out: str,
        guests: int,
        with_food: bool = False
) -> Dict[str, Any]:
    """Расширенный расчет стоимости бронирования с учетом питания и дней недели"""
    from app.database.crud import get_room

    room = await get_room(db, room_id)
    if not room:
        raise ValueError("Номер не найден")

    # Преобразуем строки в объекты datetime
    check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()

    # Проверяем корректность дат
    if check_out_date <= check_in_date:
        raise ValueError("Дата выезда должна быть позже даты заезда")

    # Считаем количество ночей
    nights = (check_out_date - check_in_date).days

    # Если выбрано питание, используем цену с питанием
    if with_food and hasattr(room, 'price_with_food') and room.price_with_food:
        total_price = room.price_with_food * nights
        price_details = {
            "base_price_per_night": room.price_with_food,
            "nights": nights,
            "food_included": True,
            "price_breakdown": [{"night": i + 1, "price": room.price_with_food} for i in range(nights)]
        }
    else:
        # Без питания - учитываем разные цены для будних и выходных дней
        current_date = check_in_date
        total_price = 0
        price_breakdown = []

        for i in range(nights):
            # Определяем день недели (0 - понедельник, 6 - воскресенье)
            weekday = current_date.weekday()

            # Определяем, это будний (0-3, пн-чт) или выходной (4-6, пт-вс) день
            is_weekend = weekday >= 4  # Пятница, суббота, воскресенье

            # Проверяем наличие атрибутов перед использованием
            has_weekday_price = hasattr(room, 'price_without_food_weekday') and room.price_without_food_weekday
            has_weekend_price = hasattr(room, 'price_without_food_weekend') and room.price_without_food_weekend

            if is_weekend and has_weekend_price:
                night_price = room.price_without_food_weekend
            elif not is_weekend and has_weekday_price:
                night_price = room.price_without_food_weekday
            else:
                # Если специальные цены не установлены, используем стандартную
                night_price = room.price_per_night

            total_price += night_price
            price_breakdown.append({
                "night": i + 1,
                "date": current_date.strftime("%Y-%m-%d"),
                "price": night_price,
                "is_weekend": is_weekend
            })

            # Переходим к следующему дню
            current_date += timedelta(days=1)

        price_details = {
            "nights": nights,
            "food_included": False,
            "price_breakdown": price_breakdown
        }

    # Добавляем наценку за дополнительных гостей
    if guests > room.capacity:
        extra_guests = guests - room.capacity
        extra_fee_per_night = room.price_per_night * 0.3  # 30% от базовой цены за доп. гостя
        extra_fee_total = extra_fee_per_night * nights * extra_guests

        total_price += extra_fee_total
        price_details["extra_guests"] = extra_guests
        price_details["extra_fee_per_night"] = extra_fee_per_night
        price_details["extra_fee_total"] = extra_fee_total

    return {
        "total_price": total_price,
        "nights": nights,
        "guests": guests,
        "room_name": room.name,
        "room_capacity": room.capacity,
        "check_in": check_in,
        "check_out": check_out,
        "with_food": with_food,
        "details": price_details
    }