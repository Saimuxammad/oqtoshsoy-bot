import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://web-production-1c8d.up.railway.app/app")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://web-production-1c8d.up.railway.app/webhook")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///oqtoshsoy.db")

# Web App
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))