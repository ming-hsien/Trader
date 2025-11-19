"""
用 ccxt 從 Binance 抓歷史 K 線，並用 SMA20 / SMA50 交叉做最小可跑回測。

功能：
- 透過 ccxt.binance().fetch_ohlcv() 抓 XRP/USDT 等商品歷史 K 線
- 本地計算 SMA_20, SMA_50, EMA_20, EMA_50
- 策略 : SMA20 黃金交叉 SMA50 時全倉做多，死亡交叉出場
- 手續費：單邊 fee_rate (預設 0.1%)
"""

from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from types_trading import Trade

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    在 DataFrame 上加上常用技術指標(SMA/EMA):
    - SMA_20, SMA_50
    - EMA_20, EMA_50
    """
    out = df.copy()
    close = out["close"]

    # 簡單移動平均
    out["SMA_20"] = close.rolling(window=20, min_periods=20).mean()
    out["SMA_50"] = close.rolling(window=50, min_periods=50).mean()

    # 指數移動平均
    out["EMA_20"] = close.ewm(span=20, adjust=False).mean()
    out["EMA_50"] = close.ewm(span=50, adjust=False).mean()

    return out


# === 產生策略訊號（SMA 交叉） ===
def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    使用 SMA20 / SMA50 交叉產生進出場訊號。
    - 黃金交叉:SMA20 由下往上穿過 SMA50 → signal_long = True
    - 死亡交叉:SMA20 由上往下跌破 SMA50 → signal_exit = True
    下單價使用「下一根 K 線的開盤價」(next_open)。
    """
    out = df.copy()

    if "SMA_20" not in out.columns or "SMA_50" not in out.columns:
        out = add_indicators(out)

    out["SMA_20_prev"] = out["SMA_20"].shift(1)
    out["SMA_50_prev"] = out["SMA_50"].shift(1)

    # 黃金交叉：前一根 20 <= 50，這一根 20 > 50
    out["signal_long"] = (
        (out["SMA_20_prev"] <= out["SMA_50_prev"]) &
        (out["SMA_20"] > out["SMA_50"])
    )

    # 死亡交叉：前一根 20 >= 50，這一根 20 < 50
    out["signal_exit"] = (
        (out["SMA_20_prev"] >= out["SMA_50_prev"]) &
        (out["SMA_20"] < out["SMA_50"])
    )

    # 實際進出場價：用「下一根 K 的開盤價」
    out["next_open"] = out["open"].shift(-1)

    return out

def backtest_sma_cross(
    df_sig: pd.DataFrame,
    initial_equity: float = 10_000.0,
    fee_rate: float = 0.001,
) -> tuple[pd.Series, List[Trade], dict]:
    """
    全倉 SMA20/50 交叉策略回測：
    - 有部位時不重複進場
    - 出場條件為死亡交叉
    - 每次買 / 賣都扣單邊手續費 fee_rate
    """
    equity = initial_equity
    equity_curve = []

    position = 0.0         # 持有幣的數量（例如 XRP）
    entry_price = None
    entry_time = None
    trades: List[Trade] = []

    for i in range(len(df_sig) - 1):  # 最後一列沒有 next_open，略過
        row = df_sig.iloc[i]

        # 還沒有 SMA 值的前期資料，跳過交易邏輯
        if pd.isna(row["SMA_20"]) or pd.isna(row["SMA_50"]):
            equity_curve.append(equity if position == 0 else equity + position * row["close"])
            continue

        px_next_open = float(row["next_open"])
        if np.isnan(px_next_open) or px_next_open <= 0:
            equity_curve.append(equity if position == 0 else equity + position * row["close"])
            continue

        # --- 出場邏輯 ---
        if position > 0 and row["signal_exit"]:
            gross = position * px_next_open
            fee = gross * fee_rate
            cash_in = gross - fee

            trade_ret = (px_next_open * (1 - fee_rate) / (entry_price * (1 + fee_rate))) - 1.0
            pnl = cash_in  # 這裡只是示意，詳細 PnL 可再拆

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

        # --- 進場邏輯 ---
        if position == 0 and row["signal_long"]:
            # 全倉買進（扣手續費）
            size = equity / (px_next_open * (1 + fee_rate))
            cost = size * px_next_open
            fee = cost * fee_rate

            equity -= (cost + fee)
            position = size
            entry_price = px_next_open
            entry_time = row["open_time"]

        # 每個 bar 計算 MTM（市值）
        mtm_equity = equity + position * row["close"]
        equity_curve.append(mtm_equity)

    equity_series = pd.Series(equity_curve, index=df_sig["open_time"].iloc[: len(equity_curve)])

    # 績效指標
    returns = equity_series.pct_change().fillna(0.0)
    total_return = equity_series.iloc[-1] / initial_equity - 1.0
    max_equity = equity_series.cummax()
    drawdown = equity_series / max_equity - 1.0
    max_dd = drawdown.min()

    if returns.std(ddof=0) > 0:
        sharpe = (returns.mean() / returns.std(ddof=0)) * np.sqrt(252 * 24)
    else:
        sharpe = 0.0

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
