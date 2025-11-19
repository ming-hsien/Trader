#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
從 Binance 抓歷史 K 線，並計算 SMA/EMA 等技術指標。

使用方式範例：
    python binance_fetch_xrp.py --symbol XRPUSDT --interval 1h --lookback-days 365
    python binance_fetch_xrp.py --symbol XRPUSDT --interval 15m --lookback-days 30
"""

import argparse
import time
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd

BASE_URL = "https://api.binance.com/api/v3/klines"


def fetch_klines(
    symbol: str = "XRPUSDT",
    interval: str = "1h",
    lookback_days: int = 365,
) -> pd.DataFrame:
    """
    從 Binance 抓指定商品的歷史 K 線資料（現貨），回傳 pandas DataFrame。

    :param symbol: 幣安交易對，例如 "XRPUSDT", "BTCUSDT"
    :param interval: K 線週期，例如 "1m", "5m", "15m", "1h", "4h", "1d"
    :param lookback_days: 往回抓幾天的資料（例如 30, 365）
    """

    end_ts = int(time.time() * 1000)  # 目前時間 (ms)
    now_utc = datetime.now(timezone.utc)
    start_ts = int((now_utc - timedelta(days=lookback_days)).timestamp() * 1000)

    all_rows = []
    limit = 1000  # Binance 單次最多 1000 根

    print(f"[INFO] Fetching {symbol} {interval} klines for last {lookback_days} days...")

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": limit,
        }
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            break

        all_rows.extend(data)

        # data[i] 結構參考：
        # 0  open time
        # 1  open
        # 2  high
        # 3  low
        # 4  close
        # 5  volume
        # 6  close time
        # 7  quote asset volume
        # 8  number of trades
        # 9  taker buy base asset volume
        # 10 taker buy quote asset volume
        # 11 ignore

        last_close_time = data[-1][6]
        # 如果下一個 startTime 已經超過 end_ts，就結束
        if last_close_time >= end_ts:
            break

        # 下一輪從上一根 K 線結束時間再往後 +1 ms
        start_ts = last_close_time + 1

        # 小小 sleep，避免打太快
        time.sleep(0.2)

    if not all_rows:
        raise RuntimeError("No kline data fetched. Check symbol/interval/lookback_days.")

    # 轉成 DataFrame
    df = pd.DataFrame(
        all_rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    # 型別處理
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

    # 依時間排序（保險起見）
    df = df.sort_values("open_time").reset_index(drop=True)

    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    在 DataFrame 上加上常用技術指標（SMA/EMA）：
    - SMA_20, SMA_50
    - EMA_20, EMA_50
    """
    out = df.copy()
    close = out["close"]

    out["SMA_20"] = close.rolling(window=20, min_periods=20).mean()
    out["SMA_50"] = close.rolling(window=50, min_periods=50).mean()
    out["EMA_20"] = close.ewm(span=20, adjust=False).mean()
    out["EMA_50"] = close.ewm(span=50, adjust=False).mean()

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="XRPUSDT", help="交易對，例如 XRPUSDT、BTCUSDT")
    parser.add_argument(
        "--interval",
        type=str,
        default="1h",
        help="K 線週期，例如 1m, 5m, 15m, 1h, 4h, 1d",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=365,
        help="往回抓幾天的歷史資料，例如 30 或 365",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="輸出 CSV 檔名（預設自動用 symbol_interval_days.csv）",
    )
    args = parser.parse_args()

    df = fetch_klines(symbol=args.symbol, interval=args.interval, lookback_days=args.lookback_days)
    df = add_indicators(df)

    if args.output:
        out_path = args.output
    else:
        out_path = f"{args.symbol}_{args.interval}_{args.lookback_days}d.csv"

    df.to_csv(out_path, index=False)
    print(f"[INFO] Saved {len(df)} rows to {out_path}")

    # 顯示最後幾列看看
    print(df.tail(5))


if __name__ == "__main__":
    main()
