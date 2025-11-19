from typing import List
import numpy as np
import pandas as pd

from types_trading import Trade

def smma(series: pd.Series, period: int) -> pd.Series:
    """
    近似 Bill Williams 的 SMMA (平滑移動平均)
    用 EWM(alpha=1/period) 來實作，速度較快。
    """
    return series.ewm(alpha=1/period, adjust=False).mean()

def add_alligator(df: pd.DataFrame) -> pd.DataFrame:
    """
    在 DataFrame 上加上 Alligator 三條線：
    - jaw   (下顎)  : 13 期 SMMA，右移 8 根
    - teeth (牙齒)  : 8 期 SMMA，右移 5 根
    - lips  (嘴唇)  : 5 期 SMMA，右移 3 根

    假設 df 至少有欄位: ["high", "low"]
    """
    price = (df["high"] + df["low"]) / 2.0

    df["jaw"] = smma(price, 13).shift(8)
    df["teeth"] = smma(price, 8).shift(5)
    df["lips"] = smma(price, 5).shift(3)
    
    df["next_open"] = df["open"].shift(-1)

    return df

def generate_alligator_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    根據鱷魚策略產生進出場訊號 & position。
    假設 df 至少有: ["open", "high", "low", "close"]。

    回傳的 df 會包含:
      - jaw, teeth, lips
      - long_entry, short_entry
      - long_exit, short_exit
      - position  (1 = 多頭, -1 = 空頭, 0 = 空手)
    """
    df = df.copy()
    df = add_alligator(df)

    # --- 多空趨勢結構判斷 --- #
    long_trend = (df["lips"] > df["teeth"]) & (df["teeth"] > df["jaw"])
    short_trend = (df["lips"] < df["teeth"]) & (df["teeth"] < df["jaw"])

    # 斜率方向（簡單用前一根比較）
    long_slope = (
        (df["lips"] > df["lips"].shift(1)) &
        (df["teeth"] > df["teeth"].shift(1)) &
        (df["jaw"] > df["jaw"].shift(1))
    )
    short_slope = (
        (df["lips"] < df["lips"].shift(1)) &
        (df["teeth"] < df["teeth"].shift(1)) &
        (df["jaw"] < df["jaw"].shift(1))
    )

    # --- 進場訊號 --- #
    df["long_entry"] = (
        long_trend &
        long_slope &
        (df["close"] > df["lips"]) &
        (~long_trend.shift(1).fillna(False))
    )

    df["short_entry"] = (
        short_trend &
        short_slope &
        (df["close"] < df["lips"]) &
        (~short_trend.shift(1).fillna(False))
    )

    # --- 出場訊號 --- #
    df["long_exit"] = (
        (df["close"] < df["jaw"]) |  # 跌破下顎
        (df["lips"] <= df["teeth"])  # 嘴唇不再領先牙齒，結構壞掉
    )

    df["short_exit"] = (
        (df["close"] > df["jaw"]) |  # 突破下顎
        (df["lips"] >= df["teeth"])
    )

    # --- 根據訊號產生 position（單一部位，非多空同時持有） --- #
    position = []
    current_pos = 0  # 1 = long, -1 = short, 0 = flat

    for i in range(len(df)):
        if current_pos == 0:
            # 沒部位時，優先進多；如果你想多空同等，可以加條件選擇
            if df["long_entry"].iloc[i]:
                current_pos = 1
            elif df["short_entry"].iloc[i]:
                current_pos = -1

        elif current_pos == 1:
            # 有多單時，遇到 long_exit 就平倉；可選擇同時 short_entry 時反手
            if df["long_exit"].iloc[i]:
                current_pos = 0
                # 如果想反手就寫：
                # if df["short_entry"].iloc[i]:
                #     current_pos = -1

        elif current_pos == -1:
            # 有空單時
            if df["short_exit"].iloc[i]:
                current_pos = 0
                # 如果想反手就寫：
                # if df["long_entry"].iloc[i]:
                #     current_pos = 1

        position.append(current_pos)

    df["position"] = position

    return df

# from types_trading import Trade  # 你共用的 Trade dataclass

def backtest_alligator(
    df_sig: pd.DataFrame,
    initial_equity: float = 10_000.0,
    fee_rate: float = 0.001,
) -> tuple[pd.Series, List[Trade], dict]:
    """
    全倉 Alligator 順勢策略回測（只做多）：
    - 有部位時不重複進場
    - 進場條件:long_entry == True (Alligator 張口向上、多頭結構成立)
    - 出場條件:long_exit == True (Alligator 結構被破壞或價格跌破下顎)
    - 交易在「下一根 K 線開盤價」成交
    - 每次買 / 賣都扣單邊手續費 fee_rate
    """
    equity = initial_equity
    equity_curve = []

    position = 0.0         # 持有標的數量（例如 XRP 數量）
    entry_price = None
    entry_time = None
    trades: List[Trade] = []

    for i in range(len(df_sig) - 1):  # 最後一列沒有 next_open，略過
        row = df_sig.iloc[i]

        # 還沒有 Alligator 值的前期資料，跳過交易邏輯
        if pd.isna(row["jaw"]) or pd.isna(row["teeth"]) or pd.isna(row["lips"]):
            equity_curve.append(equity if position == 0 else equity + position * row["close"])
            continue

        px_next_open = float(row["next_open"])
        if np.isnan(px_next_open) or px_next_open <= 0:
            equity_curve.append(equity if position == 0 else equity + position * row["close"])
            continue

        # --- 出場邏輯（已有多單時） --- #
        if position > 0 and bool(row["long_exit"]):
            gross = position * px_next_open           # 賣出總金額
            fee = gross * fee_rate                    # 交易手續費
            cash_in = gross - fee                     # 實收金額

            # 粗略報酬率（含進出場雙邊手續費）
            trade_ret = (px_next_open * (1 - fee_rate) / (entry_price * (1 + fee_rate))) - 1.0
            pnl = cash_in  # 這裡沿用你原本的寫法，PnL 如需更精確可再調整

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

        # --- 進場邏輯（目前空手 & 出現多頭訊號） --- #
        if position == 0 and bool(row["long_entry"]):
            # 全倉買進（扣手續費）
            size = equity / (px_next_open * (1 + fee_rate))
            cost = size * px_next_open
            fee = cost * fee_rate

            equity -= (cost + fee)
            position = size
            entry_price = px_next_open
            entry_time = row["open_time"]

        # --- 每個 bar 計算 MTM（市值） --- #
        mtm_equity = equity + position * row["close"]
        equity_curve.append(mtm_equity)

    # 用 open_time 當 equity curve index（跟你的 SMA 版本風格一致）
    equity_series = pd.Series(
        equity_curve,
        index=df_sig["open_time"].iloc[: len(equity_curve)]
    )

    # 績效指標
    returns = equity_series.pct_change().fillna(0.0)
    total_return = equity_series.iloc[-1] / initial_equity - 1.0
    max_equity = equity_series.cummax()
    drawdown = equity_series / max_equity - 1.0
    max_dd = drawdown.min()

    if returns.std(ddof=0) > 0:
        # 這裡假設 1 天 24 根 bar，252 交易日（你可依實際週期調整）
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

