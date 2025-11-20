# Trader
This repository provides a complete algorithmic trading framework designed for both historical backtesting and live automated execution on Binance.
The system supports multi-strategy evaluation, adaptive strategy switching, and fully automated trading signals based on price data, technical indicators, and custom-defined rules.

The framework includes:

- Backtesting engine — simulate trading performance with precise equity tracking, slippage, and fee modeling

- Live trading module — automatically send real orders to Binance using ccxt

- Strategy library — EMA crossover, SMA/ATR, Alligator, RSI, Bollinger Bands, Breakout, VWAP, and more

- Adaptive strategy selection — the bot evaluates multiple strategies and dynamically switches to the best-performing one

- Config-driven architecture — all parameters (API keys, symbols, timeframes, risk, strategy settings) are defined via config.yaml

- Performance analysis — equity curve, drawdown, Sharpe ratio, trade logs

This repository is ideal for traders, researchers, and developers who want a clean, extensible Python codebase for experimenting with crypto strategies and deploying real automated trading systems.

## Set Environment
```bash
git clone https://github.com/ming-hsien/Trader.git
cd TRADER
source setup_env.sh
```

## Run Backtest
```bash
cd backtest
python backtest.py --symbol <SYMBOL> --strategy <STRATEGY> --timeframe <TIME_FRAME> --days <DAYS> --fee <FEE_RATE> --initial <PRINCIPAL>
```
- `<SYMBOL>` ： XRP/USDT or BTC/USDT or ETH/USDT (default=XRP/USDT)
- `<STRATEGY>` ：sma、ema、alligator (default=sma)
- `<TIME_FRAME>` ：Kline Period 1m, 15m, 1h, 4h, 1d (default=1h)
- `<DAYS>` : Number of Backtesting Days (default=365)
- `<FEE_RATE>` : Funding Rate (default=0.001)
- `<PRINCIPAL>` : Initial Principal (default=10_000.0)

## Run Automated Trading