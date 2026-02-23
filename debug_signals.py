# =============================================================================
# DEBUG_SIGNALS.py — Check Waarom Geen Signalen
# =============================================================================
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

if not mt5.initialize():
    print("❌ MT5 init failed")
    exit()

symbol = "XAUUSD"
timeframe = mt5.TIMEFRAME_M15
start = datetime(2024, 10, 1)
end = datetime.now()

rates = mt5.copy_rates_range(symbol, timeframe, start, end)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

print("="*70)
print("DEBUG: Waarom Geen Signalen?")
print("="*70)

# Bereken EMA 50
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# Bereken resistance (20 candles)
lookback = 20
df['resistance'] = df['high'].rolling(window=lookback).max()
df['support'] = df['low'].rolling(window=lookback).min()

# Check laatste 50 candles
print(f"\n📊 Laatste 50 candles analyse:\n")
print(f"{'Time':<20} {'Close':<10} {'EMA50':<10} {'Resistance':<12} {'Above EMA?':<12} {'Above Res?':<12}")
print("-"*70)

for idx in range(-50, -1):
    row = df.iloc[idx]
    above_ema = row['close'] > row['ema_50'] * 1.001
    above_res = row['close'] > row['resistance']
    
    print(f"{str(row.name):<20} {row['close']:<10.2f} {row['ema_50']:<10.2f} {row['resistance']:<12.2f} {str(above_ema):<12} {str(above_res):<12}")

# Tel hoeveel candles voldoen aan LONG conditions
long_conditions = (df['close'] > df['ema_50'] * 1.001) & (df['close'] > df['resistance'])
print(f"\n✅ Candles die voldoen aan LONG conditions: {long_conditions.sum()}")

# Tel hoeveel candles voldoen aan SHORT conditions
short_conditions = (df['close'] < df['ema_50'] * 0.999) & (df['close'] < df['support'])
print(f"✅ Candles die voldoen aan SHORT conditions: {short_conditions.sum()}")

print("\n" + "="*70)
if long_conditions.sum() == 0 and short_conditions.sum() == 0:
    print("❌ PROBLEEM: Geen enkele candle voldoet aan de conditions!")
    print("\nMogelijke oorzaken:")
    print("1. Resistance is ALTIJD boven prijs (markt in downtrend)")
    print("2. EMA 50 buffer (1.001) is te streng")
    print("3. Lookback 20 is te kort (resistance te dichtbij)")
else:
    print("✅ Er ZIJN candles die voldoen — probleem zit ergens anders")
print("="*70)

mt5.shutdown()
