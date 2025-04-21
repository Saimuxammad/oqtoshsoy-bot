import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from aiogram.types import Update

from app.config import BOT_TOKEN, HOST, PORT, WEBHOOK_URL, WEBAPP_URL
from app.database import init_db
# Import router from web routes but not bot yet
from app.bot.middleware import DatabaseMiddleware
from app.web.routes import router as web_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create bot and dispatcher outside lifespan to make them accessible
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

# Register middleware
dp.update.outer_middleware(DatabaseMiddleware())


# Create context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set webhook when application starts
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Bot webhook set to {WEBHOOK_URL}")
    logger.info(f"Web app URL is {WEBAPP_URL}")

    # Import and set up the router here
    from app.bot.handlers import router as bot_router
    if not any(router is bot_router for router in getattr(dp, "_sub_routers", [])):
        dp.include_router(bot_router)
        logger.info("Bot router registered")

    # Initialize database here to ensure it's done during startup
    await init_db()
    logger.info("Database initialized")

    yield

    # Close bot session when application stops
    await bot.session.close()
    logger.info("Bot session closed")


# Create FastAPI application
app = FastAPI(
    lifespan=lifespan,
    debug=True,
    docs_url="/docs",
    redoc_url="/redoc",
    title="Oqtoshsoy Hotel Booking API",
    description="API for Oqtoshsoy Hotel Telegram Bot and Web App",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include web router
app.include_router(web_router, prefix="")


# Webhook route handler for Telegram updates
@app.post("/webhook")
async def webhook(request: Request):
    update_data = await request.json()

    # Convert dict to Update object
    update = Update.model_validate(update_data)

    # Process the update
    await dp.feed_update(bot, update)

    return Response(status_code=200)


# Add root endpoint for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "Oqtoshsoy Hotel Bot API is running"}


@app.get("/app")
async def webapp():
    file_path = "app/web/templates/index.html"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    else:
        # Базовая HTML страница, если файл не найден
        logger.warning(f"Index.html file not found at {file_path}, using default template")
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Курорт Oqtoshsoy</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .rooms {
                    margin-top: 20px;
                }
                .room {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 15px;
                }
                .room h3 {
                    margin-top: 0;
                }
                .price {
                    font-weight: bold;
                    color: #2678b6;
                }
                .button {
                    background-color: #2678b6;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 5px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Курорт Oqtoshsoy</h1>
                <p>Добро пожаловать в систему бронирования нашего курорта!</p>

                <div class="rooms">
                    <div class="room">
                        <h3>Стандартный номер</h3>
                        <p>Уютный стандартный номер с видом на горы.</p>
                        <p class="price">3000₽ за ночь</p>
                        <button class="button" id="standard">Забронировать</button>
                    </div>

                    <div class="room">
                        <h3>Люкс</h3>
                        <p>Просторный номер люкс с отдельной гостиной.</p>
                        <p class="price">5000₽ за ночь</p>
                        <button class="button" id="lux">Забронировать</button>
                    </div>

                    <div class="room">
                        <h3>Семейный номер</h3>
                        <p>Большой номер для всей семьи.</p>
                        <p class="price">7000₽ за ночь</p>
                        <button class="button" id="family">Забронировать</button>
                    </div>
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const tgApp = window.Telegram.WebApp;
                    tgApp.expand();
                    tgApp.ready();

                    // Обработка клика по кнопкам
                    document.querySelectorAll('.button').forEach(button => {
                        button.addEventListener('click', function() {
                            tgApp.sendData(JSON.stringify({
                                action: 'book',
                                room_type: this.id
                            }));
                            tgApp.close();
                        });
                    });
                });
            </script>
        </body>
        </html>
        """)


# Эндпоинт для веб-приложения Telegram
@app.get("/webapp")
async def webapp_endpoint():
    """Эндпоинт для веб-приложения Telegram"""
    file_path = "app/web/templates/index.html"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    else:
        # Базовая HTML страница, если файл не найден
        logger.warning(f"Index.html file not found at {file_path}, using default template")
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Курорт Oqtoshsoy</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .rooms {
                    margin-top: 20px;
                }
                .room {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 15px;
                }
                .room h3 {
                    margin-top: 0;
                }
                .price {
                    font-weight: bold;
                    color: #2678b6;
                }
                .button {
                    background-color: #2678b6;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 5px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Курорт Oqtoshsoy</h1>
                <p>Добро пожаловать в систему бронирования нашего курорта!</p>

                <div class="rooms">
                    <div class="room">
                        <h3>Стандартный номер</h3>
                        <p>Уютный стандартный номер с видом на горы.</p>
                        <p class="price">3000₽ за ночь</p>
                        <button class="button" id="standard">Забронировать</button>
                    </div>

                    <div class="room">
                        <h3>Люкс</h3>
                        <p>Просторный номер люкс с отдельной гостиной.</p>
                        <p class="price">5000₽ за ночь</p>
                        <button class="button" id="lux">Забронировать</button>
                    </div>

                    <div class="room">
                        <h3>Семейный номер</h3>
                        <p>Большой номер для всей семьи.</p>
                        <p class="price">7000₽ за ночь</p>
                        <button class="button" id="family">Забронировать</button>
                    </div>
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const tgApp = window.Telegram.WebApp;
                    tgApp.expand();
                    tgApp.ready();

                    // Обработка клика по кнопкам
                    document.querySelectorAll('.button').forEach(button => {
                        button.addEventListener('click', function() {
                            tgApp.sendData(JSON.stringify({
                                action: 'book',
                                room_type: this.id
                            }));
                            tgApp.close();
                        });
                    });
                });
            </script>
        </body>
        </html>
        """)


# Диагностический эндпоинт для проверки веб-приложения
@app.get("/check-webapp")
async def check_webapp():
    """Диагностический эндпоинт для проверки веб-приложения"""
    try:
        import os
        from app.config import WEBAPP_URL

        file_path = "app/web/templates/index.html"
        file_exists = os.path.exists(file_path)

        file_content = None
        if file_exists:
            try:
                with open(file_path, "r") as f:
                    file_content = f.read(500) + "..."  # Первые 500 символов
            except Exception as e:
                file_content = f"Ошибка чтения файла: {str(e)}"

        return {
            "status": "ok",
            "webapp_url": WEBAPP_URL,
            "template_exists": file_exists,
            "template_path": os.path.abspath(file_path) if file_exists else None,
            "cwd": os.getcwd(),
            "template_preview": file_content,
            "telegram_js_included": "telegram-web-app.js" in (file_content or "")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/debug")
async def debug_info():
    """Debug endpoint to check paths and configuration"""
    template_path = "app/web/templates/index.html"
    content = None
    try:
        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                content = f.read()[:100] + "..."  # Show first 100 chars
    except Exception as e:
        content = f"Error reading file: {str(e)}"

    return {
        "webapp_url": WEBAPP_URL,
        "webhook_url": WEBHOOK_URL,
        "template_exists": os.path.exists(template_path),
        "template_path": template_path,
        "static_path_exists": os.path.exists("static"),
        "cwd": os.getcwd(),
        "directory_contents": os.listdir(),
        "template_preview": content
    }


# Reset database endpoint for development
@app.get("/reset-db")
async def reset_database():
    """Temporary endpoint to reset the database during development"""
    try:
        # Use force_recreate=True to drop and recreate tables with sample data
        await init_db(force_recreate=True)
        return {"status": "success",
                "message": "База данных oqtoshsoy.db успешно сброшена и заполнена тестовыми данными"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Add sample data endpoint
@app.get("/add-sample-data")
async def add_sample_data_endpoint():
    """Endpoint to add sample data to the database"""
    try:
        from app.database import add_sample_data
        await add_sample_data()
        return {"status": "success", "message": "Добавлены примеры номеров"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Direct database reset endpoint
@app.get("/direct-reset")
async def direct_reset():
    """Endpoint to directly reset and populate the database using raw SQLite"""
    import asyncio
    import os
    import sqlite3
    import json

    try:
        # 1. Delete existing database file if it exists
        from app.config import DATABASE_URL

        # Extract file path from SQLite URL
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL[10:]
        else:
            db_path = 'oqtoshsoy.db'  # Default fallback

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

        # Обновленная таблица rooms с дополнительными полями
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

        # Bookings table с полем admin_notified
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

        # 4. Добавляем обновленные номера
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
        return {"status": "success",
                "message": f"База данных успешно сброшена и заполнена {len(rooms)} номерами напрямую через SQLite"}

    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {"status": "error", "message": str(e)}


# Database info endpoint to diagnose issues
@app.get("/db-info")
async def db_info():
    """Get information about the database"""
    import os
    from app.config import DATABASE_URL

    # Extract file path from SQLite URL
    if DATABASE_URL.startswith('sqlite:///'):
        db_path = DATABASE_URL[10:]
    else:
        db_path = DATABASE_URL

    # Check if file exists
    exists = os.path.exists(db_path)

    # Get current working directory
    cwd = os.getcwd()

    # List files in the current directory
    try:
        files = os.listdir()
    except Exception as e:
        files = [f"Unable to list files: {str(e)}"]

    # Try to open and check tables in the database
    tables = []
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        tables = [f"Error accessing database: {str(e)}"]

    return {
        "database_url": DATABASE_URL,
        "db_path": db_path,
        "exists": exists,
        "cwd": cwd,
        "files": files,
        "tables": tables,
        "app_directory_structure": os.listdir("app") if os.path.exists("app") else ["app directory not found"]
    }


@app.get("/direct-reset-absolute")
async def direct_reset_absolute():
    """Endpoint to directly reset and populate the database using raw SQLite with absolute path"""
    import os
    import sqlite3
    import json

    try:
        # 1. Get the absolute path for the database
        from app.config import DATABASE_URL

        # Extract file path from SQLite URL
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL[10:]
        else:
            db_path = DATABASE_URL

        # Make the path absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)

        logger.info(f"Using absolute database path: {db_path}")

        # 2. Delete existing database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Deleted existing database file: {db_path}")

        # 3. Create a new database directly with SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 4. Create tables manually
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

        # Обновленная таблица rooms с дополнительными полями
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

        # Bookings table с полем admin_notified
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

        # 5. Добавляем обновленные номера
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

        # 6. Commit changes and close connection
        conn.commit()
        conn.close()

        # 7. Set permissions as permissive as possible
        try:
            import stat
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
            logger.info(f"Set permissive permissions on database file: {db_path}")
        except Exception as e:
            logger.warning(f"Could not set permissions on database file: {str(e)}")

        # 8. Verify the tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Database has been successfully reset with sample data. Tables: {tables}")
        return {
            "status": "success",
            "message": "База данных успешно сброшена и заполнена тестовыми данными напрямую через SQLite",
            "path": db_path,
            "tables": tables
        }

    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/fix-connection")
async def fix_connection():
    """Fix the database connection by updating the engine"""
    try:
        import sqlite3
        import os
        from sqlalchemy.ext.asyncio import create_async_engine
        import app.database

        # 1. Get the absolute path for the database
        from app.config import DATABASE_URL

        # Extract file path from SQLite URL
        if DATABASE_URL.startswith('sqlite:///'):
            db_path = DATABASE_URL[10:]
        else:
            db_path = DATABASE_URL

        # Make the path absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)

        # 2. Check if the database exists and has tables
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            if "rooms" in tables:
                # 3. Create a new engine with the correct path
                new_url = f"sqlite+aiosqlite:///{db_path}"
                try:
                    new_engine = create_async_engine(new_url, echo=False, future=True)

                    # 4. Try to update the module's engine
                    if hasattr(app.database, 'engine'):
                        app.database.engine = new_engine
                        logger.info(f"Successfully updated database engine to {new_url}")
                except Exception as e:
                    logger.error(f"Error creating new engine: {str(e)}")

                return {
                    "status": "success",
                    "message": "База данных успешно подключена",
                    "database_path": db_path,
                    "tables": tables,
                    "database_url": DATABASE_URL,
                    "new_url": new_url
                }
            else:
                return {
                    "status": "error",
                    "message": "База данных существует, но таблица 'rooms' не найдена",
                    "tables": tables
                }
        else:
            return {
                "status": "error",
                "message": f"База данных по пути {db_path} не существует"
            }

    except Exception as e:
        logger.error(f"Error in fix_connection: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/direct-rooms")
async def direct_rooms():
    """Get rooms directly from the database"""
    try:
        import sqlite3
        import os
        import json
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
            return {"status": "error", "message": f"Database file not found at {db_path}"}

        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()

        # Query rooms
        cursor.execute("SELECT * FROM rooms ORDER BY price_per_night")
        rows = cursor.fetchall()

        # Convert rows to list of dicts
        rooms = []
        for row in rows:
            room_dict = {key: row[key] for key in row.keys()}
            # Parse JSON fields
            if 'amenities' in room_dict and room_dict['amenities']:
                try:
                    room_dict['amenities'] = json.loads(room_dict['amenities'])
                except:
                    pass
            if 'photos' in room_dict and room_dict['photos']:
                try:
                    room_dict['photos'] = json.loads(room_dict['photos'])
                except:
                    pass
            rooms.append(room_dict)

        conn.close()

        return {"status": "success", "rooms": rooms}

    except Exception as e:
        logger.error(f"Error in direct_rooms: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/update-room-images")
async def update_room_images():
    """Update room images with valid URLs"""
    try:
        import sqlite3
        import os
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
            return {"status": "error", "message": f"Database file not found at {db_path}"}

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update with direct image URLs that work with Telegram
        image_updates = [
            (1, "https://i.imgur.com/ZXBtVw7.jpg"),  # Standard room
            (2, "https://i.imgur.com/Ecz64bK.jpg"),  # Luxury room
            (3, "https://i.imgur.com/nf1aE8m.jpg")  # Family room
        ]

        for room_id, image_url in image_updates:
            cursor.execute(
                "UPDATE rooms SET image_url = ? WHERE id = ?",
                (image_url, room_id)
            )

        # Commit and close
        conn.commit()
        conn.close()

        return {"status": "success", "message": "Room images updated with valid URLs"}

    except Exception as e:
        logger.error(f"Error updating room images: {str(e)}")
        return {"status": "error", "message": str(e)}

# Entry point for server startup
if __name__ == "__main__":
    import uvicorn

    # Start with reload=False until router issues are fixed
    uvicorn.run("main:app", host=HOST, port=8001, reload=False)