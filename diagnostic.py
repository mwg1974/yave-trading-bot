# diagnostic.py
import MetaTrader5 as mt5

if not mt5.initialize():
    print("❌ MT5 init failed")
    exit()

# Zoek naar goud-gerelateerde symbolen
gold_symbols = []
for sym in mt5.symbols_get():
    if 'gold' in sym.name.lower() or 'xau' in sym.name.lower():
        gold_symbols.append(sym.name)

print("📊 Goud symbolen beschikbaar bij jouw broker:")
for s in gold_symbols:
    print(f"   - {s}")

# Check ook veelgebruikte forex symbolen
print("\n📊 Top 10 symbolen:")
for sym in mt5.symbols_get()[:10]:
    print(f"   - {sym.name}")

mt5.shutdown()
