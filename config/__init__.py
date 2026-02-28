"""Configuration package."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# Admin chat IDs (comma-separated) - for receiving user messages and notifications
ADMIN_CHAT_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_CHAT_IDS", "").split(",")
    if x.strip().isdigit()
]

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/casewalker.db")

# Schedule (UTC)
MORNING_DIGEST_HOUR = int(os.getenv("MORNING_DIGEST_HOUR", "7"))
EVENING_DIGEST_HOUR = int(os.getenv("EVENING_DIGEST_HOUR", "19"))
PARSE_INTERVAL_MINUTES = int(os.getenv("PARSE_INTERVAL_MINUTES", "30"))
