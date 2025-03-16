import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import BOT_TOKEN, HOST, PORT
from app.database import init_db
from app.bot.handlers import router as bot_router
from app.bot.middleware import DatabaseMiddleware
from app.web.routes import router as web_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Create context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start bot when application starts
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.update.outer_middleware(DatabaseMiddleware())

    # Register bot router
    dp.include_router(bot_router)

    # Start polling in separate task
    asyncio.create_task(dp.start_polling(bot))
    logger.info("Bot started polling")

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

# Add root endpoint for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "Oqtoshsoy Hotel Bot API is running"}

# Entry point for server startup
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)