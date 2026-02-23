# =============================================================================
# STRATEGY — Breakout (GEFIXTE VERSIE)
# =============================================================================
import pandas as pd
import numpy as np
import config

def generate_final_signals(df, params):
    """
    Genereer breakout signalen — GEFIXT!
    """
    df = df.copy()
    df['signal'] = 0
    
    # Bereken EMA 50 voor trend
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # Bereken support/resistance (vorige 20 candles, NIET inclusief huidige)
    lookback = params.get('breakout_lookback', 20)
    df['resistance'] = df['high'].shift(1).rolling(window=lookback, min_periods=lookback).max()
    df['support'] = df['low'].shift(1).rolling(window=lookback, min_periods=lookback).min()
    
    # Genereer signalen
    for idx in range(lookback + 1, len(df)):
        current_close = df['close'].iloc[idx]
        ema_50 = df['ema_50'].iloc[idx]
        resistance = df['resistance'].iloc[idx]
        support = df['support'].iloc[idx]
        
        # Trend bepalen
        if current_close > ema_50 * 1.001:
            trend = 'BULLISH'
        elif current_close < ema_50 * 0.999:
            trend = 'BEARISH'
        else:
            continue
        
        # Breakout check (prijs moet boven resistance van VORIGE candles)
        if trend == 'BULLISH' and current_close > resistance:
            df.iloc[idx, df.columns.get_loc('signal')] = 1
        elif trend == 'BEARISH' and current_close < support:
            df.iloc[idx, df.columns.get_loc('signal')] = -1
    
    # Positie
    df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    
    # Debug info
    total_signals = (df['signal'] != 0).sum()
    print(f"   📊 Signal debug: {total_signals} signalen gegenereerd")
    print(f"   📊 Long signalen: {(df['signal'] == 1).sum()}")
    print(f"   📊 Short signalen: {(df['signal'] == -1).sum()}")
    
    return df

# ... (rest van de functies hetzelfde als eerder)
def calculate_dynamic_lot_size(equity, risk_pct, stop_loss_points, symbol='XAUUSD'):
    if equity is None or equity <= 0:
        equity = config.INITIAL_CAPITAL
    if stop_loss_points is None or stop_loss_points <= 0:
        stop_loss_points = config.STOP_LOSS_POINTS
    pip_value_per_01lot = 0.10
    risk_amount = equity * (risk_pct / 100)
    sl_cost_per_01lot = stop_loss_points * pip_value_per_01lot
    if sl_cost_per_01lot == 0:
        return config.LOT_SIZE_BASE
    lot_size = (risk_amount / sl_cost_per_01lot) * 0.1
    lot_size = round(lot_size, 2)
    lot_size = max(0.01, min(lot_size, 5.0))
    return lot_size

def check_stop_loss_tp(entry_price, current_high, current_low, position, sl_points, tp_points):
    if entry_price is None:
        return 'CONTINUE', None
    if position == 1:
        sl_price = entry_price - (sl_points * 0.01)
        tp_price = entry_price + (tp_points * 0.01)
        if current_low <= sl_price:
            return 'SL', sl_price
        elif current_high >= tp_price:
            return 'TP', tp_price
    elif position == -1:
        sl_price = entry_price + (sl_points * 0.01)
        tp_price = entry_price - (tp_points * 0.01)
        if current_high >= sl_price:
            return 'SL', sl_price
        elif current_low <= tp_price:
            return 'TP', tp_price
    return 'CONTINUE', None

def apply_trailing_stop(entry_price, current_price, position, activation_points, trail_points):
    if entry_price is None:
        return None
    unrealized_pnl_points = abs(current_price - entry_price) / 0.01
    if unrealized_pnl_points < activation_points:
        return None
    if position == 1:
        new_sl = current_price - (trail_points * 0.01)
        original_sl = entry_price - (config.STOP_LOSS_POINTS * 0.01)
        return max(original_sl, new_sl)
    elif position == -1:
        new_sl = current_price + (trail_points * 0.01)
        original_sl = entry_price + (config.STOP_LOSS_POINTS * 0.01)
        return min(original_sl, new_sl)
    return None