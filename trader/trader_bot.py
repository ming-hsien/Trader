import time
import ccxt
import yaml
import argparse
import pandas as pd

import order
from position_manager import PositionManager


def fetch_ohlcv(exchange, symbol, timeframe="5m", limit=200) -> pd.DataFrame:
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df

def generate_signal(df, strategy):
    if strategy == "auto":
        best_strat = best_strategy()
        strategy = best_strat
        
    if strategy == "sma":
        df_sig = generate_sma_signals(df)
    elif strategy == "ema":
        df_sig = generate_ema_signals(df)
    elif strategy == "alligator":
        df_sig = generate_alligator_signals(df)
        
    # 用倒數第二根避免 repaint
    last = df_sig.iloc[-2]
    return last["signal_long"], last["signal_exit"]

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

def best_strategy() -> str:
    stats = {}
    for strat in ["sma", "ema", "alligator"]:
        df_sig = apply_strategy(df, strat)
        _, _, s = backtest(df_sig)
        stats[strat] = s["total_return"]
    best_strat = max(stats, key=stats.get)
    return best_strat

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="../config.yaml", help="config file path")
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
        df = fetch_ohlcv(exchange, symbol, timeFrame)
        df_sig = generate_signal(df, strategy)
        last = df_sig.iloc[-2]

        price = last["close"]

        # buy logic
        if not pm.active and last["signal_long"]:
            qty = (equity * 0.01) / price
            sl = price - last["atr"]
            tp = price + 2 * last["atr"]

            pm.open_long(price, qty, last["ts"], sl=sl, tp=tp)
            exchange.create_order(symbol, "market", "buy", qty)
            print("BUY", qty, price)

        # sell logic
        elif pm.active and pm.should_exit(price, exit_signal=last["signal_exit"]):
            exchange.create_order(symbol, "market", "sell", pm.qty)
            print("SELL", pm.qty, price)
            pm.close_position()

        time.sleep(5)

if __name__ == "__main__":
    main()
        