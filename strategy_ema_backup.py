# =============================================================================
# STRATEGY — Signal Generation with Filters & Risk Management
# =============================================================================
import pandas as pd
import numpy as np
import config

def generate_crossover_signals(df, ema_fast, ema_slow):
    """Genereer basis crossover signalen."""
    df = df.copy()
    
    # Crossover detectie
    df['bull_cross'] = (df[f'ema_{ema_fast}'] > df[f'ema_{ema_slow}']) & \
                       (df[f'ema_{ema_fast}'].shift(1) <= df[f'ema_{ema_slow}'].shift(1))
    df['bear_cross'] = (df[f'ema_{ema_fast}'] < df[f'ema_{ema_slow}']) & \
                       (df[f'ema_{ema_fast}'].shift(1) >= df[f'ema_{ema_slow}'].shift(1))
    
    return df

def apply_trend_filter(df, ema_trend):
    """Voeg EMA trendfilter toe."""
    df = df.copy()
    # Long alleen als prijs > EMA_trend
    df['trend_long_ok'] = df['close'] > df[f'ema_{ema_trend}']
    # Short alleen als prijs < EMA_trend
    df['trend_short_ok'] = df['close'] < df[f'ema_{ema_trend}']
    return df

def apply_fvg_filter(df):
    """Voeg FVG confirmatie filter toe."""
    df = df.copy()
    # Long alleen met recente bullish FVG
    df['fvg_long_ok'] = df['fvg_bullish_recent'] >= 1
    # Short alleen met recente bearish FVG
    df['fvg_short_ok'] = df['fvg_bearish_recent'] >= 1
    return df

def generate_final_signals(df, params):
    """
    Combineer alle componenten naar definitieve signalen.
    params: dict met ema_fast, ema_slow, use_trend_filter, use_fvg_filter
    """
    df = df.copy()
    
    # 1. Basis crossovers
    df = generate_crossover_signals(df, params['ema_fast'], params['ema_slow'])
    
    # 2. Optionele filters
    if params.get('use_trend_filter', True):
        df = apply_trend_filter(df, config.EMA_TREND_DEFAULT)
    else:
        df['trend_long_ok'] = True
        df['trend_short_ok'] = True
    
    if params.get('use_fvg_filter', True):
        df = apply_fvg_filter(df)
    else:
        df['fvg_long_ok'] = True
        df['fvg_short_ok'] = True
    
    # 3. Combineer naar signal
    df['signal'] = 0
    df.loc[df['bull_cross'] & df['trend_long_ok'] & df['fvg_long_ok'], 'signal'] = 1
    df.loc[df['bear_cross'] & df['trend_short_ok'] & df['fvg_short_ok'], 'signal'] = -1
    
    # 4. Positie (houd tot tegenovergesteld signaal)
    df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    
    return df

def calculate_dynamic_lot_size(equity, risk_pct, stop_loss_points, symbol='XAUUSD'):
    """
    Bereken lot size op basis van risk % en stop loss.
    Formule: lot = (equity * risk%) / (SL_points * pip_value)
    Voor XAUUSD: 1 point = $0.10 per 0.1 lot
    """
    # Null checks
    if equity is None or equity <= 0:
        equity = config.INITIAL_CAPITAL
    
    if stop_loss_points is None or stop_loss_points <= 0:
        stop_loss_points = config.STOP_LOSS_POINTS
    
    pip_value_per_01lot = 0.10  # USD per point voor 0.1 lot XAUUSD
    risk_amount = equity * (risk_pct / 100)
    sl_cost_per_01lot = stop_loss_points * pip_value_per_01lot
    
    if sl_cost_per_01lot == 0:
        return config.LOT_SIZE_BASE
    
    lot_size = (risk_amount / sl_cost_per_01lot) * 0.1
    # Round naar broker granularity (meestal 0.01)
    lot_size = round(lot_size, 2)
    # Min/max bounds
    lot_size = max(0.01, min(lot_size, 5.0))  # Max 5.0 lot als safety
    return lot_size

def check_stop_loss_tp(entry_price, current_high, current_low, position, sl_points, tp_points):
    """
    Check of SL of TP is geraakt.
    Returns: ('SL', exit_price), ('TP', exit_price), of ('CONTINUE', None)
    
    Voor XAUUSD: 1 point = 0.01 price move
    """
    if entry_price is None:
        return 'CONTINUE', None
    
    # Bereken SL en TP prijzen
    if position == 1:  # LONG
        sl_price = entry_price - (sl_points * 0.01)
        tp_price = entry_price + (tp_points * 0.01)
        
        # Check SL eerst (priority)
        if current_low <= sl_price:
            return 'SL', sl_price
        # Check TP
        elif current_high >= tp_price:
            return 'TP', tp_price
            
    elif position == -1:  # SHORT
        sl_price = entry_price + (sl_points * 0.01)
        tp_price = entry_price - (tp_points * 0.01)
        
        # Check SL eerst (priority)
        if current_high >= sl_price:
            return 'SL', sl_price
        # Check TP
        elif current_low <= tp_price:
            return 'TP', tp_price
    
    return 'CONTINUE', None

def apply_trailing_stop(entry_price, current_price, position, activation_points, trail_points):
    """
    Bereken trailing stop niveau.
    Returns: nieuwe stop loss prijs of None als nog niet geactiveerd
    """
    if entry_price is None:
        return None
    
    unrealized_pnl_points = abs(current_price - entry_price) / 0.01
    
    if unrealized_pnl_points < activation_points:
        return None  # Nog niet activeren
    
    if position == 1:  # Long: trail omhoog
        new_sl = current_price - (trail_points * 0.01)
        original_sl = entry_price - (config.STOP_LOSS_POINTS * 0.01)
        return max(original_sl, new_sl)  # Niet lager dan originele SL
    elif position == -1:  # Short: trail omlaag
        new_sl = current_price + (trail_points * 0.01)
        original_sl = entry_price + (config.STOP_LOSS_POINTS * 0.01)
        return min(original_sl, new_sl)  # Niet hoger dan originele SL
    
    return None