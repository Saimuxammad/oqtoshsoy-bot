import os
from dotenv import load_dotenv
from db_config import get_safe_database_url

# Load .env file
load_dotenv()
# In app/config.py
WEBHOOK_URL = "https://web-production-1c8d.up.railway.app/webhook"
# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Database configuration
DATABASE_URL = get_safe_database_url()

# Web App
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))