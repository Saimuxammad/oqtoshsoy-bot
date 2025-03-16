from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import datetime

from app.database import get_db
from app.database.crud import (
    get_user_by_telegram_id, create_user, get_all_rooms, get_room,
    get_available_rooms, create_booking, get_user_bookings
)
from app.bot.utils import calculate_booking_price

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/webapp", response_class=HTMLResponse)
async def webapp(request: Request, room_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Основная страница веб-приложения"""
    context = {
        "request": request,
        "room_id": room_id
    }

    if room_id:
        room = get_room(db, room_id)
        if room:
            context["room"] = room

    # Получаем все доступные номера для отображения
    rooms = get_all_rooms(db)
    context["rooms"] = rooms

    return templates.TemplateResponse("index.html", context)


@router.get("/api/rooms")
async def get_rooms(db: Session = Depends(get_db)):
    """API-эндпоинт для получения всех номеров"""
    rooms = get_all_rooms(db)
    return {
        "success": True,
        "rooms": [
            {
                "id": room.id,
                "name": room.name,
                "description": room.description,
                "type": room.room_type,
                "price": room.price_per_night,
                "capacity": room.capacity,
                "available": room.is_available,
                "image_url": room.image_url
            }
            for room in rooms
        ]
    }


@router.get("/api/rooms/{room_id}")
async def get_room_details(room_id: int, db: Session = Depends(get_db)):
    """API-эндпоинт для получения данных о конкретном номере"""
    room = get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return {
        "success": True,
        "room": {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "type": room.room_type,
            "price": room.price_per_night,
            "capacity": room.capacity,
            "available": room.is_available,
            "image_url": room.image_url
        }
    }


@router.post("/api/calculate-price")
async def calculate_price(
        room_id: int = Form(...),
        check_in: str = Form(...),
        check_out: str = Form(...),
        guests: int = Form(...),
        db: Session = Depends(get_db)
):
    """API-эндпоинт для расчета стоимости бронирования"""
    try:
        check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if check_in_date >= check_out_date:
        raise HTTPException(status_code=400, detail="Check-out date must be after check-in date")

    price = await calculate_booking_price(room_id, check_in_date, check_out_date, guests, db)
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
        db: Session = Depends(get_db)
):
    """API-эндпоинт для создания бронирования"""
    # Проверяем и получаем пользователя
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем и получаем номер
    room = get_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Преобразуем даты
    try:
        check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Рассчитываем стоимость
    total_price = await calculate_booking_price(room_id, check_in_date, check_out_date, guests, db)
    if total_price is None:
        raise HTTPException(status_code=400, detail="Could not calculate price")

    # Создаем бронирование
    booking = create_booking(
        db=db,
        user_id=user.id,
        room_id=room_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        guests_count=guests,
        total_price=total_price
    )

    return {
        "success": True,
        "booking_id": booking.id,
        "message": "Бронирование успешно создано!"
    }


@router.get("/api/user/{telegram_id}/bookings")
async def get_user_all_bookings(telegram_id: int, db: Session = Depends(get_db)):
    """API-эндпоинт для получения всех бронирований пользователя"""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookings = get_user_bookings(db, user.id)
    return {
        "success": True,
        "bookings": [
            {
                "id": booking.id,
                "room_name": booking.room.name,
                "check_in": booking.check_in_date.strftime("%Y-%m-%d"),
                "check_out": booking.check_out_date.strftime("%Y-%m-%d"),
                "guests": booking.guests_count,
                "total_price": booking.total_price,
                "status": booking.status,
                "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for booking in bookings
        ]
    }