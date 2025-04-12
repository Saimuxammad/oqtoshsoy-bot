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

        # Create sample rooms - обновлено с полным списком номеров согласно прайсу
        rooms = [
            Room(
                name="Стандарт - 2х местный",
                description="Уютный номер с видом на горы. Включает завтрак и доступ к детской площадке.",
                room_type="standard",
                price_per_night=700000,  # Цена ПН-ЧТ в сумах
                capacity=2,
                image_url="https://i.imgur.com/ZXBtVw7.jpg"
            ),
            Room(
                name="Люкс - 2х местный",
                description="Просторный номер с дополнительными удобствами. Включает завтрак и доступ к детской площадке.",
                room_type="luxury",
                price_per_night=900000,  # Цена ПН-ЧТ в сумах
                capacity=2,
                image_url="https://i.imgur.com/Ecz64bK.jpg"
            ),
            Room(
                name="Стандарт - 4х местный",
                description="Просторный номер для семьи или компании. Включает завтрак и доступ к детской площадке.",
                room_type="standard_family",
                price_per_night=1200000,  # Цена ПН-ЧТ в сумах
                capacity=4,
                image_url="https://i.imgur.com/nf1aE8m.jpg"
            ),
            Room(
                name="VIP малый - 4х местный",
                description="Комфортабельный номер с улучшенной отделкой. Включает завтрак и доступ к детской площадке.",
                room_type="vip_small",
                price_per_night=1300000,  # Цена ПН-ЧТ в сумах
                capacity=4,
                image_url="https://i.imgur.com/Ecz64bK.jpg"
            ),
            Room(
                name="VIP большой - 4х местный",
                description="Просторный номер категории VIP с панорамным видом на горы. Включает завтрак и доступ к детской площадке.",
                room_type="vip_large",
                price_per_night=1600000,  # Цена ПН-ЧТ в сумах
                capacity=4,
                image_url="https://i.imgur.com/Ecz64bK.jpg"
            ),
            Room(
                name="Апартамент - 4х местный",
                description="Элитный номер с отдельной гостиной. Включает завтрак и доступ к детской площадке.",
                room_type="apartment",
                price_per_night=1800000,  # Цена ПН-ЧТ в сумах
                capacity=4,
                image_url="https://i.imgur.com/nf1aE8m.jpg"
            ),
            Room(
                name="Котедж - 6 местный",
                description="Отдельный коттедж с собственной территорией. Включает завтрак и доступ к детской площадке.",
                room_type="cottage",
                price_per_night=3000000,  # Цена ПН-ЧТ в сумах
                capacity=6,
                image_url="https://i.imgur.com/nf1aE8m.jpg"
            ),
            Room(
                name="Президентский апартамент - 8 местный",
                description="Эксклюзивные апартаменты с максимальным комфортом. Включает завтрак и доступ к детской площадке.",
                room_type="presidential",
                price_per_night=3800000,  # Цена ПН-ЧТ в сумах
                capacity=8,
                image_url="https://i.imgur.com/Ecz64bK.jpg"
            ),
            Room(
                name="Тапчан маленький - 7 местный",
                description="Уютный тапчан для отдыха на свежем воздухе. Идеально для групп.",
                room_type="tapshan_small",
                price_per_night=150000,  # Примерная цена
                capacity=7,
                image_url="https://i.imgur.com/ZXBtVw7.jpg"
            ),
            Room(
                name="Тапчан большой - 15 местный",
                description="Большой тапчан для больших компаний. Комфортный отдых на природе.",
                room_type="tapshan_large",
                price_per_night=300000,  # Примерная цена
                capacity=15,
                image_url="https://i.imgur.com/ZXBtVw7.jpg"
            )
        ]

        for room in rooms:
            db.add(room)

        db.commit()
        logger.info("Тестовые данные успешно добавлены в базу данных.")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании тестовых данных: {e}")
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