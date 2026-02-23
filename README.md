# 🚀 YAVE Trading Bot v4.2

**Inverse Price Action Trading Strategy - EURUSD M15**

## 📊 Performance (Backtest)

| Metric | Value |
|--------|-------|
| **Win Rate** | 61.0% |
| **Total Return** | 19.49% (4-5 maanden) |
| **Total PnL** | +$1,949.50 |
| **Total Trades** | 244 |

## 🎯 Strategie

**Inverse Breakout (Fade Trading)**
- SHORT wanneer prijs BOVEN resistance breekt
- LONG wanneer prijs ONDER support breekt
- Stop Loss: 40 pips
- Take Profit: 90 pips (1:2.25 RR)
- Trailing Stop: Activeert bij 45 pips winst
- Max Duration: 28 candles (~7 uur)

## 🛠 Installatie

```bash
pip install -r requirements.txt
python inverse_optimized_v42.py