from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.database.models import Base
from app.database.additional_models import AdditionalService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def seed_additional_services():
    """Заполнение базы данных дополнительными услугами"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже услуги в базе
        existing_services = db.query(AdditionalService).count()
        if existing_services > 0:
            logger.info("В базе данных уже есть дополнительные услуги. Пропускаем заполнение.")
            return

        # Создаем дополнительные услуги на основе прайс-листа
        services = [
            AdditionalService(
                name="Сауна",
                description="Финская сауна с купелью. Идеальное место для релаксации после активного дня.",
                price=200000,
                is_hourly=True,
                max_capacity=6,
                image_url="https://images.unsplash.com/photo-1554679665-f5537f187268?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Крытый бассейн",
                description="Крытый бассейн с подогревом. Размер: 10x5 м, глубина: 1.2-1.8 м.",
                price=150000,
                is_hourly=True,
                max_capacity=10,
                image_url="https://images.unsplash.com/photo-1572028412480-0a75271c6bb6?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Топчан (место для отдыха)",
                description="Комфортное крытое место для отдыха с матрасами и подушками.",
                price=100000,
                is_hourly=False,
                max_capacity=4,
                image_url="https://images.unsplash.com/photo-1540541338287-41700207dee6?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Дополнительная кровать",
                description="Дополнительная односпальная кровать для комнаты. Устанавливается по запросу.",
                price=300000,
                is_hourly=False,
                max_capacity=1,
                image_url="https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Экскурсия по территории",
                description="Групповая экскурсия по территории курорта с посещением солевой пещеры и исторических мест.",
                price=500000,
                is_hourly=False,
                max_capacity=5,
                image_url="https://images.unsplash.com/photo-1528127269322-539801943592?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Солевая пещера",
                description="Сеанс в солевой пещере. Посещение солевой пещеры помогает при заболеваниях дыхательных путей и кожи.",
                price=120000,
                is_hourly=True,
                max_capacity=4,
                image_url="https://images.unsplash.com/photo-1544161515-4ab6ce6db874?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            ),
            AdditionalService(
                name="Детская игровая комната",
                description="Детская игровая комната с аниматором для детей от 3 до 12 лет.",
                price=100000,
                is_hourly=True,
                max_capacity=8,
                image_url="https://images.unsplash.com/photo-1545558014-8692077e9b5c?q=80&w=2070&auto=format&fit=crop",
                is_available=True
            )
        ]

        for service in services:
            db.add(service)

        db.commit()
        logger.info(f"Добавлено {len(services)} дополнительных услуг в базу данных.")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при заполнении базы данных дополнительными услугами: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        # Заполняем базу данных дополнительными услугами
        seed_additional_services()
    except Exception as e:
        logger.error(f"Ошибка в seed_services.py: {e}")