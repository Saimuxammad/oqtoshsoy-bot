import asyncio
import os
import logging
import sqlite3
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("db_reset")


async def reset_database():
    """A direct script to reset the database completely"""
    try:
        # 1. Delete existing database file if it exists
        db_path = "oqtoshsoy.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Deleted existing database file: {db_path}")

        # 2. Create a new database directly with SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 3. Create tables manually
        # Users table
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Rooms table with all required columns
        cursor.execute('''
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            room_type TEXT NOT NULL,
            price_per_night REAL NOT NULL,
            weekend_price REAL,
            capacity INTEGER NOT NULL,
            is_available INTEGER DEFAULT 1,
            image_url TEXT,
            photos TEXT,
            video_url TEXT,
            amenities TEXT,
            meal_included INTEGER DEFAULT 1,
            with_breakfast INTEGER DEFAULT 1,
            season_type TEXT DEFAULT 'all'
        )
        ''')

        # Bookings table
        cursor.execute('''
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TIMESTAMP NOT NULL,
            check_out TIMESTAMP NOT NULL,
            guests INTEGER DEFAULT 1,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone TEXT,
            admin_notified INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
        ''')

        # Reviews table
        cursor.execute('''
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            room_id INTEGER,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
        ''')

        # 4. Add updated rooms data
        rooms = [
            # Стандартные номера
            (
                "Стандарт 2-х местный",
                "Уютный номер для двух человек с видом на горы. Включает все необходимое для комфортного отдыха.",
                "standard",
                700000,   # будни (ПН-ЧТ)
                900000,   # выходные (ПТ-ВС)
                2,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "TV", "Холодильник", "Кондиционер", "Душ"]),
                1,
                1,
                "all"
            ),
            (
                "Люкс 2-х местный",
                "Просторный номер люкс с отдельной гостиной для двух человек. Повышенный уровень комфорта.",
                "luxury",
                900000,   # будни
                1200000,  # выходные
                2,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "TV", "Холодильник", "Кондиционер", "Ванная", "Мини-бар"]),
                1,
                1,
                "all"
            ),
            (
                "Стандарт 4-х местный",
                "Номер с двумя спальнями для семьи или компании до 4 человек.",
                "standard",
                1200000,  # будни
                1500000,  # выходные
                4,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "TV", "Холодильник", "Кондиционер", "Душ", "Детская кроватка (по запросу)"]),
                1,
                1,
                "all"
            ),
            (
                "VIP малый 4-х местный",
                "Улучшенный номер для компании до 4 человек с дополнительными удобствами.",
                "vip",
                1300000,  # будни
                1700000,  # выходные
                4,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "Smart TV", "Холодильник", "Кондиционер", "Ванная", "Мини-кухня"]),
                1,
                1,
                "all"
            ),
            (
                "VIP большой 4-х местный",
                "Премиум номер для компании до 4 человек. Просторные комнаты с повышенным комфортом.",
                "vip",
                1600000,  # будни
                1900000,  # выходные
                4,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "Smart TV", "Холодильник", "Кондиционер", "Джакузи", "Мини-кухня", "Терраса"]),
                1,
                1,
                "all"
            ),
            (
                "Апартамент 4-х местный",
                "Апартаменты с отдельной гостиной и кухней для компании до 4 человек.",
                "apartment",
                1800000,  # будни
                2200000,  # выходные
                4,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "Smart TV", "Холодильник", "Кондиционер", "Ванная", "Полноценная кухня", "Гостиная"]),
                1,
                1,
                "all"
            ),
            (
                "Котедж 6-ти местный",
                "Отдельный коттедж для большой семьи или компании до 6 человек с собственной территорией.",
                "cottage",
                3000000,  # будни
                3500000,  # выходные
                6,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "Smart TV", "Холодильник", "Кондиционер", "Ванная", "Кухня", "Барбекю зона", "Терраса"]),
                1,
                1,
                "all"
            ),
            (
                "Президентский апартамент 8-ми местный",
                "Эксклюзивные апартаменты высшего уровня для компании до 8 человек с максимальным комфортом.",
                "president",
                3800000,  # будни
                4500000,  # выходные
                8,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                json.dumps(["Wi-Fi", "Smart TV", "Холодильник", "Кондиционер", "Джакузи", "Сауна", "Кухня", "Бильярд", "Терраса"]),
                1,
                1,
                "all"
            ),
            # Тапчаны
            (
                "Тапчан малый (7 местный)",
                "Традиционный тапчан под открытым небом для отдыха компанией до 7 человек.",
                "tapchan",
                300000,   # единая цена
                300000,   # та же цена
                7,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                json.dumps(["Зона для пикника", "Мангал (по запросу)", "Доступ к общей инфраструктуре"]),
                0,
                0,
                "all"
            ),
            (
                "Тапчан большой (15 местный)",
                "Большой тапчан для отдыха большой компанией до 15 человек.",
                "tapchan",
                500000,   # единая цена
                500000,   # та же цена
                15,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                json.dumps(["Зона для пикника", "Мангал (по запросу)", "Доступ к общей инфраструктуре"]),
                0,
                0,
                "all"
            )
        ]

        cursor.executemany('''
        INSERT INTO rooms (
            name, 
            description, 
            room_type, 
            price_per_night, 
            weekend_price, 
            capacity, 
            is_available, 
            image_url, 
            photos, 
            video_url, 
            amenities,
            meal_included,
            with_breakfast,
            season_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rooms)

        # 5. Commit changes and close connection
        conn.commit()
        conn.close()

        logger.info(f"Database has been successfully reset with {len(rooms)} rooms")
        return {"status": "success", "message": f"База данных успешно сброшена и заполнена {len(rooms)} номерами"}

    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {"status": "error", "message": str(e)}


# Run the script
if __name__ == "__main__":
    asyncio.run(reset_database())