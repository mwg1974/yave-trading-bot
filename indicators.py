# =============================================================================
# INDICATORS — EMA + Fair Value Gap Detection (FIXED)
# =============================================================================
import pandas as pd
import numpy as np
import config

def calculate_ema_series(df, column='close', spans=None):
    """
    Bereken meerdere EMA's in één keer.
    spans: list van perioden, bijv. [9, 21, 200]
    """
    df = df.copy()
    if spans is None:
        spans = [config.EMA_FAST_DEFAULT, config.EMA_SLOW_DEFAULT, config.EMA_TREND_DEFAULT]
    
    for span in spans:
        col_name = f'ema_{span}'
        # Check of al bestaat om dubbel werk te voorkomen
        if col_name not in df.columns:
            df[col_name] = df[column].ewm(span=span, adjust=False).mean()
    
    return df

def detect_fvg(df, min_points=None, lookback=None):
    """
    Detecteer Fair Value Gaps met size validatie.
    """
    df = df.copy()
    min_pts = min_points or config.FVG_MIN_POINTS
    lb = lookback or config.FVG_LOOKBACK
    
    # Bereken gap sizes in points (voor XAUUSD: 1 point = 0.01)
    df['fvg_bullish_gap'] = df['low'] - df['high'].shift(2)
    df['fvg_bearish_gap'] = df['low'].shift(2) - df['high']
    
    # Flag alleen als gap > minimum en positief
    df['fvg_bullish'] = (df['fvg_bullish_gap'] > (min_pts * 0.01)).astype(int)
    df['fvg_bearish'] = (df['fvg_bearish_gap'] > (min_pts * 0.01)).astype(int)
    
    # Recent FVG? (rolling window)
    df['fvg_bullish_recent'] = df['fvg_bullish'].rolling(window=lb, min_periods=1).max()
    df['fvg_bearish_recent'] = df['fvg_bearish'].rolling(window=lb, min_periods=1).max()
    
    # Cleanup tijdelijke kolommen
    df.drop(columns=['fvg_bullish_gap', 'fvg_bearish_gap'], inplace=True, errors='ignore')
    
    return df

def calculate_all_indicators(df, params=None):
    """
    Wrapper: bereken alle indicatoren voor strategie.
    params: dict met ema_fast, ema_slow (voor optimalisatie)
    """
    # Bepaal welke EMA spans we nodig hebben
    if params:
        spans = [
            params.get('ema_fast', config.EMA_FAST_DEFAULT),
            params.get('ema_slow', config.EMA_SLOW_DEFAULT),
            config.EMA_TREND_DEFAULT
        ]
    else:
        spans = [config.EMA_FAST_DEFAULT, config.EMA_SLOW_DEFAULT, config.EMA_TREND_DEFAULT]
    
    df = calculate_ema_series(df, spans=spans)
    df = detect_fvg(df)
    return df