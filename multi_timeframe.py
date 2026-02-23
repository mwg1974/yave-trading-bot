# =============================================================================
# MULTI_TIMEFRAME.py — Haal H4 + H1 + M15 Data Op
# =============================================================================
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def get_multi_timeframe_data(symbol, start_date, end_date):
    """
    Haalt data op voor 3 timeframes: H4, H1, M15
    Returns: dict met DataFrames voor elk timeframe
    """
    timeframes = {
        'H4': mt5.TIMEFRAME_H4,
        'H1': mt5.TIMEFRAME_H1,
        'M15': mt5.TIMEFRAME_M15
    }
    
    data = {}
    
    for tf_name, tf_constant in timeframes.items():
        rates = mt5.copy_rates_range(symbol, tf_constant, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Geen data voor {tf_name}")
            continue
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        data[tf_name] = df
        print(f"✅ {tf_name}: {len(df)} candles geladen")
    
    return data

def sync_timeframes(data):
    """
    Synchroniseert timeframes zodat M15 candles alignen met H1/H4
    """
    # Voor nu: return data zoals het is
    # Later: voeg H1/H4 data toe aan M15 DataFrame voor snelle access
    return data

# Test functie
if __name__ == "__main__":
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    data = get_multi_timeframe_data(
        "XAUUSD",
        datetime(2024, 10, 1),
        datetime.now()
    )
    
    for tf, df in data.items():
        print(f"\n{tf} Data:")
        print(f"  Candles: {len(df)}")
        print(f"  Date range: {df.index[0]} to {df.index[-1]}")
        print(f"  Close price: {df['close'].iloc[-1]:.2f}")
    
    mt5.shutdown()
