from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import datetime
import logging
import json

from app.database import get_db
from app.database.crud import (
    get_user_by_telegram_id, create_user, get_all_rooms, get_room,
    get_available_rooms, create_booking, get_user_bookings
)
from app.bot.utils import calculate_booking_price
from app.config import BOT_TOKEN, ADMIN_TELEGRAM_ID

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
logger = logging.getLogger(__name__)


@router.get("/webapp", response_class=HTMLResponse)
async def webapp(request: Request, room_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """Основная страница веб-приложения"""
    context = {
        "request": request,
        "room_id": room_id
    }

    if room_id:
        room = await get_room(db, room_id)
        if room:
            context["room"] = room

    # Получаем все доступные номера для отображения
    rooms = await get_all_rooms(db)
    context["rooms"] = rooms

    return templates.TemplateResponse("index.html", context)


@router.get("/api/rooms")
async def get_rooms(db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для получения всех номеров"""
    try:
        # Используем await здесь
        rooms = await get_all_rooms(db)

        return {
            "success": True,
            "rooms": [
                {
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "type": room.room_type,
                    "price": room.price_per_night,
                    "weekend_price": room.weekend_price if hasattr(room,
                                                                   "weekend_price") and room.weekend_price else None,
                    "capacity": room.capacity,
                    "available": room.is_available,
                    "image_url": room.image_url
                }
                for room in rooms
            ]
        }
    except Exception as e:
        logger.error(f"Error getting rooms: {e}")
        return {"success": False, "detail": str(e)}


@router.get("/api/rooms/{room_id}")
async def get_room_details(room_id: int, db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для получения данных о конкретном номере"""
    room = await get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Парсим JSON-поля
    amenities = []
    photos = []

    if room.amenities:
        try:
            amenities = json.loads(room.amenities)
        except:
            amenities = []

    if room.photos:
        try:
            photos = json.loads(room.photos)
        except:
            photos = []

    return {
        "success": True,
        "room": {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "type": room.room_type,
            "price": room.price_per_night,
            "weekend_price": room.weekend_price if hasattr(room, "weekend_price") and room.weekend_price else None,
            "capacity": room.capacity,
            "available": room.is_available,
            "image_url": room.image_url,
            "photos": photos,
            "video_url": room.video_url,
            "amenities": amenities
        }
    }


@router.post("/api/calculate-price")
async def calculate_price(
        room_id: int = Form(...),
        check_in: str = Form(...),
        check_out: str = Form(...),
        guests: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для расчета стоимости бронирования"""
    try:
        check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if check_in_date >= check_out_date:
        raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")

    # Убедитесь, что функция calculate_booking_price правильно работает с датами
    price = await calculate_booking_price(db, room_id, check_in, check_out, guests)
    if price is None:
        raise HTTPException(status_code=400, detail="Could not calculate price")

    return {
        "success": True,
        "price": price,
        "nights": (check_out_date - check_in_date).days
    }


@router.post("/api/book")
async def book_room(
        telegram_id: int = Form(...),
        room_id: int = Form(...),
        check_in: str = Form(...),
        check_out: str = Form(...),
        guests: int = Form(...),
        phone: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """API-эндпоинт для создания бронирования"""
    try:
        # Проверяем и получаем пользователя
        user = await get_user_by_telegram_id(db, telegram_id)
        if not user:
            # Создаем пользователя, если он не существует
            user = await create_user(db, telegram_id)

        # Проверяем и получаем номер
        room = await get_room(db, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Преобразуем даты
        try:
            check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        # Создаем бронирование
        booking = await create_booking(
            db=db,
            user_id=user.id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            phone=phone
        )

        # Отправляем уведомление администратору если настроено
        try:
            from aiogram import Bot
            if ADMIN_TELEGRAM_ID and BOT_TOKEN:
                bot = Bot(token=BOT_TOKEN)

                # Формируем текст уведомления
                booking_info = (
                    f"📝 *Новое бронирование #{booking.id}*\n\n"
                    f"🛏️ Номер: {room.name}\n"
                    f"📅 Заезд: {check_in_date.strftime('%d.%m.%Y')}\n"
                    f"📅 Выезд: {check_out_date.strftime('%d.%m.%Y')}\n"
                    f"👥 Гостей: {guests}\n"
                    f"⏱ Ночей: {(check_out_date - check_in_date).days}\n"
                    f"💰 Сумма: {booking.total_price}₽\n\n"
                    f"📱 Контакт: {phone if phone else 'Не указан'}\n"
                    f"👤 Пользователь: {user.username if user.username else f'@{telegram_id}'}"
                )

                await bot.send_message(
                    chat_id=ADMIN_TELEGRAM_ID,
                    text=booking_info,
                    parse_mode="Markdown"
                )

                # Отмечаем что администратор уведомлен
                booking.admin_notified = True
                await db.commit()
                logger.info(f"Admin notification for booking #{booking.id} sent successfully")

        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            # Не прерываем процесс если уведомление не отправилось

        return {
            "success": True,
            "booking_id": booking.id,
            "message": "Бронирование успешно создано!"
        }
    except ValueError as e:
        # Обработка ошибок валидации из функции create_booking
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/user/{telegram_id}/bookings")
async def get_user_all_bookings(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """API-эндпоинт для получения всех бронирований пользователя"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookings = await get_user_bookings(db, user.id)
    return {
        "success": True,
        "bookings": [
            {
                "id": booking.id,
                "room_name": booking.room.name,
                "check_in": booking.check_in.strftime("%Y-%m-%d"),
                "check_out": booking.check_out.strftime("%Y-%m-%d"),
                "guests": booking.guests,
                "total_price": booking.total_price,
                "status": booking.status,
                "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else ""
            }
            for booking in bookings
        ]
    }