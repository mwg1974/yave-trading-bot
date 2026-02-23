# =============================================================================
# INTEGRATION_TEST.py — Test Alle Modules Samen
# =============================================================================
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Import onze modules
import multi_timeframe
import session_filter
import breakout_detector

def run_integration_test():
    """
    Test de complete strategie flow:
    1. Haal multi-timeframe data op
    2. Check session filter
    3. Bepaal H4 trend
    4. Bereken H1 support/resistance
    5. Check M15 voor breakout entry
    6. Return: TRADE of NO TRADE
    """
    print("="*70)
    print("YAVE BREAKOUT STRATEGY — INTEGRATION TEST")
    print("="*70)
    
    # Initialiseer MT5
    if not mt5.initialize():
        print("❌ MT5 init failed")
        return None
    
    symbol = "XAUUSD"
    end_date = datetime.now()
    start_date = datetime(end_date.year, end_date.month, 1)
    
    # =========================================================================
    # STAP 1: Multi-Timeframe Data
    # =========================================================================
    print("\n📡 STAP 1: Loading multi-timeframe data...")
    data = multi_timeframe.get_multi_timeframe_data(symbol, start_date, end_date)
    
    if len(data) < 3:
        print("❌ Niet alle timeframes geladen")
        mt5.shutdown()
        return None
    
    h4_df = data['H4']
    h1_df = data['H1']
    m15_df = data['M15']
    
    print(f"✅ H4: {len(h4_df)} candles")
    print(f"✅ H1: {len(h1_df)} candles")
    print(f"✅ M15: {len(m15_df)} candles")
    
    # =========================================================================
    # STAP 2: Session Filter
    # =========================================================================
    print("\n⏰ STAP 2: Checking session filter...")
    current_time = datetime.now()
    is_session = session_filter.is_trading_session(current_time)
    session_name = session_filter.get_session_name(current_time)
    
    print(f"Huidige tijd: {current_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Sessie: {session_name}")
    print(f"Trade toegestaan: {'✅ JA' if is_session else '❌ NEE'}")
    
    if not is_session:
        print("\n⚠️  Buiten trading sessie - Geen trades nu")
        print("   Wacht tot London Open (08:00) of London/NY Overlap (14:00)")
        mt5.shutdown()
        return {'signal': 'NO_TRADE', 'reason': 'Outside trading session'}
    
    # =========================================================================
    # STAP 3: H4 Trend Direction
    # =========================================================================
    print("\n📈 STAP 3: Determining H4 trend...")
    trend = breakout_detector.get_h4_trend_direction(h4_df)
    print(f"H4 Trend: {trend}")
    
    if trend == 'NEUTRAL':
        print("\n⚠️  Geen duidelijke trend - Geen trades nu")
        mt5.shutdown()
        return {'signal': 'NO_TRADE', 'reason': 'Neutral trend'}
    
    # =========================================================================
    # STAP 4: H1 Support/Resistance Levels
    # =========================================================================
    print("\n📊 STAP 4: Calculating support/resistance levels...")
    levels = breakout_detector.calculate_support_resistance(h1_df, lookback=20)
    
    if levels is None:
        print("❌ Niet genoeg data voor levels")
        mt5.shutdown()
        return None
    
    print(f"Resistance: {levels['resistance']:.2f}")
    print(f"Support: {levels['support']:.2f}")
    print(f"Range: {levels['resistance'] - levels['support']:.2f} points")
    
    # =========================================================================
    # STAP 5: Check M15 voor Breakout Entry
    # =========================================================================
    print("\n🎯 STAP 5: Checking for breakout entry...")
    current_price = m15_df['close'].iloc[-1]
    print(f"Current M15 Price: {current_price:.2f}")
    
    signal = None
    
    if trend == 'BULLISH':
        print(f"\n🎯 Strategy: Look for LONG breakout above {levels['resistance']:.2f}")
        
        if current_price > levels['resistance']:
            # Check laatste M15 candle voor valide breakout
            last_candle = m15_df.iloc[-1]
            breakout = breakout_detector.check_breakout_with_wick_filter(
                last_candle, levels, 'long', min_breakout_points=50
            )
            
            if breakout and breakout['valid']:
                signal = {
                    'signal': 'LONG',
                    'entry_price': current_price,
                    'stop_loss': current_price - (500 * 0.01),  # 50 pips
                    'take_profit': current_price + (1000 * 0.01),  # 100 pips (1:2)
                    'reason': 'Bullish trend + breakout above resistance',
                    'confidence': 'HIGH'
                }
                print(f"✅ LONG SIGNAL GENERATED!")
            else:
                print("⏳ Price above resistance but no confirmed breakout yet")
                signal = {'signal': 'NO_TRADE', 'reason': 'Waiting for confirmed breakout'}
        else:
            distance = levels['resistance'] - current_price
            print(f"⏳ Price {distance:.2f} points below resistance - Waiting...")
            signal = {'signal': 'NO_TRADE', 'reason': 'Price below resistance'}
    
    elif trend == 'BEARISH':
        print(f"\n🎯 Strategy: Look for SHORT breakout below {levels['support']:.2f}")
        
        if current_price < levels['support']:
            last_candle = m15_df.iloc[-1]
            breakout = breakout_detector.check_breakout_with_wick_filter(
                last_candle, levels, 'short', min_breakout_points=50
            )
            
            if breakout and breakout['valid']:
                signal = {
                    'signal': 'SHORT',
                    'entry_price': current_price,
                    'stop_loss': current_price + (500 * 0.01),  # 50 pips
                    'take_profit': current_price - (1000 * 0.01),  # 100 pips (1:2)
                    'reason': 'Bearish trend + breakout below support',
                    'confidence': 'HIGH'
                }
                print(f"✅ SHORT SIGNAL GENERATED!")
            else:
                print("⏳ Price below support but no confirmed breakout yet")
                signal = {'signal': 'NO_TRADE', 'reason': 'Waiting for confirmed breakout'}
        else:
            distance = current_price - levels['support']
            print(f"⏳ Price {distance:.2f} points above support - Waiting...")
            signal = {'signal': 'NO_TRADE', 'reason': 'Price above support'}
    
    # =========================================================================
    # RESULTAAT
    # =========================================================================
    print("\n" + "="*70)
    print("📋 INTEGRATION TEST RESULT")
    print("="*70)
    
    if signal and signal['signal'] in ['LONG', 'SHORT']:
        print(f"✅ TRADE SIGNAL: {signal['signal']}")
        print(f"   Entry: {signal['entry_price']:.2f}")
        print(f"   Stop Loss: {signal['stop_loss']:.2f}")
        print(f"   Take Profit: {signal['take_profit']:.2f}")
        print(f"   Reason: {signal['reason']}")
        print(f"   Confidence: {signal['confidence']}")
    else:
        print("❌ NO TRADE SIGNAL")
        print(f"   Reason: {signal['reason'] if signal else 'Unknown'}")
    
    print("="*70)
    
    mt5.shutdown()
    return signal

# =============================================================================
# RUN TEST
# =============================================================================
if __name__ == "__main__":
    result = run_integration_test()
    
    print("\n✅ Integration test completed!")
    print(f"Result: {result}")
