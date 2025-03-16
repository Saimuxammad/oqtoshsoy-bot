import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import BOT_TOKEN, HOST, PORT, WEBHOOK_URL
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
    await dp.feed_webhook_update(bot, update_data)
    return Response(status_code=200)


# Add root endpoint for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "Oqtoshsoy Hotel Bot API is running"}

@app.get("/app")
async def webapp():
    return FileResponse("app/web/templates/index.html")

# Entry point for server startup
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)

from fastapi import Form, HTTPException
from app.database import crud


@app.get("/api/rooms")
async def get_rooms():
    try:
        # Get room data from database
        rooms = await crud.get_all_rooms()
        return {"success": True, "rooms": rooms}
    except Exception as e:
        logger.error(f"Error getting rooms: {e}")
        return {"success": False, "detail": str(e)}


@app.get("/api/user/{user_id}/bookings")
async def get_user_bookings(user_id: int):
    try:
        # Get user bookings from database
        bookings = await crud.get_user_bookings(user_id)
        return {"success": True, "bookings": bookings}
    except Exception as e:
        logger.error(f"Error getting bookings: {e}")
        return {"success": False, "detail": str(e)}


@app.post("/api/calculate-price")
async def calculate_price(request: Request):
    try:
        form_data = await request.form()
        room_id = int(form_data.get("room_id"))
        check_in = form_data.get("check_in")
        check_out = form_data.get("check_out")
        guests = int(form_data.get("guests"))

        # Calculate booking price
        price_info = await crud.calculate_booking_price(room_id, check_in, check_out)
        return {"success": True, "price": price_info["total_price"], "nights": price_info["nights"]}
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        return {"success": False, "detail": str(e)}


@app.post("/api/book")
async def create_booking(request: Request):
    try:
        form_data = await request.form()
        telegram_id = int(form_data.get("telegram_id"))
        room_id = int(form_data.get("room_id"))
        check_in = form_data.get("check_in")
        check_out = form_data.get("check_out")
        guests = int(form_data.get("guests"))
        phone = form_data.get("phone")

        # Create booking in database
        booking = await crud.create_booking(telegram_id, room_id, check_in, check_out, guests, phone)
        return {"success": True, "booking_id": booking.id}
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        return {"success": False, "detail": str(e)}