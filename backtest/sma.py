from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest.types_trading import Trade


def add_indicators(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    加上 SMA_fast / SMA_slow 以及 EMA_fast / EMA_slow。
    fast / slow 可以任意調整。
    """
    out = df.copy()
    close = out["close"]

    # SMA
    out[f"SMA_{fast}"] = close.rolling(window=fast, min_periods=fast).mean()
    out[f"SMA_{slow}"] = close.rolling(window=slow, min_periods=slow).mean()

    return out

def compute_signals(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    使用 SMA_fast / SMA_slow 動態交叉產生訊號。
    - 黃金交叉: SMA_fast 由下往上穿過 SMA_slow → signal_long
    - 死亡交叉: SMA_fast 由上往下跌破 SMA_slow → signal_exit
    """
    if fast >= slow:
        raise ValueError("fast SMA 必須小於 slow SMA，例如 fast=20, slow=50")

    out = df.copy()
    out = add_indicators(out, fast=fast, slow=slow)

    sma_fast = f"SMA_{fast}"
    sma_slow = f"SMA_{slow}"

    out[f"{sma_fast}_prev"] = out[sma_fast].shift(1)
    out[f"{sma_slow}_prev"] = out[sma_slow].shift(1)

    out["signal_long"] = (
        (out[f"{sma_fast}_prev"] <= out[f"{sma_slow}_prev"]) &
        (out[sma_fast] > out[sma_slow])
    )

    out["signal_exit"] = (
        (out[f"{sma_fast}_prev"] >= out[f"{sma_slow}_prev"]) &
        (out[sma_fast] < out[sma_slow])
    )

    out["next_open"] = out["open"].shift(-1)

    return out


def backtest_sma_cross(
    df_sig: pd.DataFrame,
    initial_equity: float = 10_000.0,
    fee_rate: float = 0.001,
) -> tuple[pd.Series, List[Trade], dict]:

    equity = initial_equity
    equity_curve = []

    position = 0.0
    entry_price = None
    entry_time = None
    trades: List[Trade] = []

    for i in range(len(df_sig) - 1):
        row = df_sig.iloc[i]

        if pd.isna(row["next_open"]):
            equity_curve.append(equity + position * row["close"])
            continue

        px_next_open = float(row["next_open"])
        if px_next_open <= 0:
            equity_curve.append(equity + position * row["close"])
            continue

        if position > 0 and row["signal_exit"]:
            gross = position * px_next_open
            fee = gross * fee_rate
            cash_in = gross - fee

            trade_ret = (px_next_open * (1 - fee_rate) / (entry_price * (1 + fee_rate))) - 1.0
            pnl = cash_in

            equity += cash_in
            trades.append(
                Trade(
                    entry_time=entry_time,
                    exit_time=row["open_time"],
                    entry_price=entry_price,
                    exit_price=px_next_open,
                    pnl=pnl,
                    ret=trade_ret,
                )
            )

            position = 0.0
            entry_price = None
            entry_time = None

        if position == 0 and row["signal_long"]:
            size = equity / (px_next_open * (1 + fee_rate))
            cost = size * px_next_open
            fee = cost * fee_rate

            equity -= (cost + fee)
            position = size
            entry_price = px_next_open
            entry_time = row["open_time"]

        mtm_equity = equity + position * row["close"]
        equity_curve.append(mtm_equity)

    equity_series = pd.Series(equity_curve, index=df_sig["open_time"].iloc[:len(equity_curve)])

    returns = equity_series.pct_change().fillna(0.0)
    total_return = equity_series.iloc[-1] / initial_equity - 1.0
    max_equity = equity_series.cummax()
    drawdown = equity_series / max_equity - 1.0
    max_dd = drawdown.min()

    sharpe = 0.0
    if returns.std(ddof=0) > 0:
        sharpe = (returns.mean() / returns.std(ddof=0)) * np.sqrt(252 * 24)

    stats = {
        "initial_equity": initial_equity,
        "final_equity": float(equity_series.iloc[-1]),
        "total_return": float(total_return),
        "max_drawdown": float(max_dd),
        "sharpe_approx": float(sharpe),
        "num_trades": len(trades),
    }

    return equity_series, trades, stats


if __name__ == "__main__":
    pass
