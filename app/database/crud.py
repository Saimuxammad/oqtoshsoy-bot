from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple

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
    result = await db.execute(select(Room).order_by(Room.price_per_night))
    return result.scalars().all()


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