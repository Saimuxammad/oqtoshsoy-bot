from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.database.crud import get_user_by_telegram_id, get_room
from app.database.additional_models import AdditionalService, ServiceBooking, Payment
from app.database.additional_crud import (
    get_all_services, get_available_services, get_service,
    create_service_booking, check_service_availability,
    get_user_service_bookings, get_service_booking,
    cancel_service_booking, get_room_occupancy,
    get_all_rooms_occupancy, create_payment,
    update_payment_status, calculate_booking_price_enhanced
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ================== Маршруты для дополнительных услуг ==================

@router.get("/api/services")
async def get_services(db: AsyncSession = Depends(get_db), available_only: bool = True):
    """API-эндпоинт для получения всех дополнительных услуг"""
    try:
        if available_only:
            services = await get_available_services(db)
        else:
            services = await get_all_services(db)

        return {
            "success": True,
            "services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "price": service.price,
                    "is_hourly": service.is_hourly,
                    "max_capacity": service.max_capacity,
                    "image_url": service.image_url,
                    "is_available": service.is_available
                }
                for service in services
            ]
        }
    except Exception as e:
        logger.error(f"Error getting services: {e}")
        return {"success": False, "detail": str(e)}


@router.get("/api/services/{service_id}")
async def get_service_details(service_id: int, db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для получения данных о конкретной услуге"""
    service = await get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return {
        "success": True,
        "service": {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "price": service.price,
            "is_hourly": service.is_hourly,
            "max_capacity": service.max_capacity,
            "image_url": service.image_url,
            "is_available": service.is_available
        }
    }


@router.get("/api/services/{service_id}/availability")
async def get_service_availability(
        service_id: int,
        date: str,
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для проверки доступности услуги на указанную дату"""
    service = await get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    try:
        # Проверяем формат даты
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Получаем занятые слоты на указанную дату
    from app.database.additional_crud import get_service_occupancy
    occupied_slots = await get_service_occupancy(db, service_id, date)

    # Генерируем все возможные слоты
    all_slots = []
    start_hour = 9  # 9:00
    end_hour = 21  # 21:00

    for hour in range(start_hour, end_hour):
        start_time = f"{hour:02d}:00"
        end_time = f"{hour + 1:02d}:00"

        # Проверяем доступность слота
        is_available = await check_service_availability(
            db, service_id, date, start_time, end_time
        )

        all_slots.append({
            "start_time": start_time,
            "end_time": end_time,
            "is_available": is_available
        })

    return {
        "success": True,
        "service_id": service_id,
        "date": date,
        "slots": all_slots,
        "occupied_slots": occupied_slots
    }


@router.post("/api/services/book")
async def book_service(
        telegram_id: int = Form(...),
        service_id: int = Form(...),
        date: str = Form(...),
        start_time: str = Form(...),
        end_time: str = Form(...),
        guests: int = Form(...),
        notes: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для бронирования дополнительной услуги"""
    try:
        # Проверяем и получаем пользователя
        user = await get_user_by_telegram_id(db, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Проверяем и получаем услугу
        service = await get_service(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        # Создаем бронирование
        service_booking = await create_service_booking(
            db=db,
            user_id=user.id,
            service_id=service_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            guests=guests,
            notes=notes
        )

        return {
            "success": True,
            "booking_id": service_booking.id,
            "message": "Бронирование услуги успешно создано!"
        }
    except ValueError as e:
        # Обработка ошибок валидации из функции create_service_booking
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating service booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/user/{telegram_id}/service-bookings")
async def get_user_all_service_bookings(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для получения всех бронирований услуг пользователя"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookings = await get_user_service_bookings(db, user.id)
    return {
        "success": True,
        "bookings": [
            {
                "id": booking.id,
                "service_id": booking.service_id,
                "service_name": booking.service.name,
                "date": booking.date.strftime("%Y-%m-%d"),
                "start_time": booking.start_time.strftime("%H:%M"),
                "end_time": booking.end_time.strftime("%H:%M"),
                "guests": booking.guests,
                "total_price": booking.total_price,
                "status": booking.status,
                "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else ""
            }
            for booking in bookings
        ]
    }


@router.post("/api/service-bookings/{booking_id}/cancel")
async def cancel_user_service_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для отмены бронирования услуги"""
    booking = await get_service_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Service booking not found")

    cancelled_booking = await cancel_service_booking(db, booking_id)
    if not cancelled_booking:
        raise HTTPException(status_code=500, detail="Failed to cancel service booking")

    return {
        "success": True,
        "message": "Бронирование услуги успешно отменено",
        "booking_id": booking_id
    }


# ================== Маршруты для календаря занятости ==================

@router.get("/api/rooms/availability")
async def get_rooms_availability(
        start_date: str,
        end_date: str,
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для получения данных о занятости всех номеров"""
    try:
        # Проверяем формат дат
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Ограничиваем период до 3 месяцев
        max_period = timedelta(days=90)
        if end - start > max_period:
            raise HTTPException(status_code=400, detail="Maximum allowed period is 90 days")

        # Получаем данные о занятости
        occupancy = await get_all_rooms_occupancy(db, start_date, end_date)

        # Преобразуем результат в удобный формат для API
        result = {}
        for room_id, bookings in occupancy.items():
            room = await get_room(db, room_id)
            if room:
                result[room_id] = {
                    "room_id": room_id,
                    "room_name": room.name,
                    "bookings": bookings
                }

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "rooms": result
        }
    except Exception as e:
        logger.error(f"Error getting rooms availability: {e}")
        return {"success": False, "detail": str(e)}


@router.get("/api/rooms/{room_id}/availability")
async def get_room_availability(
        room_id: int,
        start_date: str,
        end_date: str,
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для получения данных о занятости конкретного номера"""
    room = await get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    try:
        # Проверяем формат дат
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Ограничиваем период до 3 месяцев
        max_period = timedelta(days=90)
        if end - start > max_period:
            raise HTTPException(status_code=400, detail="Maximum allowed period is 90 days")

        # Получаем данные о занятости
        occupancy = await get_room_occupancy(db, room_id, start_date, end_date)

        return {
            "success": True,
            "room_id": room_id,
            "room_name": room.name,
            "start_date": start_date,
            "end_date": end_date,
            "bookings": occupancy
        }
    except Exception as e:
        logger.error(f"Error getting room availability: {e}")
        return {"success": False, "detail": str(e)}


# ================== Маршруты для улучшенного расчета стоимости ==================

@router.post("/api/calculate-price-enhanced")
async def calculate_price_enhanced(
        room_id: int = Form(...),
        check_in: str = Form(...),
        check_out: str = Form(...),
        guests: int = Form(...),
        with_food: bool = Form(False),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для расширенного расчета стоимости бронирования"""
    try:
        # Проверяем формат дат
        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        if check_in_date >= check_out_date:
            raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")

        # Рассчитываем стоимость с учетом питания и дней недели
        price_info = await calculate_booking_price_enhanced(
            db, room_id, check_in, check_out, guests, with_food
        )

        return {
            "success": True,
            "price_info": price_info
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating enhanced price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================== Маршруты для работы с платежами ==================

@router.post("/api/payments/create")
async def create_new_payment(
        amount: float = Form(...),
        payment_method: str = Form(...),
        booking_id: Optional[int] = Form(None),
        service_booking_id: Optional[int] = Form(None),
        payment_id: Optional[str] = Form(None),
        details: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для создания новой записи о платеже"""
    try:
        if not booking_id and not service_booking_id:
            raise HTTPException(status_code=400, detail="Booking ID or Service Booking ID is required")

        # Преобразуем details из JSON строки в словарь, если указан
        payment_details = None
        if details:
            import json
            try:
                payment_details = json.loads(details)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in details field")

        # Создаем платеж
        payment = await create_payment(
            db=db,
            amount=amount,
            payment_method=payment_method,
            booking_id=booking_id,
            service_booking_id=service_booking_id,
            payment_id=payment_id,
            details=payment_details
        )

        return {
            "success": True,
            "payment_id": payment.id,
            "message": "Платеж успешно создан"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/payments/{payment_id}/update")
async def update_payment(
        payment_id: int,
        status: str = Form(...),
        payment_system_id: Optional[str] = Form(None),
        details: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для обновления статуса платежа"""
    try:
        # Преобразуем details из JSON строки в словарь, если указан
        payment_details = None
        if details:
            import json
            try:
                payment_details = json.loads(details)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in details field")

        # Обновляем статус платежа
        payment = await update_payment_status(
            db=db,
            payment_id=payment_id,
            status=status,
            payment_system_id=payment_system_id,
            details=payment_details
        )

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return {
            "success": True,
            "payment_id": payment.id,
            "status": payment.status,
            "message": "Статус платежа успешно обновлен"
        }
    except Exception as e:
        logger.error(f"Error updating payment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))