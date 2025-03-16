from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db, engine
from app.database.models import Base, User, Room, Booking, Review
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def seed_database():
    # Create tables first to ensure they exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if data already exists
        existing_rooms = db.query(Room).count()
        if existing_rooms > 0:
            logger.info("Database already contains data. Skipping test data creation.")
            return

        # Create sample rooms
        rooms = [
            Room(
                name="Стандартный номер",
                description="Уютный стандартный номер с видом на горы. В номере: двуспальная кровать, телевизор, кондиционер, мини-бар, ванная комната с душем.",
                room_type="standard",
                price_per_night=3000,
                capacity=2,
                image_url="https://images.unsplash.com/photo-1566195992011-5f6b21e539aa?q=80&w=1287&auto=format&fit=crop"
            ),
            Room(
                name="Люкс",
                description="Просторный номер люкс с панорамным видом на горный ландшафт. В номере: большая двуспальная кровать, гостиная зона с диваном, телевизор, кондиционер, мини-бар, ванная комната с джакузи.",
                room_type="luxury",
                price_per_night=5000,
                capacity=2,
                image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?q=80&w=1974&auto=format&fit=crop"
            ),
            Room(
                name="Семейный номер",
                description="Просторный номер для семейного отдыха. В номере: две спальни с двуспальными кроватями, гостиная, телевизор, кондиционер, мини-бар, ванная комната с душем.",
                room_type="family",
                price_per_night=7000,
                capacity=4,
                image_url="https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?q=80&w=2070&auto=format&fit=crop"
            ),
            Room(
                name="Президентский люкс",
                description="Эксклюзивный номер с максимальным комфортом и уединением. В номере: большая спальня с королевской кроватью, гостиная, кабинет, джакузи, сауна, терраса с видом на горы.",
                room_type="suite",
                price_per_night=12000,
                capacity=2,
                image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?q=80&w=2070&auto=format&fit=crop"
            )
        ]

        for room in rooms:
            db.add(room)

        db.commit()
        logger.info("Test data successfully added to database.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        # Initialize database (create tables)
        init_db()

        # Seed the database with test data
        seed_database()
    except Exception as e:
        logger.error(f"Error in seed_data.py: {e}")