"""
SQLite persistence layer.

Tables:
  users(
    user_id INTEGER PRIMARY KEY,
    interval_seconds INTEGER,        -- NULL = notifications off
    last_notified TEXT               -- ISO timestamp of last notification sent
  )

  watchlist(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ticker TEXT,
    UNIQUE(user_id, ticker)
  )

  stock_alerts(                    -- per-stock price-change alerts
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ticker TEXT,
    interval_seconds INTEGER,
    last_notified TEXT,
    last_price REAL,
    UNIQUE(user_id, ticker)
  )
"""

import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

from config import DB_PATH, MAX_STOCKS_PER_USER


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                interval_seconds INTEGER,
                last_notified TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                UNIQUE(user_id, ticker)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL,
                last_notified TEXT,
                last_price REAL,
                UNIQUE(user_id, ticker)
            )
            """
        )


def ensure_user(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, interval_seconds, last_notified) VALUES (?, NULL, NULL)",
            (user_id,),
        )


def add_stock(user_id: int, ticker: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    ensure_user(user_id)
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM watchlist WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]

        existing = conn.execute(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        if existing:
            return False, f"{ticker} is already in your watchlist."

        if count >= MAX_STOCKS_PER_USER:
            return False, (
                f"You already track {MAX_STOCKS_PER_USER} stocks (the max). "
                f"Remove one first with /remove <TICKER>."
            )

        conn.execute(
            "INSERT INTO watchlist (user_id, ticker) VALUES (?, ?)", (user_id, ticker)
        )
        return True, f"{ticker} added to your watchlist."


def remove_stock(user_id: int, ticker: str) -> bool:
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        return cur.rowcount > 0


def get_stocks(user_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
        return [r["ticker"] for r in rows]


def set_interval(user_id: int, seconds: int | None):
    ensure_user(user_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET interval_seconds = ?, last_notified = ? WHERE user_id = ?",
            (seconds, datetime.now(timezone.utc).isoformat(), user_id),
        )


def get_interval(user_id: int) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT interval_seconds FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["interval_seconds"] if row else None


def get_users_due_for_notification() -> list[dict]:
    """Returns users whose interval has elapsed since last_notified."""
    now = datetime.now(timezone.utc)
    due = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, interval_seconds, last_notified FROM users "
            "WHERE interval_seconds IS NOT NULL"
        ).fetchall()
        for row in rows:
            last = row["last_notified"]
            if last is None:
                due.append(dict(row))
                continue
            last_dt = datetime.fromisoformat(last)
            elapsed = (now - last_dt).total_seconds()
            if elapsed >= row["interval_seconds"]:
                due.append(dict(row))
    return due


def update_last_notified(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_notified = ? WHERE user_id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id),
        )


def set_stock_alert(user_id: int, ticker: str, interval_seconds: int):
    """Creates or updates a price-change alert for one ticker."""
    ticker = ticker.upper().strip()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO stock_alerts (user_id, ticker, interval_seconds, last_notified, last_price)
            VALUES (?, ?, ?, ?, NULL)
            ON CONFLICT(user_id, ticker) DO UPDATE SET
                interval_seconds = excluded.interval_seconds,
                last_notified = excluded.last_notified
            """,
            (user_id, ticker, interval_seconds, now),
        )


def remove_stock_alert(user_id: int, ticker: str) -> bool:
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM stock_alerts WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        return cur.rowcount > 0


def get_user_alerts(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker, interval_seconds FROM stock_alerts WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_alerts_due() -> list[dict]:
    """Returns per-stock alerts whose interval has elapsed."""
    now = datetime.now(timezone.utc)
    due = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, user_id, ticker, interval_seconds, last_notified, last_price FROM stock_alerts"
        ).fetchall()
        for row in rows:
            last = row["last_notified"]
            if last is None:
                due.append(dict(row))
                continue
            elapsed = (now - datetime.fromisoformat(last)).total_seconds()
            if elapsed >= row["interval_seconds"]:
                due.append(dict(row))
    return due


def update_alert_notified(alert_id: int, price: float | None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE stock_alerts SET last_notified = ?, last_price = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), price, alert_id),
        )