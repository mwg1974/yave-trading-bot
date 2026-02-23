# =============================================================================
# YAVE BOT v3.0 — CONFIGURATIE
# =============================================================================
# Laatst bijgewerkt: Februari 2026
# Asset: EURUSD (Forex Major)
# Strategie: EMA 5/20 Crossover
# Timeframe: M15
# =============================================================================
from datetime import datetime
from enum import Enum

# ----- BASIS -----
SYMBOL = "EURUSD"               # ← VERANDERD van XAUUSD
TIMEFRAME_MT5 = "M15"
START_DATE = datetime(2024, 10, 1)
END_DATE = datetime.now()
INITIAL_CAPITAL = 10000.0
CURRENCY = "USD"

# ----- TRADING PARAMETERS -----
LOT_SIZE_BASE = 0.1
RISK_PER_TRADE_PCT = 2.0            # % van equity per trade (dynamische sizing)
STOP_LOSS_POINTS = 50               # 50 points = 5 pips voor EURUSD ✅
TAKE_PROFIT_POINTS = 100            # 100 points = 10 pips (1:2 risk-reward) ✅
TRAILING_STOP_ACTIVATION = 50       # Start trailen na 5 pips winst (1:1)
TRAILING_STOP_POINTS = 25           # Trail afstand (2.5 pips)

# ----- KOSTEN MODEL (EURUSD - Fusion Markets) -----
SPREAD_POINTS_AVG = 10              # 10 points = 1 pip gemiddeld voor EURUSD ✅
SLIPPAGE_POINTS_AVG = 5             # 5 points = 0.5 pip slippage ✅
COMMISSION_PER_LOT = 7.0            # USD per lot

# ----- EMA PARAMETERS -----
EMA_FAST_DEFAULT = 5                # EMA 5 voor snelle crossover
EMA_SLOW_DEFAULT = 20               # EMA 20 voor langzame crossover
EMA_TREND_DEFAULT = 200             # EMA 200 voor trend filter (optioneel)

# ----- STRATEGIE FLAGS -----
USE_TREND_FILTER = False            # ❌ UIT (filterde te veel goede trades)
USE_FVG_FILTER = False              # ❌ UIT (werkt niet goed)
USE_SESSION_FILTER = False          # ❌ UIT (forex is 24/5, geen session issues)
FVG_MIN_POINTS = 20
FVG_LOOKBACK = 10

# ----- OPTIMALISATIE -----
OPTIMIZE_RANGES = {
    'ema_fast': [5, 7, 9],          # Test snelle EMA's
    'ema_slow': [18, 20, 22],       # Test langzame EMA's
    'use_trend_filter': [False],    # Trend filter uitlaten
    'use_fvg_filter': [False]       # FVG uitlaten
}

# ----- WALK-FORWARD -----
WF_TRAIN_MONTHS = 3
WF_TEST_MONTHS = 1
WF_MIN_TRAIN_CANDLES = 500
WF_MIN_TEST_CANDLES = 100

# ----- FORWARD TEST -----
FORWARD_TEST_MODE = False           # ❌ UIT (eerst backtesten)
FORWARD_LOG_FILE = "yave_forward_test_log.json"
FORWARD_COMPARE_REPORT = "yave_backtest_vs_forward.md"

# ----- OUTPUT -----
SAVE_RESULTS = True
RESULTS_DIR = "yave_results"
PLOT_DPI = 150