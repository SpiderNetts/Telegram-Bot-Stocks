"""
Configuration for the Stock Tracker Telegram Bot.

Set your bot token either by:
  1. Exporting an environment variable before running the bot:
       export TELEGRAM_BOT_TOKEN="123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  2. Or simply pasting it directly below where it says "PASTE_YOUR_TOKEN_HERE".
"""

import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "past your token here")

MAX_STOCKS_PER_USER = 5


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks_bot.db")

INTERVALS = {
    "5 min": 300,
    "10 min": 600,
    "30 min": 1800,
    "1 hour": 3600,
    "3 hours": 10800,
}

SCHEDULER_TICK_SECONDS = 60

TIMEFRAMES = {
    "1H": {"label": "Last Hour",  "period": "1d",  "interval": "5m",  "last_n": 12},
    "1D": {"label": "Today",      "period": "1d",  "interval": "5m",  "last_n": None},
    "1W": {"label": "1 Week",     "period": "5d",  "interval": "15m", "last_n": None},
    "1M": {"label": "1 Month",    "period": "1mo", "interval": "1d",  "last_n": None},
    "3M": {"label": "3 Months",   "period": "3mo", "interval": "1d",  "last_n": None},
}

DEFAULT_NOTIFY_TIMEFRAME = "1D"

CHART_PERIOD = "1mo"
CHART_INTERVAL = "1d"