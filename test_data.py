# test_data.py
import MetaTrader5 as mt5
from datetime import datetime

if not mt5.initialize():
    print("❌ MT5 init failed")
    exit()

symbol = "XAUUSD"
timeframe = mt5.TIMEFRAME_M15
start = datetime(2024, 10, 1)
end = datetime.now()

print(f"📡 Requesting {symbol} M15 from {start} to {end}")

# Forceer symbool selectie
mt5.symbol_select(symbol, True)

# Haal data op
rates = mt5.copy_rates_range(symbol, timeframe, start, end)

if rates is None:
    print("❌ rates = None")
    print(f"MT5 Error: {mt5.last_error()}")
elif len(rates) == 0:
    print("❌ rates is empty (0 candles)")
    print("   Open XAUUSD chart in MT5 and scroll back to load history")
else:
    print(f"✅ SUCCESS! {len(rates)} candles loaded")
    print(f"   First candle: {rates[0]['time']}")
    print(f"   Last candle: {rates[-1]['time']}")
    print(f"   First close: {rates[0]['close']}")
    print(f"   Last close: {rates[-1]['close']}")

mt5.shutdown()
