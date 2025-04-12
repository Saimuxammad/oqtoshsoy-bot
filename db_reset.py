import asyncio
import os
import logging
import sqlite3

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
            capacity INTEGER NOT NULL,
            is_available INTEGER DEFAULT 1,
            image_url TEXT,
            photos TEXT,
            video_url TEXT,
            amenities TEXT
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

        # 4. Add sample rooms data with full list of rooms
        rooms = [
            (
                "Стандарт - 2х местный",
                "Уютный номер с видом на горы. Включает завтрак и доступ к детской площадке.",
                "standard",
                700000,
                2,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник"]'
            ),
            (
                "Люкс - 2х местный",
                "Просторный номер с дополнительными удобствами. Включает завтрак и доступ к детской площадке.",
                "luxury",
                900000,
                2,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
            ),
            (
                "Стандарт - 4х местный",
                "Просторный номер для семьи или компании. Включает завтрак и доступ к детской площадке.",
                "standard_family",
                1200000,
                4,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Детская кроватка"]'
            ),
            (
                "VIP малый - 4х местный",
                "Комфортабельный номер с улучшенной отделкой. Включает завтрак и доступ к детской площадке.",
                "vip_small",
                1300000,
                4,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
            ),
            (
                "VIP большой - 4х местный",
                "Просторный номер категории VIP с панорамным видом на горы. Включает завтрак и доступ к детской площадке.",
                "vip_large",
                1600000,
                4,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Джакузи", "Мини-бар"]'
            ),
            (
                "Апартамент - 4х местный",
                "Элитный номер с отдельной гостиной. Включает завтрак и доступ к детской площадке.",
                "apartment",
                1800000,
                4,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Джакузи", "Кухня"]'
            ),
            (
                "Котедж - 6 местный",
                "Отдельный коттедж с собственной территорией. Включает завтрак и доступ к детской площадке.",
                "cottage",
                3000000,
                6,
                1,
                "https://i.imgur.com/nf1aE8m.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Кухня", "Барбекю"]'
            ),
            (
                "Президентский апартамент - 8 местный",
                "Эксклюзивные апартаменты с максимальным комфортом. Включает завтрак и доступ к детской площадке.",
                "presidential",
                3800000,
                8,
                1,
                "https://i.imgur.com/Ecz64bK.jpg",
                "[]",
                None,
                '["Wi-Fi", "TV", "Холодильник", "Джакузи", "Кухня", "Сауна"]'
            ),
            (
                "Тапчан маленький - 7 местный",
                "Уютный тапчан для отдыха на свежем воздухе. Идеально для групп.",
                "tapshan_small",
                150000,
                7,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                '[]'
            ),
            (
                "Тапчан большой - 15 местный",
                "Большой тапчан для больших компаний. Комфортный отдых на природе.",
                "tapshan_large",
                300000,
                15,
                1,
                "https://i.imgur.com/ZXBtVw7.jpg",
                "[]",
                None,
                '[]'
            )
        ]

        cursor.executemany('''
        INSERT INTO rooms (name, description, room_type, price_per_night, capacity, is_available, image_url, photos, video_url, amenities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rooms)

        # 5. Commit changes and close connection
        conn.commit()
        conn.close()

        logger.info("Database has been successfully reset with sample data")
        return {"status": "success", "message": "Database has been reset and populated with sample data"}

    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {"status": "error", "message": str(e)}


# Run the script
if __name__ == "__main__":
    asyncio.run(reset_database())