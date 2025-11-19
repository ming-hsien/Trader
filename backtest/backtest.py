import pandas as pd
import time
from datetime import datetime, timedelta, timezone
import ccxt
import argparse
import json
import matplotlib.pyplot as plt

import alligator
import sma
import ema

def fetch_klines_ccxt(
    symbol: str = "XRP/USDT",
    timeframe: str = "1h",
    lookback_days: int = 365,
) -> pd.DataFrame:
    """
    從 Binance 用 ccxt 抓 OHLCV,回傳 DataFrame:
    欄位 : open_time, open, high, low, close, volume
    """
    exchange = ccxt.binance({
        "enableRateLimit": True,  # 幫你自動 sleep，避免觸發 rate limit
    })

    # 往回抓 lookback_days 天
    now_utc = datetime.now(timezone.utc)
    since = int((now_utc - timedelta(days=lookback_days)).timestamp() * 1000)

    all_rows: list[list] = []
    limit = 1000

    print(f"[INFO] Fetching {symbol} {timeframe} klines from Binance via ccxt (last {lookback_days} days)…")

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not ohlcv:
            break

        all_rows.extend(ohlcv)
        last_ts = ohlcv[-1][0]

        # 下一輪從最後一根 K 線後 1ms 開始，避免重複
        since = last_ts + 1

        # 如果這次拿到的根數 < limit，代表大概已經到尾端了
        if len(ohlcv) < limit:
            break

        # 避免打太快
        time.sleep(exchange.rateLimit / 1000)

    if not all_rows:
        raise RuntimeError("No kline data fetched, please check symbol/timeframe/lookback_days.")

    df = pd.DataFrame(
        all_rows,
        columns=["open_time", "open", "high", "low", "close", "volume"],
    )

    # 型別處理
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)

    df = df.sort_values("open_time").reset_index(drop=True)
    print(f"[INFO] Fetched {len(df)} bars.")
    return df

# === 畫資產曲線 ===
def plot_equity_curve(eq: pd.Series, out_path: str | None = None):
    plt.figure(figsize=(10, 4))
    plt.plot(eq.index, eq.values)
    plt.title("Equity Curve (SMA20/50 Cross, ccxt+Binance)")
    plt.xlabel("Time")
    plt.ylabel("Equity")
    plt.grid(True)
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, bbox_inches="tight")
        print(f"[INFO] Equity curve saved to {out_path}")
    else:
        plt.show()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", type=str, default="XRP/USDT", help="交易對，例如 XRP/USDT, BTC/USDT")
    ap.add_argument("--timeframe", type=str, default="1h", help="K 線週期，例如 1m, 15m, 1h, 4h, 1d")
    ap.add_argument("--days", type=int, default=365, help="往回抓幾天的資料")
    ap.add_argument("--fee", type=float, default=0.001, help="單邊手續費率（預設 0.001 = 0.1%)")
    ap.add_argument("--initial", type=float, default=10_000.0, help="初始資金")
    ap.add_argument("--no-plot", action="store_true", help="不要畫圖，只輸出數字")
    
    ap.add_argument("--strategy", type=str, default="sma", choices=["sma", "alligator", "ema"], help="選擇回測策略(預設 sma)")
    args = ap.parse_args()

    df_raw = fetch_klines_ccxt(symbol=args.symbol, timeframe=args.timeframe, lookback_days=args.days)
    
    if args.strategy == "sma":
        df_ind = sma.add_indicators(df_raw)
        df_sig = sma.compute_signals(df_ind)
        equity, trades, stats = sma.backtest_sma_cross(
            df_sig,
            initial_equity=args.initial,
            fee_rate=args.fee,
        )
        
    elif args.strategy == "alligator":
        df_ind = alligator.add_alligator(df_raw)
        df_sig = alligator.generate_alligator_signals(df_ind)
        equity, trades, stats = alligator.backtest_alligator(
            df_sig,
            initial_equity=args.initial,
            fee_rate=args.fee,
        )
    
    elif args.strategy == "ema":
        df_ind = ema.generate_ema_signals(df_raw)
        equity, trades, stats = ema.backtest_ema_cross(
            df_ind,
            initial_equity=args.initial,
            fee_rate=args.fee,
        )

    print("[RESULT] Backtest stats:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    if not args.no_plot:
        plot_equity_curve(equity, out_path="equity_curve_ccxt.png")


if __name__ == "__main__":
    main()
