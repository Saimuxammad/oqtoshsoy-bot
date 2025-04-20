import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://web-production-1c8d.up.railway.app/webapp")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://web-production-1c8d.up.railway.app/webhook")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")  # ID администратора для уведомлений

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///oqtoshsoy.db")

# Web App
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))

# Курорт
RESORT_NAME = "Oqtoshsoy"
RESORT_LOCATION = "Ташкентская область, Бостанлыкский район"
RESORT_ALTITUDE = "1200 м"
RESORT_PHONE = "+99890 096 50 55"
RESORT_ADMIN_USERNAME = "Oqtosh_Soy"