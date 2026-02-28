"""Configuration package."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/casewalker.db")

# Schedule (UTC)
MORNING_DIGEST_HOUR = int(os.getenv("MORNING_DIGEST_HOUR", "7"))
EVENING_DIGEST_HOUR = int(os.getenv("EVENING_DIGEST_HOUR", "19"))
PARSE_INTERVAL_MINUTES = int(os.getenv("PARSE_INTERVAL_MINUTES", "30"))
