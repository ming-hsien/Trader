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
python -m backtest.backtest --symbol <SYMBOL> --strategy <STRATEGY> --timeframe <TIME_FRAME> --days <DAYS> --fee <FEE_RATE> --initial <PRINCIPAL>
```
- `<SYMBOL>` ： XRP/USDT or BTC/USDT or ETH/USDT (default=XRP/USDT)
- `<STRATEGY>` ：sma、ema、alligator (default=sma)
- `<TIME_FRAME>` ：Kline Period 1m, 15m, 1h, 4h, 1d (default=1h)
- `<DAYS>` : Number of Backtesting Days (default=365)
- `<FEE_RATE>` : Funding Rate (default=0.001)
- `<PRINCIPAL>` : Initial Principal (default=10_000.0)

## Run Trader
### 1. Configure `config.yaml`
Locate the config.yaml file in the project root and adjust the parameters according to your needs.
```yaml
EXCHANGE: "binance"
API_KEY: "YOUR_API_KEY"
SECRET: "YOUR_SECRET"

# Trading Parameters
STRATEGY: AUTO # SMA, ALLIGATOR, EMA, AUTO

SYMBOL: XRPUSDT
TIME_FRAME: 1h
FEE_RATE: 0.001 # 0.1% per trade
EQUITY: 10.0
RISK_PER_TRADE: 0.01
MAX_DAILY_DRAWDOWN: 0.03

NAME: SmaAtrStrategy
SMA_FAST: 20
SMA_SLOW: 50
ATR_PERIOD: 14
ATR_MULT_SL: 1.0
ATR_MULT_TP: 2.0
ALLOW_SHORT: false

# Backtest Parameters
SLIPPAGE_TICKS: 1
```
Key configuration fields:

- STRATEGY – choose between SMA, EMA, ALLIGATOR, or AUTO

- SYMBOL / TIME_FRAME – market symbol and timeframe to trade

- Risk Settings – RISK_PER_TRADE, MAX_DAILY_DRAWDOWN

- ATR-based SL/TP – ATR_MULT_SL, ATR_MULT_TP

- ALLOW_SHORT – enable or disable short positions

- SLIPPAGE_TICKS – simulated slippage during backtest

Make sure to insert your own API key/secret if running live.


### 2. Run the Trading Bot
After adjusting the configuration, start the bot with:
```bash
python -m trader.trader_bot
```