from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from types_trading import Trade

def generate_ema_signals(df, fast=20, slow=50):
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow, adjust=False).mean()

    df["signal_long"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
    df["signal_exit"] = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

    df["next_open"] = df["open"].shift(-1)
    return df

def backtest_ema_cross(
    df_sig: pd.DataFrame,
    initial_equity: float = 10_000.0,
    fee_rate: float = 0.001,
) -> tuple[pd.Series, List[Trade], dict]:

    equity_curve = []
    trades: List[Trade] = []

    cash = initial_equity
    position = 0.0            # 幣的數量（例如 XRP）
    entry_price = None
    entry_time = None

    for i in range(len(df_sig) - 1):
        row = df_sig.iloc[i]
        px_next_open = row["next_open"]

        # 若資料不完整，跳過
        if np.isnan(px_next_open) or px_next_open <= 0:
            equity_curve.append(cash + position * row["close"])
            continue

        # ------------------------------
        # 出場邏輯（已有部位 + 出場訊號）
        # ------------------------------
        if position > 0 and row["signal_exit"]:
            gross = position * px_next_open
            fee = gross * fee_rate
            cash_in = gross - fee

            # 報酬率（含進出場手續費）
            ret = (px_next_open * (1 - fee_rate)) / (entry_price * (1 + fee_rate)) - 1.0
            pnl = cash_in                         # 如果你之後想拆 PnL 可修改

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

            # reset position
            position = 0.0
            entry_price = None
            entry_time = None

        # ------------------------------
        # 進場邏輯（空手 + 進場訊號）
        # ------------------------------
        if position == 0 and row["signal_long"]:
            size = cash / (px_next_open * (1 + fee_rate))
            cost = size * px_next_open
            fee = cost * fee_rate

            cash -= (cost + fee)

            position = size
            entry_price = px_next_open
            entry_time = row["open_time"]

        # ------------------------------
        # 每根 bar 計算市值
        # ------------------------------
        mtm_equity = cash + position * row["close"]
        equity_curve.append(mtm_equity)

    # ------------------------------
    # 產生 equity series
    # ------------------------------
    equity_series = pd.Series(
        equity_curve, 
        index=df_sig["open_time"].iloc[: len(equity_curve)]
    )

    # ------------------------------
    # KPI 統計
    # ------------------------------
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
