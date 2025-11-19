import pandas as pd
import numpy as np

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(df: pd.DataFrame, n: int) -> pd.Series:
    return true_range(df).rolling(n, min_periods=n).mean()

def sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = 365*24) -> float:
    # hourly frequency default
    ex = returns - rf/periods_per_year
    if ex.std(ddof=0) == 0:
        return 0.0
    return (ex.mean() / ex.std(ddof=0)) * (periods_per_year ** 0.5)

def max_drawdown(equity_curve: pd.Series) -> float:
    roll_max = equity_curve.cummax()
    dd = equity_curve/roll_max - 1.0
    return dd.min() if len(dd) else 0.0