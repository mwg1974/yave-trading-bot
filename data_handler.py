# =============================================================================
# DATA HANDLER — MT5 Integration + Validation
# =============================================================================
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import config

def initialize_mt5():
    """Initialiseer MT5 verbinding met error handling."""
    try:
        if not mt5.initialize():
            print("❌ MT5 initialize failed")
            return False
        print("✅ MT5 initialized")
        return True
    except Exception as e:
        print(f"❌ MT5 init error: {str(e)}")
        return False

def get_data(symbol, timeframe_str, start, end):
    """
    Haalt data op van MT5 met validatie.
    Returns: DataFrame of None bij fout
    """
    try:
        # Map timeframe string naar MT5 constant
        tf_map = {
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        timeframe = tf_map.get(timeframe_str, mt5.TIMEFRAME_M15)
        
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Geen data voor {symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Validatie: check op gaps
        df = validate_and_clean_data(df, timeframe_str)
        
        print(f"✅ Data geladen: {len(df)} candles, {symbol} {timeframe_str}")
        return df
        
    except Exception as e:
        print(f"❌ Data fetch error: {str(e)}")
        return None

def validate_and_clean_data(df, timeframe_str):
    """
    Validatie en cleaning:
    - Check op missende candles
    - Vul gaps met forward-fill (conservatief)
    - Verwijder weekend candles voor XAUUSD
    """
    # Verwijder weekend data voor goud (gesloten markt)
    if config.SYMBOL == "XAUUSD":
        df = df[(df.index.dayofweek < 5)]  # Maandag-vrijdag alleen
    
    # Check tijdconsistentie
    expected_freq = {'M15': '15min', 'H1': '60min', 'H4': '4H', 'D1': 'D'}
    freq = expected_freq.get(timeframe_str, '15min')
    
    # Detecteer grote gaps (>3x verwachte interval)
    time_diff = df.index.to_series().diff()
    median_diff = time_diff.median()
    gap_threshold = median_diff * 3
    
    gaps = time_diff[time_diff > gap_threshold]
    if len(gaps) > 0:
        print(f"⚠️  Gedetecteerd {len(gaps)} grote gaps in data")
        # Optioneel: log details
        # for gap_time, gap_size in gaps.items():
        #     print(f"   Gap bij {gap_time}: {gap_size}")
    
    # Forward-fill voor kleine gaps (max 2 missende candles)
    df = df.asfreq(freq)
    df = df.ffill(limit=2)
    df = df.dropna()
    
    return df

def shutdown_mt5():
    """Sluit MT5 verbinding netjes af."""
    try:
        mt5.shutdown()
        print("✅ MT5 shutdown")
    except:
        pass
