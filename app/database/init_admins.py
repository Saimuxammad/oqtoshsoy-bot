from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.database.models import User
from app.database.additional_models import BotAdmin
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def init_admin_users():
    """
    Инициализирует администраторов бота.
    Берет ID администраторов из переменной окружения ADMIN_IDS в формате comma-separated.
    Первый ID в списке становится суперадмином.
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        logger.warning("No admin IDs specified in ADMIN_IDS environment variable")
        return

    try:
        # Разбиваем строку с ID на список
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
        if not admin_ids:
            logger.warning("No valid admin IDs found in ADMIN_IDS environment variable")
            return

        # Инициализируем сессию с базой данных
        db = SessionLocal()

        try:
            # Проверяем наличие администраторов в базе
            existing_admins = db.query(BotAdmin).all()
            existing_admin_ids = [admin.telegram_id for admin in existing_admins]

            for i, telegram_id in enumerate(admin_ids):
                # Пропускаем, если администратор уже существует
                if telegram_id in existing_admin_ids:
                    logger.info(f"Admin with Telegram ID {telegram_id} already exists")
                    continue

                # Проверяем, существует ли пользователь с таким Telegram ID
                user = db.query(User).filter(User.telegram_id == telegram_id).first()

                # Если пользователь не существует, создаем его
                if not user:
                    user = User(
                        telegram_id=telegram_id,
                        username=f"admin_{telegram_id}",
                        first_name="Admin",
                        last_name=str(telegram_id)
                    )
                    db.add(user)
                    db.flush()
                    logger.info(f"Created user for admin with Telegram ID {telegram_id}")

                # Создаем администратора
                admin = BotAdmin(
                    user_id=user.id,
                    telegram_id=telegram_id,
                    is_superadmin=(i == 0),  # Первый в списке становится суперадмином
                    can_manage_rooms=True,
                    can_manage_bookings=True,
                    can_manage_services=True
                )

                db.add(admin)
                logger.info(f"Added admin with Telegram ID {telegram_id}, is_superadmin: {i == 0}")

            db.commit()
            logger.info(f"Successfully initialized {len(admin_ids)} admin users")

        except Exception as e:
            db.rollback()
            logger.error(f"Error initializing admin users: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error parsing admin IDs: {e}")


if __name__ == "__main__":
    try:
        # Инициализируем базу данных
        init_db()

        # Инициализируем администраторов
        init_admin_users()
    except Exception as e:
        logger.error(f"Error in init_admins.py: {e}")