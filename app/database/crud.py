from sqlalchemy.orm import Session
from app.database.models import User, Room, Booking, Review
import datetime

# Функции для работы с пользователями
def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db: Session, telegram_id: int, username: str = None, full_name: str = None):
    db_user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_phone(db: Session, telegram_id: int, phone_number: str):
    db_user = get_user_by_telegram_id(db, telegram_id)
    if db_user:
        db_user.phone_number = phone_number
        db.commit()
        db.refresh(db_user)
    return db_user

# Функции для работы с номерами
def get_all_rooms(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Room).offset(skip).limit(limit).all()

def get_room(db: Session, room_id: int):
    return db.query(Room).filter(Room.id == room_id).first()

def get_available_rooms(db: Session, check_in: datetime.datetime, check_out: datetime.datetime):
    # Сложный запрос для получения доступных номеров в заданном диапазоне дат
    # Здесь можно использовать более сложную логику с фильтрацией по существующим бронированиям
    return db.query(Room).filter(Room.is_available == True).all()

# Функции для работы с бронированиями
def create_booking(db: Session, user_id: int, room_id: int,
                   check_in_date: datetime.datetime, check_out_date: datetime.datetime,
                   guests_count: int, total_price: float):
    db_booking = Booking(
        user_id=user_id,
        room_id=room_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        guests_count=guests_count,
        total_price=total_price
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def get_user_bookings(db: Session, user_id: int):
    return db.query(Booking).filter(Booking.user_id == user_id).all()

def update_booking_status(db: Session, booking_id: int, status: str):
    db_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if db_booking:
        db_booking.status = status
        db.commit()
        db.refresh(db_booking)
    return db_booking

# Функции для работы с отзывами
def create_review(db: Session, user_id: int, room_id: int, rating: int, comment: str = None):
    db_review = Review(user_id=user_id, room_id=room_id, rating=rating, comment=comment)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

def get_room_reviews(db: Session, room_id: int):
    return db.query(Review).filter(Review.room_id == room_id).all()