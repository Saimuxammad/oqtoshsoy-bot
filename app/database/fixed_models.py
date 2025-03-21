from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

# Create the declarative base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")

    def __repr__(self):
        return f"<User {self.first_name} {self.last_name}>"

class Room(Base):
    __tablename__ = "rooms"  # Важно добавить это!

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    room_type = Column(String(50), nullable=False)  # standard, luxury, suite
    price_per_night = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)
    # Новые поля, которые мы хотели добавить
    photos = Column(Text, nullable=True)  # JSON-массив URL фотографий
    video_url = Column(String(500), nullable=True)
    amenities = Column(Text, nullable=True)  # JSON-массив удобств в номере
    price_with_food = Column(Float, nullable=True)
    price_without_food_weekday = Column(Float, nullable=True)
    price_without_food_weekend = Column(Float, nullable=True)
    check_in_time = Column(String(50), default="14:00")
    check_out_time = Column(String(50), default="12:00")

    bookings = relationship("Booking", back_populates="room")
    reviews = relationship("Review", back_populates="room")

    def __repr__(self):
        return f"<Room {self.name}>"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime, nullable=False)
    guests = Column(Integer, default=1)
    total_price = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    phone = Column(String(20), nullable=True)

    user = relationship("User", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.id} - {self.status}>"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    room = relationship("Room", back_populates="reviews")

    def __repr__(self):
        return f"<Review {self.id} - {self.rating}>"