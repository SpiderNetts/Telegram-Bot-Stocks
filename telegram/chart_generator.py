"""
Generates a price chart (PNG) for a given ticker's history DataFrame.
"""

import io
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import pandas as pd


def generate_chart(ticker: str, df: pd.DataFrame, label: str | None = None) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)

    line_color = "#2e7d32" if df["Close"].iloc[-1] >= df["Close"].iloc[0] else "#c62828"

    ax.plot(df.index, df["Close"], color=line_color, linewidth=1.8)
    ax.fill_between(df.index, df["Close"], df["Close"].min(), color=line_color, alpha=0.08)

    title = f"{ticker.upper()} — {label}" if label else f"{ticker.upper()} — Price Chart"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Price")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.autofmt_xdate(rotation=30)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf