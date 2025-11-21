from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest.types_trading import Trade

def add_ema_indicators(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    在 DataFrame 上加上 EMA_fast / EMA_slow
    """
    if fast >= slow:
        raise ValueError("EMA fast 必須小於 slow，例如 fast=20, slow=50")

    out = df.copy()
    close = out["close"]

    out[f"EMA_{fast}"] = close.ewm(span=fast, adjust=False).mean()
    out[f"EMA_{slow}"] = close.ewm(span=slow, adjust=False).mean()

    return out


def compute_signals(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    產生可調參數的 EMA fast / EMA slow 交叉策略訊號。
    - 黃金交叉 → signal_long = True
    - 死亡交叉 → signal_exit = True
    """

    out = add_ema_indicators(df, fast=fast, slow=slow)

    ema_fast = f"EMA_{fast}"
    ema_slow = f"EMA_{slow}"

    out[f"{ema_fast}_prev"] = out[ema_fast].shift(1)
    out[f"{ema_slow}_prev"] = out[ema_slow].shift(1)

    # 黃金交叉
    out["signal_long"] = (
        (out[f"{ema_fast}_prev"] <= out[f"{ema_slow}_prev"]) &
        (out[ema_fast] > out[ema_slow])
    )

    # 死亡交叉
    out["signal_exit"] = (
        (out[f"{ema_fast}_prev"] >= out[f"{ema_slow}_prev"]) &
        (out[ema_fast] < out[ema_slow])
    )

    # 下一根 K 的 open 當作下單價
    out["next_open"] = out["open"].shift(-1)

    return out


def backtest_ema_cross(
    df_sig: pd.DataFrame,
    initial_equity: float = 10_000.0,
    fee_rate: float = 0.001,
) -> tuple[pd.Series, List[Trade], dict]:

    equity_curve = []
    trades: List[Trade] = []

    cash = initial_equity
    position = 0.0
    entry_price = None
    entry_time = None

    for i in range(len(df_sig) - 1):
        row = df_sig.iloc[i]
        px_next_open = row["next_open"]

        if np.isnan(px_next_open) or px_next_open <= 0:
            equity_curve.append(cash + position * row["close"])
            continue

        if position > 0 and row["signal_exit"]:
            gross = position * px_next_open
            fee = gross * fee_rate
            cash_in = gross - fee

            ret = (px_next_open * (1 - fee_rate)) / (entry_price * (1 + fee_rate)) - 1.0
            pnl = cash_in

            cash += cash_in

            trades.append(
                Trade(
                    entry_time=entry_time,
                    exit_time=row["open_time"],
                    entry_price=entry_price,
                    exit_price=px_next_open,
                    pnl=pnl,
                    ret=ret,
                )
            )

            # reset
            position = 0.0
            entry_price = None
            entry_time = None

        if position == 0 and row["signal_long"]:
            size = cash / (px_next_open * (1 + fee_rate))
            cost = size * px_next_open
            fee = cost * fee_rate

            cash -= (cost + fee)

            position = size
            entry_price = px_next_open
            entry_time = row["open_time"]

        mtm_equity = cash + position * row["close"]
        equity_curve.append(mtm_equity)

    equity_series = pd.Series(
        equity_curve, 
        index=df_sig["open_time"].iloc[: len(equity_curve)]
    )

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
