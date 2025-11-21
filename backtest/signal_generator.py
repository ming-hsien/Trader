import pandas as pd
import backtest.sma as sma
import backtest.ema as ema
import backtest.alligator as alligator

def generate_signal(df, strategy, trader=False):
    df_sig = None
    
    if strategy == "sma":
        df_sig = sma.compute_signals(df)
    elif strategy == "ema":
        df_sig = ema.compute_signals(df)
    elif strategy == "alligator":
        df_sig = alligator.compute_signals(df)
    
    if trader:  
        # 用倒數第二根避免 repaint
        last = df_sig.iloc[-2]
        return last["signal_long"], last["signal_exit"]
    
    return df_sig
