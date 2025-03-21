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
from app.bot.handlers import router as bot_router
from app.bot.middleware import DatabaseMiddleware
from app.web.routes import router as web_router

# Импортируем функцию инициализации дополнений
from app.initialize_extensions import initialize_extensions, check_database_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Create bot and dispatcher outside lifespan to make them accessible
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

# Register middleware
dp.update.outer_middleware(DatabaseMiddleware())

# Register bot router
dp.include_router(bot_router)


# Create context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set webhook when application starts
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Bot webhook set to {WEBHOOK_URL}")
    logger.info(f"Web app URL is {WEBAPP_URL}")

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

# Initialize extensions
initialize_extensions(app, dp)

# Check database tables
import asyncio
asyncio.create_task(check_database_tables())

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


# Entry point for server startup
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)