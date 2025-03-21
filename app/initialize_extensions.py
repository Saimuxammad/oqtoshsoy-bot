"""
Модуль для инициализации всех дополнительных компонентов и расширений.
Должен быть импортирован и запущен в main.py перед запуском приложения.
"""

import logging
from fastapi import FastAPI
from aiogram import Dispatcher
from sqlalchemy import inspect

from app.database import engine
from app.database.migrations import run_migrations
from app.database.init_admins import init_admin_users
from app.database.seed_services import seed_additional_services
from app.database.room_updates import update_room_model
from app.web.additional_routes import router as additional_router
from app.bot.additional_handlers import register_additional_handlers

logger = logging.getLogger(__name__)


def initialize_extensions(app: FastAPI, dispatcher: Dispatcher):
    """
    Инициализирует все дополнительные компоненты и расширения.

    Args:
        app: FastAPI экземпляр приложения
        dispatcher: Aiogram диспетчер
    """
    logger.info("Initializing extensions...")

    # Запускаем миграции базы данных
    try:
        run_migrations(engine)
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")

    # Обновляем модель Room
    try:
        update_room_model()
        logger.info("Room model updated")
    except Exception as e:
        logger.error(f"Error updating Room model: {e}")

    # Инициализируем администраторов бота
    try:
        init_admin_users()
        logger.info("Bot administrators initialized")
    except Exception as e:
        logger.error(f"Error initializing bot administrators: {e}")

    # Добавляем дополнительные услуги в базу данных
    try:
        seed_additional_services()
        logger.info("Additional services seeded")
    except Exception as e:
        logger.error(f"Error seeding additional services: {e}")

    # Регистрируем дополнительные обработчики бота
    try:
        register_additional_handlers(dispatcher)
        logger.info("Additional bot handlers registered")
    except Exception as e:
        logger.error(f"Error registering additional bot handlers: {e}")

    # Включаем дополнительные маршруты API
    try:
        app.include_router(additional_router, prefix="")
        logger.info("Additional API routes included")
    except Exception as e:
        logger.error(f"Error including additional API routes: {e}")

    # Добавляем новые маршруты для веб-приложения
    try:
        from fastapi.responses import HTMLResponse
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="app/web/templates")

        @app.get("/app/services", response_class=HTMLResponse)
        async def services_page(request: FastAPI.request):
            return templates.TemplateResponse("services.html", {"request": request})

        @app.get("/app/admin/calendar", response_class=HTMLResponse)
        async def calendar_page(request: FastAPI.request):
            return templates.TemplateResponse("calendar.html", {"request": request})

        logger.info("Additional web routes added")
    except Exception as e:
        logger.error(f"Error adding additional web routes: {e}")

    logger.info("Extensions initialization completed")


def check_database_tables():
    """
    Проверяет наличие всех необходимых таблиц в базе данных.
    Выводит информацию о текущем состоянии базы данных.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"Database tables: {tables}")

    # Проверяем наличие основных таблиц
    required_tables = [
        "users", "rooms", "bookings", "reviews",
        "additional_services", "service_bookings", "bot_admins", "payments"
    ]

    missing_tables = [table for table in required_tables if table not in tables]

    if missing_tables:
        logger.warning(f"Missing tables: {missing_tables}")
    else:
        logger.info("All required tables are present")

    # Выводим структуру существующих таблиц
    for table in tables:
        columns = inspector.get_columns(table)
        logger.debug(f"Table '{table}' columns: {[col['name'] for col in columns]}")