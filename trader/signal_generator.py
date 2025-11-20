import pandas as pd

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
