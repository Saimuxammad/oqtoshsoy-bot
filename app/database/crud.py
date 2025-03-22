from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import sqlite3
import os
import json

from app.database.models import User, Room, Booking, Review


# User-related functions
async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """Get a user by Telegram ID"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, telegram_id: int, username: Optional[str] = None,
                      first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
    """Create a new user"""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_user(db: AsyncSession, telegram_id: int, username: Optional[str] = None,
                             first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
    """Get a user by Telegram ID or create if not exists"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = await create_user(db, telegram_id, username, first_name, last_name)
    return user


# Room-related functions
async def get_all_rooms(db: AsyncSession) -> List[Room]:
    """Get all available rooms"""
    try:
        result = await db.execute(select(Room).order_by(Room.price_per_night))
        return result.scalars().all()
    except Exception as e:
        # Fallback to direct SQLite if SQLAlchemy fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting rooms with SQLAlchemy: {str(e)}")

        try:
            # Try to get rooms directly with SQLite
            from app.config import DATABASE_URL

            # Extract file path from SQLite URL
            if DATABASE_URL.startswith('sqlite:///'):
                db_path = DATABASE_URL[10:]
            else:
                db_path = DATABASE_URL

            # Make the path absolute
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)

            if not os.path.exists(db_path):
                logger.error(f"Database file not found at {db_path}")
                return []

            # Connect to database
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()

            # Query rooms
            cursor.execute("SELECT * FROM rooms ORDER BY price_per_night")
            rows = cursor.fetchall()

            # Convert rows to Room objects
            rooms = []
            for row in rows:
                room_dict = {key: row[key] for key in row.keys()}
                # Create Room object
                room = Room(
                    id=room_dict['id'],
                    name=room_dict['name'],
                    description=room_dict['description'],
                    room_type=room_dict['room_type'],
                    price_per_night=room_dict['price_per_night'],
                    capacity=room_dict['capacity'],
                    is_available=bool(room_dict['is_available']),
                    image_url=room_dict['image_url'],
                    photos=room_dict['photos'],
                    video_url=room_dict['video_url'],
                    amenities=room_dict['amenities']
                )
                rooms.append(room)

            conn.close()
            logger.info(f"Successfully fetched {len(rooms)} rooms directly with SQLite")
            return rooms

        except Exception as direct_error:
            logger.error(f"Error getting rooms with direct SQLite: {str(direct_error)}")
            return []


async def get_room(db: AsyncSession, room_id: int) -> Optional[Room]:
    """Get a room by ID"""
    result = await db.execute(select(Room).where(Room.id == room_id))
    return result.scalars().first()


async def get_room_reviews(db: AsyncSession, room_id: int) -> List[Review]:
    """Get reviews for a specific room"""
    result = await db.execute(
        select(Review)
        .where(Review.room_id == room_id)
        .order_by(desc(Review.created_at))
    )
    return result.scalars().all()


async def add_room_review(db: AsyncSession, user_id: int, room_id: int,
                          rating: int, comment: Optional[str] = None) -> Review:
    """Add a review for a room"""
    review = Review(
        user_id=user_id,
        room_id=room_id,
        rating=rating,
        comment=comment,
        created_at=datetime.now()
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


# Booking-related functions
async def create_booking(db: AsyncSession, user_id: int, room_id: int,
                         check_in: str, check_out: str, guests: int,
                         phone: Optional[str] = None) -> Booking:
    """Create a new booking"""
    # Convert date strings to date objects
    check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()

    # Check if dates are valid
    if check_out_date <= check_in_date:
        raise ValueError("Check-out date must be after check-in date")

    # Check if room is available for these dates
    is_available = await check_room_availability(db, room_id, check_in, check_out)
    if not is_available:
        raise ValueError("Room is not available for selected dates")

    # Get room to calculate price
    room = await get_room(db, room_id)
    if not room:
        raise ValueError("Room not found")

    # Calculate nights and total price
    nights = (check_out_date - check_in_date).days
    total_price = room.price_per_night * nights

    # Create booking
    booking = Booking(
        user_id=user_id,
        room_id=room_id,
        check_in=check_in_date,
        check_out=check_out_date,
        guests=guests,
        phone=phone,
        total_price=total_price,
        status="pending",
        created_at=datetime.now()
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def get_user_bookings(db: AsyncSession, user_id: int) -> List[Booking]:
    """Get all bookings for a user"""
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .order_by(desc(Booking.created_at))
    )
    return result.scalars().all()


async def get_booking(db: AsyncSession, booking_id: int) -> Optional[Booking]:
    """Get a booking by ID"""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    return result.scalars().first()


async def cancel_booking(db: AsyncSession, booking_id: int) -> Optional[Booking]:
    """Cancel a booking"""
    booking = await get_booking(db, booking_id)
    if not booking:
        return None

    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)
    return booking


async def calculate_booking_price(db: AsyncSession, room_id: int,
                                  check_in: str, check_out: str) -> Dict[str, Any]:
    """Calculate the total price for a booking"""
    room = await get_room(db, room_id)
    if not room:
        raise ValueError("Room not found")

    check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()

    nights = (check_out_date - check_in_date).days
    if nights <= 0:
        raise ValueError("Check-out date must be after check-in date")

    total_price = room.price_per_night * nights

    return {
        "total_price": total_price,
        "nights": nights,
        "room_price": room.price_per_night,
        "room_name": room.name
    }


async def check_room_availability(db: AsyncSession, room_id: int,
                                  check_in: str, check_out: str) -> bool:
    """Check if a room is available for the given dates"""
    check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()

    # Check for overlapping bookings
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.room_id == room_id,
                Booking.status != "cancelled",
                or_(
                    # New check-in date is during an existing booking
                    and_(
                        Booking.check_in <= check_in_date,
                        Booking.check_out > check_in_date
                    ),
                    # New check-out date is during an existing booking
                    and_(
                        Booking.check_in < check_out_date,
                        Booking.check_out >= check_out_date
                    ),
                    # New booking completely encompasses an existing booking
                    and_(
                        Booking.check_in >= check_in_date,
                        Booking.check_out <= check_out_date
                    )
                )
            )
        )
    )

    # If any overlapping booking exists, the room is not available
    return result.scalars().first() is None


async def get_available_rooms(db: AsyncSession, check_in: str, check_out: str) -> List[Room]:
    """Get rooms available for the given dates"""
    check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()

    # Get all rooms
    all_rooms = await get_all_rooms(db)

    # Filter out rooms that have overlapping bookings
    available_rooms = []
    for room in all_rooms:
        is_available = await check_room_availability(db, room.id, check_in, check_out)
        if is_available:
            available_rooms.append(room)

    return available_rooms


# Statistics and dashboard functions
async def get_booking_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get booking statistics"""
    # Total bookings
    total_bookings_result = await db.execute(select(func.count(Booking.id)))
    total_bookings = total_bookings_result.scalar_one()

    # Active bookings (pending or confirmed)
    active_bookings_result = await db.execute(
        select(func.count(Booking.id))
        .where(Booking.status.in_(["pending", "confirmed"]))
    )
    active_bookings = active_bookings_result.scalar_one()

    # Total revenue
    revenue_result = await db.execute(
        select(func.sum(Booking.total_price))
        .where(Booking.status != "cancelled")
    )
    total_revenue = revenue_result.scalar_one() or 0

    return {
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "cancelled_bookings": total_bookings - active_bookings,
        "total_revenue": total_revenue
    }