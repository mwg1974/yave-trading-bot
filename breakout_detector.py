# =============================================================================
# BREAKOUT_DETECTOR.py — Detecteer Support/Resistance Breakouts
# =============================================================================
import pandas as pd
import numpy as np

def calculate_support_resistance(df, lookback=20):
    """
    Bereken support en resistance levels gebaseerd op laatste N candles.
    
    Args:
        df: DataFrame met OHLC data (H1 timeframe)
        lookback: Aantal candles om te kijken (standaard 20)
    
    Returns:
        dict met 'resistance' en 'support' levels
    """
    if len(df) < lookback:
        return None
    
    # Resistance = hoogste high van laatste lookback candles
    resistance = df['high'].rolling(window=lookback).max().iloc[-1]
    
    # Support = laagste low van laatste lookback candles
    support = df['low'].rolling(window=lookback).min().iloc[-1]
    
    return {
        'resistance': resistance,
        'support': support,
        'lookback': lookback,
        'calculated_at': df.index[-1]
    }

def check_breakout(current_candle, levels, position='long'):
    """
    Check of er een breakout is geweest.
    
    Args:
        current_candle: DataFrame row met huidige candle (M15)
        levels: dict met resistance en support van calculate_support_resistance
        position: 'long' voor breakout boven resistance, 'short' voor breakout onder support
    
    Returns:
        dict met breakout info of None als geen breakout
    """
    if levels is None:
        return None
    
    resistance = levels['resistance']
    support = levels['support']
    
    if position == 'long':
        # Long breakout: candle close BOVEN resistance
        if current_candle['close'] > resistance:
            return {
                'type': 'LONG',
                'breakout_level': resistance,
                'breakout_price': current_candle['close'],
                'breakout_time': current_candle.name,
                'candle_high': current_candle['high'],
                'candle_low': current_candle['low'],
                'candle_close': current_candle['close'],
                'valid': True  # Close boven level = valide breakout
            }
    
    elif position == 'short':
        # Short breakout: candle close ONDER support
        if current_candle['close'] < support:
            return {
                'type': 'SHORT',
                'breakout_level': support,
                'breakout_price': current_candle['close'],
                'breakout_time': current_candle.name,
                'candle_high': current_candle['high'],
                'candle_low': current_candle['low'],
                'candle_close': current_candle['close'],
                'valid': True  # Close onder level = valide breakout
            }
    
    return None

def check_breakout_with_wick_filter(current_candle, levels, position='long', min_breakout_points=50):
    """
    Check breakout met extra filter: minimale breakout distance.
    
    Args:
        min_breakout_points: Minimale punten boven/onder level (standaard 50 = 5 pips)
    
    Returns:
        dict met breakout info of None als geen breakout
    """
    breakout = check_breakout(current_candle, levels, position)
    
    if breakout is None:
        return None
    
    # Check of breakout groot genoeg is (niet alleen een kleine pierce)
    if position == 'long':
        breakout_distance = breakout['candle_close'] - breakout['breakout_level']
    else:
        breakout_distance = breakout['breakout_level'] - breakout['candle_close']
    
    # Converteer punten naar prijs (1 point = 0.01 voor XAUUSD)
    min_distance_price = min_breakout_points * 0.01
    
    if breakout_distance >= min_distance_price:
        breakout['breakout_distance_points'] = breakout_distance / 0.01
        breakout['valid'] = True
        return breakout
    else:
        breakout['valid'] = False
        breakout['reason'] = f'Breakout too small: {breakout_distance/0.01:.1f} points < {min_breakout_points}'
        return breakout

def get_h4_trend_direction(h4_df, ema_period=50):
    """
    Bepaal H4 trend richting met EMA.
    
    Returns:
        'BULLISH', 'BEARISH', of 'NEUTRAL'
    """
    if len(h4_df) < ema_period:
        return 'NEUTRAL'
    
    # Bereken EMA 50
    ema = h4_df['close'].ewm(span=ema_period, adjust=False).mean().iloc[-1]
    current_price = h4_df['close'].iloc[-1]
    
    # Bullish als prijs > EMA
    if current_price > ema * 1.001:  # 0.1% buffer voor ruis
        return 'BULLISH'
    elif current_price < ema * 0.999:
        return 'BEARISH'
    else:
        return 'NEUTRAL'

# =============================================================================
# TEST FUNCTIE
# =============================================================================
if __name__ == "__main__":
    import MetaTrader5 as mt5
    from datetime import datetime
    
    print("="*60)
    print("BREAKOUT DETECTOR TEST")
    print("="*60)
    
    # Initialiseer MT5
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    # Haal test data op
    symbol = "XAUUSD"
    end_date = datetime.now()
    start_date = datetime(end_date.year, end_date.month, 1)  # Eerste van deze maand
    
    print(f"\n📡 Loading data: {symbol}")
    
    # H4 data voor trend
    h4_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, start_date, end_date)
    h4_df = pd.DataFrame(h4_rates)
    h4_df['time'] = pd.to_datetime(h4_df['time'], unit='s')
    h4_df.set_index('time', inplace=True)
    
    # H1 data voor support/resistance
    h1_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_date, end_date)
    h1_df = pd.DataFrame(h1_rates)
    h1_df['time'] = pd.to_datetime(h1_df['time'], unit='s')
    h1_df.set_index('time', inplace=True)
    
    # M15 data voor entry
    m15_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start_date, end_date)
    m15_df = pd.DataFrame(m15_rates)
    m15_df['time'] = pd.to_datetime(m15_df['time'], unit='s')
    m15_df.set_index('time', inplace=True)
    
    print(f"✅ H4: {len(h4_df)} candles")
    print(f"✅ H1: {len(h1_df)} candles")
    print(f"✅ M15: {len(m15_df)} candles")
    
    # Test 1: H4 Trend Direction
    print("\n" + "-"*60)
    print("TEST 1: H4 Trend Direction")
    print("-"*60)
    trend = get_h4_trend_direction(h4_df)
    print(f"H4 Trend: {trend}")
    print(f"Current H4 Close: {h4_df['close'].iloc[-1]:.2f}")
    
    # Test 2: Support/Resistance Levels
    print("\n" + "-"*60)
    print("TEST 2: Support/Resistance Levels (H1)")
    print("-"*60)
    levels = calculate_support_resistance(h1_df, lookback=20)
    if levels:
        print(f"Resistance: {levels['resistance']:.2f}")
        print(f"Support: {levels['support']:.2f}")
        print(f"Range: {levels['resistance'] - levels['support']:.2f} points")
    
    # Test 3: Check Breakouts op M15
    print("\n" + "-"*60)
    print("TEST 3: Check Breakouts (M15)")
    print("-"*60)
    
    # Check laatste 10 M15 candles voor breakouts
    recent_m15 = m15_df.iloc[-10:]
    breakouts_found = []
    
    for idx, candle in recent_m15.iterrows():
        # Check long breakout
        long_breakout = check_breakout_with_wick_filter(candle, levels, 'long')
        if long_breakout and long_breakout['valid']:
            breakouts_found.append(long_breakout)
            print(f"✅ LONG BREAKOUT @ {candle.name}")
            print(f"   Level: {long_breakout['breakout_level']:.2f}")
            print(f"   Price: {long_breakout['breakout_price']:.2f}")
            print(f"   Distance: {long_breakout['breakout_distance_points']:.1f} points")
        
        # Check short breakout
        short_breakout = check_breakout_with_wick_filter(candle, levels, 'short')
        if short_breakout and short_breakout['valid']:
            breakouts_found.append(short_breakout)
            print(f"✅ SHORT BREAKOUT @ {candle.name}")
            print(f"   Level: {short_breakout['breakout_level']:.2f}")
            print(f"   Price: {short_breakout['breakout_price']:.2f}")
            print(f"   Distance: {short_breakout['breakout_distance_points']:.1f} points")
    
    if not breakouts_found:
        print("ℹ️  Geen breakouts gevonden in laatste 10 M15 candles")
        print(f"   Current M15 Close: {m15_df['close'].iloc[-1]:.2f}")
        print(f"   Resistance: {levels['resistance']:.2f}")
        print(f"   Support: {levels['support']:.2f}")
    
    # Test 4: Combineer Alle Checks
    print("\n" + "-"*60)
    print("TEST 4: Complete Strategy Check")
    print("-"*60)
    print(f"H4 Trend: {trend}")
    print(f"Current Price: {m15_df['close'].iloc[-1]:.2f}")
    print(f"Resistance: {levels['resistance']:.2f}")
    print(f"Support: {levels['support']:.2f}")
    
    if trend == 'BULLISH':
        print("\n🎯 Strategy: Look for LONG breakouts above resistance")
        last_candle = m15_df.iloc[-1]
        if last_candle['close'] > levels['resistance']:
            print("✅ Price IS above resistance - Potential LONG setup!")
        else:
            print("⏳ Price below resistance - Waiting for breakout...")
    elif trend == 'BEARISH':
        print("\n🎯 Strategy: Look for SHORT breakouts below support")
        last_candle = m15_df.iloc[-1]
        if last_candle['close'] < levels['support']:
            print("✅ Price IS below support - Potential SHORT setup!")
        else:
            print("⏳ Price above support - Waiting for breakout...")
    else:
        print("\n⚠️  NEUTRAL trend - No trades recommended")
    
    mt5.shutdown()
    print("\n" + "="*60)
    print("✅ Breakout detector test voltooid!")
    print("="*60)
