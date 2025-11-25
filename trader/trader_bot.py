import json
import time
import ccxt
import yaml
import argparse
import pandas as pd

# import trader.order
from trader.position_manager import PositionManager
from backtest.signal_generator import generate_signal

import backtest.backtest as BT

def fetch_ohlcv(exchange, symbol, timeframe="5m", limit=200) -> pd.DataFrame:
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df

def load_config(path="../config.yaml") -> dict:
    """
    Load configure file
    """
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config

def get_exchange(config: dict) -> ccxt.Exchange:
    """
    Create and return a ccxt exchange object based on the configuration file
    """
    exchange_id = config.get("EXCHANGE")
    api_key = config.get("API_KEY", "")
    secret = config.get("SECRET", "")
    if exchange_id == "binance":
        exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })
        return exchange

    return None

def apply_strategy(df, name, **params):
    """
    根據策略名稱產生訊號
    params 用來塞策略參數（例如 sma_fast, sma_slow, ema_fast, ema_slow）
    """
    df_sig = None
    try :
        df_sig = generate_signal(df, name, trader=False, **params)
    except:
        raise ValueError(f"Unknown strategy: {name}")

    return df_sig

def best_strategy(symbol, timeframe, lookback_days=365):
    """
    1) 抓 lookback_days 的 K 線資料
    2) 對每個策略嘗試多組參數
    3) 計算總報酬 total_return
    4) 回傳最佳策略名稱與最佳參數
    """
    
    df = BT.fetch_klines_ccxt(symbol, timeframe, lookback_days)

    all_results = []   # 用來存 (strategy, params, total_return)

    sma_fast_list = [5, 7, 9, 10, 15, 20]
    sma_slow_list = [30, 40, 50, 60, 100, 150, 200]

    for fast in sma_fast_list:
        for slow in sma_slow_list:
            if fast >= slow:
                continue
            
            df_sig = apply_strategy(df, "sma", fast=fast, slow=slow)
            _, _, stats = BT.backtest("sma", df_sig)

            all_results.append((
                "sma",
                {"fast": fast, "slow": slow},
                stats
            ))

    ema_fast_list = [5, 7, 9, 10, 15, 20]
    ema_slow_list = [30, 40, 50, 60, 100, 150, 200]

    for fast in ema_fast_list:
        for slow in ema_slow_list:
            if fast >= slow:
                continue
            
            df_sig = apply_strategy(df, "ema", fast=fast, slow=slow)
            _, _, stats = BT.backtest("ema", df_sig)

            all_results.append((
                "ema",
                {"fast": fast, "slow": slow},
                stats
            ))

    df_sig = apply_strategy(df, "alligator")
    _, _, stats = BT.backtest("alligator", df_sig)
    all_results.append(("alligator", {}, stats))

    best = max(all_results, key=lambda x: x[2]["total_return"])
    best_name, best_params, stats = best

    print("===== Best Strategy Found By Total Return =====")
    print("Strategy:", best_name)
    print("Parameters:", best_params)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("================================")
    
    
    best = max(all_results, key=lambda x: x[2]["sharpe_approx"])
    best_name, best_params, stats = best
    print("===== Best Strategy Found By Sharpe Approx =====")
    print("Strategy:", best_name)
    print("Parameters:", best_params)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("================================")

    return best_name, best_params

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="config.yaml", help="config file path")
    args = ap.parse_args()
    
    config = load_config(path=args.config)
    symbol = config.get("SYMBOL", "XRP/USDT")
    timeFrame = config.get("TIME_FRAME", "1h")
    feeRate = config.get("FEE_RATE", 0.001)
    equity = config.get("EQUITY", 10.0)
    rpt = config.get("RISK_PER_TRADE", 0.01)
    mdd = config.get("MAX_DAILY_DRAWDOWN", 0.03)
    
    strategy = config.get("STRATEGY", "AUTO").lower()
    
    exchange = get_exchange(config)
    pm = PositionManager()

    while True:
        # df = fetch_ohlcv(exchange, symbol, timeFrame)
        if strategy == "auto":
            best_strat, best_params = best_strategy(symbol, timeFrame, lookback_days=365)
            strategy = best_strat
        # df_sig = generate_signal(df, strategy)
        # last = df_sig.iloc[-2]

        # price = last["close"]

        # buy logic
        # if not pm.active and last["signal_long"]:
        #     qty = (equity * 0.01) / price
        #     sl = price - last["atr"]
        #     tp = price + 2 * last["atr"]

        #     pm.open_long(price, qty, last["ts"], sl=sl, tp=tp)
        #     exchange.create_order(symbol, "market", "buy", qty)
        #     print("BUY", qty, price)

        # # sell logic
        # elif pm.active and pm.should_exit(price, exit_signal=last["signal_exit"]):
        #     exchange.create_order(symbol, "market", "sell", pm.qty)
        #     print("SELL", pm.qty, price)
        #     pm.close_position()

        time.sleep(5)

if __name__ == "__main__":
    main()
        