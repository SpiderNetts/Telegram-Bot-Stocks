# 📈 Stock Tracker Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21+-26A5E4?style=flat-square&logo=telegram)](https://github.com/python-telegram-bot/python-telegram-bot)
[![yfinance](https://img.shields.io/badge/Data-Yahoo%20Finance-purple?style=flat-square)](https://pypi.org/project/yfinance/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-lightblue?style=flat-square&logo=sqlite)](https://www.sqlite.org/)
[![Matplotlib](https://img.shields.io/badge/Charts-Matplotlib-11557c?style=flat-square)](https://matplotlib.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-informational?style=flat-square)](#)

**A personal Telegram bot that tracks up to 5 stocks per user, sends live price + chart updates on demand, and pings you automatically on your own schedule.**

---

## ✨ Features

- 📊 **Personal watchlist** — each user tracks up to 5 tickers of their choice
- 💬 **On-demand commands** — instant price checks, full snapshots, and charts
- 📈 **Selectable chart timeframes** — Last Hour, Today, 1 Week, 1 Month, or 3 Months, picked with a tap
- 🔔 **All-stocks notifications** — auto-updates for your whole watchlist every 5 min / 10 min / 30 min / 1 hour / 3 hours
- 🎯 **Per-stock price alerts** — track one specific stock's ups and downs on its own independent schedule
- 🕒 **`/all` live snapshot** — price, day range, volume, and timestamp for every tracked stock in one message
- 💾 **SQLite database** — fully local, no external database server required
- 🖼️ **Auto-generated chart images** — rendered fresh with Matplotlib on every request
- 🌐 **Free market data** — powered by Yahoo Finance via `yfinance`, no API key required

---

## 🛠️ Run from Source Code

> Requires Python 3.10+

**Step 1 — Make sure Python is installed**

Download from [python.org](https://www.python.org/) — during install, check the box **Add Python to PATH**

**Step 2 — Clone the repo**

```
git clone https://github.com/YOUR-USERNAME/stock-tracker-bot
cd stock-tracker-bot
```

**Step 3 — Install dependencies**

```
pip install -r requirements.txt
```

**Step 4 — Get a Telegram bot token**

1. Open Telegram and message [**@BotFather**](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token it gives you

**Step 5 — Add your token**

Either set it as an environment variable:

```
export TELEGRAM_BOT_TOKEN="123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

or paste it directly into `config.py`:

```python
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")
```

**Step 6 — Run the bot**

```
python bot.py
```

Open a chat with your bot on Telegram and send `/start` ✅

---

## 🔑 How It Works

```
First launch
  │
  ▼
🔑 Bot token loaded from config.py / env var
  │
  ▼
💾 SQLite database created automatically (stocks_bot.db)
  │
  ▼
👤 User sends /start
  │
  ▼
➕ User adds up to 5 tickers with /add <TICKER>
  │
  ├── /list, /all, /price, /chart  → on-demand data, anytime
  │
  └── /setinterval → choose notification mode
        │
        ├── 📊 All stocks  → one interval, whole watchlist, price + chart
        │
        └── 🎯 Single stock → pick a ticker + interval, up/down price alerts
```

---

## 💬 Commands

| Command | What it does |
|---|---|
| `/start` | Welcome message + full command list |
| `/add <TICKER>` | Add a stock to your watchlist (max 5) |
| `/remove <TICKER>` | Remove a stock |
| `/list` | Quick view of your watchlist with current prices |
| `/all` | Full live snapshot of every stock — price, day range, volume, timestamp |
| `/price <TICKER>` | Current price + change for one ticker |
| `/chart <TICKER>` | Pick a timeframe, then get a chart image |
| `/setinterval` | Set up all-stocks notifications or a single-stock price alert |
| `/myinterval` | Check your current notification settings |
| `/removealert <TICKER>` | Remove a single-stock price alert |
| `/help` | Show the command list again |

---

## 🔔 Notification Modes

| Mode | Frequency options | What you get |
|---|---|---|
| 📊 All stocks | 5 min / 10 min / 30 min / 1 hour / 3 hours | Price + chart for your **entire** watchlist |
| 🎯 Single stock alert | 5 min / 10 min / 30 min / 1 hour / 3 hours | Just that stock's price + whether it went **up or down** since the last check |

You can run an all-stocks notification *and* multiple independent per-stock alerts at the same time.

---

## 📊 Chart Timeframes

| Button | Range | Candle size |
|---|---|---|
| Last Hour | Last 60 minutes | 5 min |
| Today | Full trading day | 5 min |
| 1 Week | Last 5 trading days | 15 min |
| 1 Month | Last month | Daily |
| 3 Months | Last 3 months | Daily |

---

## 📦 Dependencies

```
python-telegram-bot[job-queue]  — Telegram bot framework + scheduler
yfinance                        — Free live/near-real-time market data
matplotlib                      — Chart rendering
pandas                          — Price history handling
```

---

## 📌 Important Notes

- All data is stored **locally** in `stocks_bot.db` — nothing sent anywhere except to Telegram and Yahoo Finance to fetch prices
- Free market data via `yfinance` is typically delayed a few minutes — true tick-level real-time data requires a paid provider
- **Do not delete** `stocks_bot.db` — it holds every user's watchlist and notification settings
- The bot only runs while the Python process is running — see the deployment notes below to keep it online 24/7
- This project is for personal and educational use

---

## ☁️ Keeping It Running 24/7

Running `python bot.py` in a terminal stops the bot the moment you close that window. For always-on operation:

- **Windows Task Scheduler** — run it at startup with auto-restart on failure
- **Small VPS** (DigitalOcean, Hetzner, Oracle Free Tier) + `systemd` — the standard way to self-host reliably
- **Railway / Render** — push-to-deploy platforms that keep a background worker alive

---

Made with 📈 and Python
