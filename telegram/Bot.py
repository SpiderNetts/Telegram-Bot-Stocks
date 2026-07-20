"""
Telegram Stock Tracker Bot
===========================
Commands:
  /start                 Welcome message + instructions
  /help                  Show help
  /add <TICKER>          Add a stock to your watchlist (max 5)
  /remove <TICKER>       Remove a stock from your watchlist
  /list                  Show your current watchlist (quick view)
  /all                   Show ALL your stocks with full up-to-date detail
  /price <TICKER>        Get current price + change for one ticker
  /chart <TICKER>        Choose a timeframe, then get a price chart image
  /setinterval           Set up "all stocks" or "single stock" notifications
  /myinterval            Show your current notification settings
  /removealert <TICKER>  Remove a single-stock price alert

Run:
  python bot.py
"""

import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import config
import database as db
import stock_service
from chart_generator import generate_chart

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def format_price_line(snapshot: dict) -> str:
    arrow = "🟢▲" if snapshot["change"] >= 0 else "🔴▼"
    sign = "+" if snapshot["change"] >= 0 else ""
    return (
        f"*{snapshot['ticker']}*: ${snapshot['price']:.2f}  "
        f"{arrow} {sign}{snapshot['change']:.2f} ({sign}{snapshot['change_pct']:.2f}%)"
    )


def format_detail_block(snapshot: dict) -> str:
    """Richer per-stock block used by /all."""
    header = format_price_line(snapshot)
    ts = snapshot["timestamp"].strftime("%Y-%m-%d %H:%M")
    return (
        f"{header}\n"
        f"   Day range: ${snapshot['day_low']:.2f} – ${snapshot['day_high']:.2f}  "
        f"| Vol: {snapshot['volume']:,}\n"
        f"   As of: {ts}"
    )


def interval_label(seconds: int) -> str:
    return next((k for k, v in config.INTERVALS.items() if v == seconds), f"{seconds}s")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.ensure_user(update.effective_user.id)
    await update.message.reply_text(
        "👋 *Welcome to Stock Tracker Bot! (created by SpiderNetts)*\n\n"
        "I track up to 5 stocks for you and can send you price + chart "
        "updates automatically.\n\n"
        "*Commands:*\n"
        "/add <TICKER> — add a stock (e.g. /add AAPL)\n"
        "/remove <TICKER> — remove a stock\n"
        "/list — quick view of your watchlist\n"
        "/all — full up-to-date detail on all your stocks\n"
        "/price <TICKER> — current price\n"
        "/chart <TICKER> — pick a timeframe and get a chart\n"
        "/setinterval — set up notifications (all stocks or a single one)\n"
        "/myinterval — check your current notification settings\n"
        "/removealert <TICKER> — remove a single-stock alert\n"
        "/help — show this again",
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add <TICKER>  (e.g. /add TSLA)")
        return

    ticker = context.args[0].upper().strip()
    await update.message.reply_chat_action("typing")

    if not stock_service.validate_ticker(ticker):
        await update.message.reply_text(
            f"❌ Couldn't find a ticker called '{ticker}'. Check the symbol and try again."
        )
        return

    success, message = db.add_stock(update.effective_user.id, ticker)
    prefix = "✅" if success else "⚠️"
    await update.message.reply_text(f"{prefix} {message}")


async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /remove <TICKER>  (e.g. /remove TSLA)")
        return

    ticker = context.args[0].upper().strip()
    removed = db.remove_stock(update.effective_user.id, ticker)
    if removed:
        await update.message.reply_text(f"🗑️ Removed {ticker} from your watchlist.")
    else:
        await update.message.reply_text(f"{ticker} wasn't in your watchlist.")


async def list_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = db.get_stocks(update.effective_user.id)
    if not tickers:
        await update.message.reply_text(
            "Your watchlist is empty. Add a stock with /add <TICKER>."
        )
        return

    await update.message.reply_chat_action("typing")
    lines = ["📋 *Your Watchlist:*\n"]
    for ticker in tickers:
        snapshot = stock_service.get_price_snapshot(ticker)
        if snapshot:
            lines.append(format_price_line(snapshot))
        else:
            lines.append(f"*{ticker}*: (data unavailable)")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full, up-to-date detail on every tracked stock (price, day range, volume)."""
    tickers = db.get_stocks(update.effective_user.id)
    if not tickers:
        await update.message.reply_text(
            "Your watchlist is empty. Add a stock with /add <TICKER>."
        )
        return

    await update.message.reply_chat_action("typing")
    lines = ["📊 *All Your Stocks — Live Snapshot*\n"]
    for ticker in tickers:
        snapshot = stock_service.get_price_snapshot(ticker)
        if snapshot:
            lines.append(format_detail_block(snapshot))
        else:
            lines.append(f"*{ticker}*: (data unavailable)")
        lines.append("")  # spacer

    lines.append(f"🕒 Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price <TICKER>  (e.g. /price MSFT)")
        return

    ticker = context.args[0].upper().strip()
    await update.message.reply_chat_action("typing")
    snapshot = stock_service.get_price_snapshot(ticker)
    if not snapshot:
        await update.message.reply_text(f"❌ Couldn't fetch data for '{ticker}'.")
        return

    await update.message.reply_text(format_price_line(snapshot), parse_mode=ParseMode.MARKDOWN)

async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /chart <TICKER>  (e.g. /chart NVDA)")
        return

    ticker = context.args[0].upper().strip()
    await update.message.reply_chat_action("typing")

    if not stock_service.validate_ticker(ticker):
        await update.message.reply_text(f"❌ Couldn't find a ticker called '{ticker}'.")
        return

    buttons = [
        [InlineKeyboardButton(tf["label"], callback_data=f"chart:{ticker}:{key}")]
        for key, tf in config.TIMEFRAMES.items()
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"📈 Choose a timeframe for *{ticker}*:", reply_markup=markup, parse_mode=ParseMode.MARKDOWN
    )


async def chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, ticker, tf_key = query.data.split(":")

    await context.bot.send_chat_action(chat_id=query.message.chat_id, action="upload_photo")

    df = stock_service.get_history_for_timeframe(ticker, tf_key)
    if df is None:
        await query.message.reply_text(f"❌ Couldn't fetch chart data for {ticker} ({tf_key}).")
        return

    label = config.TIMEFRAMES[tf_key]["label"]
    snapshot = stock_service.get_price_snapshot(ticker)
    caption = (
        f"{format_price_line(snapshot)}\n_Timeframe: {label}_"
        if snapshot
        else f"*{ticker}* — {label}"
    )

    chart_buf = generate_chart(ticker, df, label=label)
    await query.message.reply_photo(photo=chart_buf, caption=caption, parse_mode=ParseMode.MARKDOWN)


async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("📊 All stocks (one setting for everything)", callback_data="intmenu:all")],
        [InlineKeyboardButton("🎯 Single stock price alert", callback_data="intmenu:single")],
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "⏱️ What kind of notification do you want to set up?", reply_markup=markup
    )


async def intmenu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":")[1]

    if choice == "all":
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"interval:{seconds}")]
            for label, seconds in config.INTERVALS.items()
        ]
        buttons.append([InlineKeyboardButton("Turn OFF", callback_data="interval:off")])
        await query.edit_message_text(
            "⏱️ How often should I send updates for your *entire* watchlist?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        tickers = db.get_stocks(query.from_user.id)
        if not tickers:
            await query.edit_message_text(
                "You don't have any stocks yet. Add one first with /add <TICKER>."
            )
            return
        buttons = [
            [InlineKeyboardButton(t, callback_data=f"alertstock:{t}")] for t in tickers
        ]
        await query.edit_message_text(
            "🎯 Which stock do you want price alerts for?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def interval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'all stocks' interval selection."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data.split(":")[1]

    if data == "off":
        db.set_interval(user_id, None)
        await query.edit_message_text("🔕 Auto-notifications for all stocks turned OFF.")
        return

    seconds = int(data)
    db.set_interval(user_id, seconds)
    await query.edit_message_text(
        f"🔔 All-stocks auto-notifications set to every {interval_label(seconds)}."
    )


async def alertstock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User picked which of their stocks to set a price alert on."""
    query = update.callback_query
    await query.answer()
    ticker = query.data.split(":")[1]

    buttons = [
        [InlineKeyboardButton(label, callback_data=f"alertinterval:{ticker}:{seconds}")]
        for label, seconds in config.INTERVALS.items()
    ]
    buttons.append([InlineKeyboardButton("🔕 Remove this alert", callback_data=f"alertremove:{ticker}")])
    await query.edit_message_text(
        f"⏱️ How often should I alert you on *{ticker}*'s price changes?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def alertinterval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, ticker, seconds = query.data.split(":")
    seconds = int(seconds)

    db.set_stock_alert(query.from_user.id, ticker, seconds)
    await query.edit_message_text(
        f"🎯 You'll get *{ticker}* price alerts every {interval_label(seconds)} "
        f"(shows whether it went up or down).",
        parse_mode=ParseMode.MARKDOWN,
    )


async def alertremove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ticker = query.data.split(":")[1]
    db.remove_stock_alert(query.from_user.id, ticker)
    await query.edit_message_text(f"🔕 Removed price alerts for {ticker}.")


async def remove_alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removealert <TICKER>  (e.g. /removealert TSLA)")
        return
    ticker = context.args[0].upper().strip()
    removed = db.remove_stock_alert(update.effective_user.id, ticker)
    if removed:
        await update.message.reply_text(f"🔕 Removed price alert for {ticker}.")
    else:
        await update.message.reply_text(f"No alert was set for {ticker}.")


async def my_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lines = []

    seconds = db.get_interval(user_id)
    if seconds:
        lines.append(f"📊 All-stocks updates: every {interval_label(seconds)}")
    else:
        lines.append("📊 All-stocks updates: OFF")

    alerts = db.get_user_alerts(user_id)
    if alerts:
        lines.append("\n🎯 Per-stock price alerts:")
        for a in alerts:
            lines.append(f"   • {a['ticker']}: every {interval_label(a['interval_seconds'])}")
    else:
        lines.append("\n🎯 No per-stock alerts set.")

    await update.message.reply_text("\n".join(lines))


async def notification_job(context: ContextTypes.DEFAULT_TYPE):
    # --- (1) All-stocks notifications ---
    due_users = db.get_users_due_for_notification()
    for user in due_users:
        user_id = user["user_id"]
        tickers = db.get_stocks(user_id)

        if not tickers:
            db.update_last_notified(user_id)
            continue

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🔔 *Scheduled Update* — {datetime.now().strftime('%H:%M:%S')}",
                parse_mode=ParseMode.MARKDOWN,
            )
            for ticker in tickers:
                snapshot = stock_service.get_price_snapshot(ticker)
                df = stock_service.get_history_for_timeframe(ticker, config.DEFAULT_NOTIFY_TIMEFRAME)
                if snapshot and df is not None:
                    label = config.TIMEFRAMES[config.DEFAULT_NOTIFY_TIMEFRAME]["label"]
                    chart_buf = generate_chart(ticker, df, label=label)
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=chart_buf,
                        caption=format_price_line(snapshot),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                elif snapshot:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=format_price_line(snapshot),
                        parse_mode=ParseMode.MARKDOWN,
                    )
        except Exception as e:
            logger.warning(f"Failed to notify user {user_id}: {e}")
        finally:
            db.update_last_notified(user_id)

    # --- (2) Per-stock price-change alerts ---
    due_alerts = db.get_alerts_due()
    for alert in due_alerts:
        user_id = alert["user_id"]
        ticker = alert["ticker"]
        try:
            snapshot = stock_service.get_price_snapshot(ticker)
            if snapshot:
                prev_price = alert.get("last_price")
                if prev_price is not None:
                    diff = snapshot["price"] - prev_price
                    if diff > 0:
                        trend = f"🟢▲ up ${diff:.2f} since the last check"
                    elif diff < 0:
                        trend = f"🔴▼ down ${abs(diff):.2f} since the last check"
                    else:
                        trend = "⏸️ no change since the last check"
                else:
                    trend = "Baseline price recorded — you'll see the trend from here."

                text = f"🎯 *{ticker} Price Alert*\n{format_price_line(snapshot)}\n{trend}"
                await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN)
                db.update_alert_notified(alert["id"], snapshot["price"])
            else:
                db.update_alert_notified(alert["id"], alert.get("last_price"))
        except Exception as e:
            logger.warning(f"Failed to send alert to user {user_id} for {ticker}: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if config.BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise SystemExit(
            "Please set your bot token in config.py or via the TELEGRAM_BOT_TOKEN "
            "environment variable before running the bot."
        )

    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("add", add_stock))
    app.add_handler(CommandHandler("remove", remove_stock))
    app.add_handler(CommandHandler("list", list_stocks))
    app.add_handler(CommandHandler("all", all_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("chart", chart_cmd))
    app.add_handler(CommandHandler("setinterval", set_interval))
    app.add_handler(CommandHandler("myinterval", my_interval))
    app.add_handler(CommandHandler("removealert", remove_alert_cmd))

    app.add_handler(CallbackQueryHandler(chart_callback, pattern=r"^chart:"))
    app.add_handler(CallbackQueryHandler(intmenu_callback, pattern=r"^intmenu:"))
    app.add_handler(CallbackQueryHandler(interval_callback, pattern=r"^interval:"))
    app.add_handler(CallbackQueryHandler(alertstock_callback, pattern=r"^alertstock:"))
    app.add_handler(CallbackQueryHandler(alertinterval_callback, pattern=r"^alertinterval:"))
    app.add_handler(CallbackQueryHandler(alertremove_callback, pattern=r"^alertremove:"))

    # Background job that checks for due notifications every SCHEDULER_TICK_SECONDS
    app.job_queue.run_repeating(
        notification_job, interval=config.SCHEDULER_TICK_SECONDS, first=10
    )

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()