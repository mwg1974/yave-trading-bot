# =============================================================================
# STRATEGY — EMA 5/20 Crossover (EURUSD Versie)
# =============================================================================
# Dit is de BEPROEFDE versie die 43.9% win rate gaf op XAUUSD M15
# Verwacht: 45-50% win rate op EURUSD M15 (minder ruis, lagere kosten)
# =============================================================================
import pandas as pd
import numpy as np
import config

def generate_final_signals(df, params):
    """
    Genereer EMA crossover signalen.
    
    LONG: EMA fast kruist boven EMA slow
    SHORT: EMA fast kruist onder EMA slow
    """
    df = df.copy()
    df['signal'] = 0
    
    # EMA's berekenen
    ema_fast = params.get('ema_fast', config.EMA_FAST_DEFAULT)
    ema_slow = params.get('ema_slow', config.EMA_SLOW_DEFAULT)
    
    df['ema_fast'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
    
    # Crossover detectie
    # LONG: EMA fast kruist boven EMA slow
    df.loc[
        (df['ema_fast'] > df['ema_slow']) & 
        (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)), 
        'signal'
    ] = 1
    
    # SHORT: EMA fast kruist onder EMA slow
    df.loc[
        (df['ema_fast'] < df['ema_slow']) & 
        (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)), 
        'signal'
    ] = -1
    
    # Positie (houd tot tegenovergesteld signaal)
    df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    
    # Debug info
    total_signals = (df['signal'] != 0).sum()
    long_signals = (df['signal'] == 1).sum()
    short_signals = (df['signal'] == -1).sum()
    print(f"   📊 Signal debug: {total_signals} signalen gegenereerd")
    print(f"   📊 Long signalen: {long_signals}")
    print(f"   📊 Short signalen: {short_signals}")
    
    return df

def calculate_dynamic_lot_size(equity, risk_pct, stop_loss_points, symbol='EURUSD'):
    """
    Bereken lot size op basis van risk %.
    
    Voor EURUSD: 1 pip = $10 per standaard lot, $1 per 0.1 lot
    1 point = 0.1 pip = $1 per standaard lot, $0.10 per 0.1 lot
    """
    if equity is None or equity <= 0:
        equity = config.INITIAL_CAPITAL
    
    if stop_loss_points is None or stop_loss_points <= 0:
        stop_loss_points = config.STOP_LOSS_POINTS
    
    # EURUSD: 1 point = 0.00001 = $0.10 per 0.1 lot
    pip_value_per_01lot = 0.10
    risk_amount = equity * (risk_pct / 100)
    sl_cost_per_01lot = stop_loss_points * pip_value_per_01lot
    
    if sl_cost_per_01lot == 0:
        return config.LOT_SIZE_BASE
    
    lot_size = (risk_amount / sl_cost_per_01lot) * 0.1
    lot_size = round(lot_size, 2)
    lot_size = max(0.01, min(lot_size, 5.0))  # Max 5.0 lot als safety
    return lot_size

def check_stop_loss_tp(entry_price, current_high, current_low, position, sl_points, tp_points):
    """
    Check of SL of TP is geraakt.
    
    Voor EURUSD: 1 point = 0.00001 (5e decimaal)
    """
    if entry_price is None:
        return 'CONTINUE', None
    
    if position == 1:  # LONG
        sl_price = entry_price - (sl_points * 0.00001)
        tp_price = entry_price + (tp_points * 0.00001)
        
        if current_low <= sl_price:
            return 'SL', sl_price
        elif current_high >= tp_price:
            return 'TP', tp_price
            
    elif position == -1:  # SHORT
        sl_price = entry_price + (sl_points * 0.00001)
        tp_price = entry_price - (tp_points * 0.00001)
        
        if current_high >= sl_price:
            return 'SL', sl_price
        elif current_low <= tp_price:
            return 'TP', tp_price
    
    return 'CONTINUE', None

def apply_trailing_stop(entry_price, current_price, position, activation_points, trail_points):
    """
    Bereken trailing stop niveau.
    
    Activeert na activation_points winst, trailt met trail_points afstand.
    """
    if entry_price is None:
        return None
    
    # Bereken onge realiseerde winst in points
    if position == 1:
        unrealized_pnl_points = (current_price - entry_price) / 0.00001
    else:
        unrealized_pnl_points = (entry_price - current_price) / 0.00001
    
    if unrealized_pnl_points < activation_points:
        return None  # Nog niet activeren
    
    if position == 1:  # Long: trail omhoog
        new_sl = current_price - (trail_points * 0.00001)
        original_sl = entry_price - (config.STOP_LOSS_POINTS * 0.00001)
        return max(original_sl, new_sl)  # Niet lager dan originele SL
    elif position == -1:  # Short: trail omlaag
        new_sl = current_price + (trail_points * 0.00001)
        original_sl = entry_price + (config.STOP_LOSS_POINTS * 0.00001)
        return min(original_sl, new_sl)  # Niet hoger dan originele SL
    
    return None