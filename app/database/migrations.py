from sqlalchemy import Column, String, Float, Text, MetaData, Table, inspect
from sqlalchemy.ext.declarative import declarative_base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_migrations(engine):
    """
    Функция для запуска всех миграций базы данных.
    """
    logger.info("Starting database migrations...")

    # Обновляем таблицу rooms
    update_rooms_table(engine)

    logger.info("Migrations completed successfully.")


def update_rooms_table(engine):
    """
    Добавляет новые поля в таблицу 'rooms'.
    """
    metadata = MetaData()
    inspector = inspect(engine)

    # Проверяем, существует ли таблица rooms
    if not inspector.has_table('rooms'):
        logger.warning("Table 'rooms' does not exist, skipping migration")
        return

    # Получаем информацию о существующих колонках
    columns = [col['name'] for col in inspector.get_columns('rooms')]

    # Подключаемся к существующей таблице
    rooms = Table('rooms', metadata, autoload_with=engine)

    # Список новых колонок для добавления
    new_columns = [
        {
            'name': 'price_with_food',
            'type': Float,
            'nullable': True
        },
        {
            'name': 'price_without_food_weekday',
            'type': Float,
            'nullable': True
        },
        {
            'name': 'price_without_food_weekend',
            'type': Float,
            'nullable': True
        },
        {
            'name': 'photos',
            'type': Text,
            'nullable': True
        },
        {
            'name': 'video_url',
            'type': String(500),
            'nullable': True
        },
        {
            'name': 'amenities',
            'type': Text,
            'nullable': True
        },
        {
            'name': 'check_in_time',
            'type': String(50),
            'nullable': True,
            'default': '14:00'
        },
        {
            'name': 'check_out_time',
            'type': String(50),
            'nullable': True,
            'default': '12:00'
        }
    ]

    # Добавляем колонки, если они еще не существуют
    with engine.begin() as conn:
        for column_info in new_columns:
            column_name = column_info['name']

            if column_name not in columns:
                column_type = column_info['type']
                nullable = column_info.get('nullable', True)
                default = column_info.get('default', None)

                # Формируем SQL-запрос для добавления колонки
                alter_stmt = f"ALTER TABLE rooms ADD COLUMN {column_name}"

                # Добавляем тип данных
                if isinstance(column_type, Float):
                    alter_stmt += " FLOAT"
                elif isinstance(column_type, Text):
                    alter_stmt += " TEXT"
                elif isinstance(column_type, String):
                    alter_stmt += f" VARCHAR({column_type.length})"

                # Добавляем NULL/NOT NULL
                if not nullable:
                    alter_stmt += " NOT NULL"

                # Добавляем DEFAULT, если указан
                if default is not None:
                    if isinstance(default, str):
                        alter_stmt += f" DEFAULT '{default}'"
                    else:
                        alter_stmt += f" DEFAULT {default}"

                # Выполняем запрос
                try:
                    conn.execute(alter_stmt)
                    logger.info(f"Added column '{column_name}' to table 'rooms'")
                except Exception as e:
                    logger.error(f"Error adding column '{column_name}': {e}")
                    raise

    logger.info("Room table migration completed")