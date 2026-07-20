"""
Fetches live/near-real-time stock data using yfinance (no API key required).

Note: yfinance pulls delayed/near-real-time data from Yahoo Finance
(typically a few minutes' delay for free access, which is standard for
free-tier market data).
"""

import yfinance as yf
import pandas as pd
from config import CHART_PERIOD, CHART_INTERVAL, TIMEFRAMES


def validate_ticker(ticker: str) -> bool:
    """Checks whether a ticker symbol exists and has data."""
    try:
        data = yf.Ticker(ticker).history(period="5d")
        return not data.empty
    except Exception:
        return False


def get_price_snapshot(ticker: str) -> dict | None:
    """
    Returns current price, previous close, absolute/percent change, plus
    today's high/low/volume and the timestamp of the last available candle.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None

        last_row = hist.iloc[-1]
        current_price = float(last_row["Close"])
        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2])
        else:
            prev_close = current_price

        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return {
            "ticker": ticker.upper(),
            "price": current_price,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "day_high": float(last_row["High"]),
            "day_low": float(last_row["Low"]),
            "volume": int(last_row["Volume"]),
            "timestamp": hist.index[-1],
        }
    except Exception:
        return None


def get_history(ticker: str, period: str = CHART_PERIOD, interval: str = CHART_INTERVAL) -> pd.DataFrame | None:
    """Returns a DataFrame of historical OHLC data for charting."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def get_history_for_timeframe(ticker: str, timeframe_key: str) -> pd.DataFrame | None:
    """
    Fetches history for one of the predefined selectable timeframes in
    config.TIMEFRAMES (e.g. "1H", "1D", "1W", "1M", "3M").
    """
    tf = TIMEFRAMES.get(timeframe_key)
    if not tf:
        return None

    df = get_history(ticker, period=tf["period"], interval=tf["interval"])
    if df is None:
        return None

    if tf.get("last_n"):
        df = df.tail(tf["last_n"])

    return df if not df.empty else None