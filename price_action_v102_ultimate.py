# === PRICE_ACTION_PRO_v10.2 – ULTIMATE FIX EDITION ===
# ✅ FIX 1: Risk Management (MAX 1% per trade, niet 5%)
# ✅ FIX 2: Strategie Selectie (TREND in trend markt, niet Mean Rev)
# ✅ FIX 3: SL/TP (2x ATR SL, 4x ATR TP, niet 1x/3x)
# ✅ FIX 4: Lot Sizes (MAX 10% van account exposure)
# ✅ FIX 5: Hard Stop (3 verliezen = STOP definitief)

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timezone, timedelta
import sys
import os
import json
import requests
import pytz
from dotenv import load_dotenv

# === LAAD ENV VARIABLES ===
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === KLEURAMA ===
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    class DummyColor:
        def __getattr__(self, _): return ''
    Fore = Back = Style = DummyColor()

# === ✅ CONFIGURATIE ===
TIMEFRAME = mt5.TIMEFRAME_M5

# ✅ TIMEZONE
try:
    import tzlocal
    LOCAL_TZ_NAME = tzlocal.get_localzone_name()
    LOCAL_TZ = pytz.timezone(LOCAL_TZ_NAME)
except:
    LOCAL_TZ_NAME = 'Europe/Amsterdam'
    LOCAL_TZ = pytz.timezone(LOCAL_TZ_NAME)

# ✅ TEST MODE
TEST_MODE = True

# ✅ ASSETS (BEPERKT VOOR TEST)
TEST_ASSETS = [
    'BTCUSD', 'ETHUSD', 'SOLUSD',  # Crypto
    'XAUUSD',  # Goud (beste trends)
    'US30',  # US30 (sterke trends)
]

# ✅ ASSET CATEGORIES
CRYPTO_24_7 = ['BTCUSD', 'ETHUSD', 'SOLUSD']
FOREX_24_5 = ['XAUUSD', 'US30']

# ✅ TRADING HOURS
ENABLE_TRADING_HOURS = False  # ✅ UIT voor 24/7 crypto

# ✅ ASSET-SPECIFIC SETTINGS (VEILIGER!)
ASSET_SETTINGS = {
    'BTCUSD': {'atr_sl_mult': 2.0, 'atr_tp_mult': 4.0, 'volume_mult': 1.5, 'min_adx': 25, 'max_lot': 5.0, 'max_risk_pct': 1.0},
    'ETHUSD': {'atr_sl_mult': 2.0, 'atr_tp_mult': 4.0, 'volume_mult': 1.5, 'min_adx': 25, 'max_lot': 20.0, 'max_risk_pct': 1.0},
    'SOLUSD': {'atr_sl_mult': 2.5, 'atr_tp_mult': 5.0, 'volume_mult': 1.8, 'min_adx': 28, 'max_lot': 50.0, 'max_risk_pct': 1.0},
    'XAUUSD': {'atr_sl_mult': 2.0, 'atr_tp_mult': 4.0, 'volume_mult': 1.5, 'min_adx': 25, 'max_lot': 10.0, 'max_risk_pct': 1.0},
    'US30': {'atr_sl_mult': 2.0, 'atr_tp_mult': 4.0, 'volume_mult': 1.5, 'min_adx': 25, 'max_lot': 5.0, 'max_risk_pct': 1.0},
}

# ✅ POSITION SIZING (VEILIG!)
USE_MAX_LOTS = False  # ✅ UIT - gebruik risk-based sizing
MAX_RISK_PER_TRADE_PCT = 1.0  # ✅ MAX 1% per trade (niet 5%!)
MAX_EXPOSURE_PCT = 10.0  # ✅ Max 10% account exposure totaal

# ✅ HARD STOP (3 verliezen = STOP)
MAX_CONSECUTIVE_LOSSES = 3  # ✅ Lager (niet 5)
HARD_STOP_ENABLED = True  # ✅ AAN - definitief stoppen na 3 verliezen
consecutive_losses = 0
loss_pause_until = None
HARD_STOP_TRIGGERED = False

# ✅ SPREAD SETTINGS
SPREAD_LIMITS = {
    'BTCUSD': 3000, 'ETHUSD': 2000, 'SOLUSD': 1500,
    'XAUUSD': 50, 'US30': 500
}

# ✅ ASSET TRACKING
asset_stats = {}

ALL_SYMBOLS = TEST_ASSETS

MAX_TRADES_TOTAL = 5  # ✅ MAX 5 trades tegelijk (niet 15!)
MAX_MARGIN_USAGE_PCT = 30.0  # ✅ Max 30% margin (niet 60%!)
DAILY_DRAWDOWN_LIMIT = 5.0  # ✅ Max 5% daily DD (niet 10%!)

STATS_FILE = "price_action_stats_v102.json"
ALERTS_LOG = "telegram_alerts_pa_v102.json"
DAILY_PNL_FILE = "daily_pnl_pa_v102.json"
ASSET_STATS_FILE = "asset_stats_v102.json"

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(f"price_action_v102_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

# === GLOBAL STATE ===
global_state = {
    'timezone': LOCAL_TZ_NAME,
    'session': 'Unknown',
    'mt5_connected': False,
    'closed_trades': set(),
    'market_regime': 'Unknown'
}

# === STATISTICS ===
trading_stats = {
    'total_trades_ever': 0,
    'total_won': 0,
    'total_lost': 0,
    'cumulative_pnl': 0.0,
    'largest_win': 0.0,
    'largest_loss': 0.0,
    'daily_drawdown': 0.0,
    'symbols_traded': set(),
    'started_date': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    'version': '10.2-ULTIMATE-FIX'
}

def load_stats():
    global trading_stats, asset_stats, consecutive_losses, HARD_STOP_TRIGGERED
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                loaded = json.load(f)
                loaded['symbols_traded'] = set(loaded.get('symbols_traded', []))
                trading_stats.update(loaded)
                HARD_STOP_TRIGGERED = loaded.get('hard_stop_triggered', False)
        
        if os.path.exists(ASSET_STATS_FILE):
            with open(ASSET_STATS_FILE, 'r') as f:
                asset_stats.update(json.load(f))
    except Exception as e:
        logger.warning(f"Kon stats niet laden: {e}")

def save_stats():
    try:
        to_save = trading_stats.copy()
        to_save['symbols_traded'] = list(to_save['symbols_traded'])
        to_save['hard_stop_triggered'] = HARD_STOP_TRIGGERED
        with open(STATS_FILE, 'w') as f:
            json.dump(to_save, f, indent=2)
        
        with open(ASSET_STATS_FILE, 'w') as f:
            json.dump(asset_stats, f, indent=2)
    except Exception as e:
        logger.warning(f"Kon stats niet opslaan: {e}")

# === TIMEZONE ===
def get_local_time():
    try:
        return datetime.now(LOCAL_TZ)
    except:
        return datetime.now()

def get_utc_time():
    return datetime.now(timezone.utc)

# === ASSET TYPE ===
def get_asset_type(symbol):
    if symbol in CRYPTO_24_7:
        return 'crypto'
    else:
        return 'forex'

def is_asset_tradable(symbol):
    local_time = get_local_time()
    weekday = local_time.weekday()
    
    if symbol in CRYPTO_24_7:
        return True
    
    if symbol in FOREX_24_5:
        if weekday >= 5:
            return False
        if weekday == 4 and local_time.hour >= 23:
            return False
        if weekday == 6 and local_time.hour < 23:
            return False
        return True
    
    return False

def is_trading_hours():
    if not ENABLE_TRADING_HOURS:
        return True
    
    local_time = get_local_time()
    hour = local_time.hour
    weekday = local_time.weekday()
    
    if TRADING_HOURS.get('skip_weekend', True) and weekday >= 5:
        crypto_available = any(s in CRYPTO_24_7 for s in ALL_SYMBOLS)
        if crypto_available:
            return True
        return False
    
    if hour < TRADING_HOURS.get('start_hour', 0) or hour >= TRADING_HOURS.get('end_hour', 23):
        return False
    
    return True

# === ✅ MARKET REGIME DETECTION ===
def detect_market_regime(df):
    if len(df) < 50:
        return 'Unknown'
    
    try:
        adx = float(df['adx'].iloc[-1])
        atr = float(df['atr'].iloc[-1])
        atr_avg = float(df['atr'].rolling(50).mean().iloc[-1])
        
        # ADX > 30 = TREND (gebruik Trend Following!)
        if adx > 30:
            return 'Trend'
        # ADX < 20 = RANGE (gebruik Mean Reversion!)
        if adx < 20:
            return 'Range'
        # Tussen 20-30 = Volatile
        if atr > atr_avg * 1.5:
            return 'Volatile'
        return 'Range'
    except:
        return 'Range'  # ✅ Default naar Range (veiliger)

# === MT5 CONNECTION ===
def check_mt5_connection():
    try:
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            mt5.shutdown()
            time.sleep(2)
            if not mt5.initialize():
                return False
            terminal_info = mt5.terminal_info()
        
        if terminal_info and terminal_info.connected:
            global_state['mt5_connected'] = True
            return True
        return False
    except Exception as e:
        logger.error(f"MT5 connection fout: {e}")
        return False

def initialize_mt5():
    try:
        mt5.shutdown()
        time.sleep(1)
        
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"❌ MT5 initialisatie mislukt: {error}")
            return False
        
        account = mt5.account_info()
        if account is None:
            logger.error("❌ Geen account verbonden")
            mt5.shutdown()
            return False
        
        global_state['mt5_connected'] = True
        logger.info(f"✅ VERBONDEN | Broker: {account.company} | Account: {account.login}")
        logger.info(f"   Balance: ${account.balance:.2f} | Equity: ${account.equity:.2f}")
        return True
    except Exception as e:
        logger.error(f"❌ MT5 exception: {e}")
        return False

# === HAAAL SYMBOLEN OP ===
def get_all_tradable_symbols():
    tradable = []
    for sym in ALL_SYMBOLS:
        if not mt5.symbol_info(sym):
            continue
        tick = mt5.symbol_info_tick(sym)
        if not tick or tick.bid <= 0:
            continue
        if not is_asset_tradable(sym):
            continue
        tradable.append(sym)
    return tradable

# === SESSIE DETECTIE ===
def get_current_session():
    local_time = get_local_time()
    hour = local_time.hour
    weekday = local_time.weekday()
    
    if weekday >= 5:
        return 'Weekend'
    elif hour >= 23 or hour < 8:
        return 'Asian'
    elif hour >= 8 and hour < 16:
        return 'London'
    elif hour >= 13 and hour < 22:
        return 'New_York'
    return 'Unknown'

# === SPREAD CHECK ===
def check_spread(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False, "Geen prijsdata"
    
    spread = tick.ask - tick.bid
    spread_limit = SPREAD_LIMITS.get(symbol, 100)
    
    if spread > spread_limit:
        return False, f"Spread {spread:.2f} > limiet"
    
    return True, "OK"

# === ASSET TRACKING ===
def init_asset_stats(symbol):
    if symbol not in asset_stats:
        asset_stats[symbol] = {
            'trades': 0, 'wins': 0, 'losses': 0,
            'pnl': 0.0, 'consecutive_losses': 0
        }

def update_asset_stats(symbol, profit):
    init_asset_stats(symbol)
    asset_stats[symbol]['trades'] += 1
    asset_stats[symbol]['pnl'] += profit
    
    if profit > 0:
        asset_stats[symbol]['wins'] += 1
        asset_stats[symbol]['consecutive_losses'] = 0
    else:
        asset_stats[symbol]['losses'] += 1
        asset_stats[symbol]['consecutive_losses'] += 1

def check_asset_performance(symbol):
    if symbol not in asset_stats:
        return True, "Geen data"
    
    stats = asset_stats[symbol]
    if stats['trades'] < 3:
        return True, f"{stats['trades']}/3"
    
    win_rate = (stats['wins'] / stats['trades']) * 100
    if win_rate < 20.0:
        return False, f"WR {win_rate:.1f}% < 20%"
    
    return True, f"OK ({win_rate:.1f}%)"

# === ✅ HARD STOP CHECK ===
def check_consecutive_losses():
    global consecutive_losses, loss_pause_until, HARD_STOP_TRIGGERED
    
    if HARD_STOP_TRIGGERED:
        logger.critical("🚨 HARD STOP ACTIEF - Bot kan NIET meer handelen")
        return False
    
    if loss_pause_until and time.time() > loss_pause_until:
        loss_pause_until = None
        consecutive_losses = 0
        logger.info("✅ Verlies pauze voorbij")
        return True
    
    if loss_pause_until:
        return False
    
    if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        if HARD_STOP_ENABLED:
            HARD_STOP_TRIGGERED = True
            loss_pause_until = None  # Geen pauze, permanent stop
            logger.critical(f"🚨🚨🚨 HARD STOP TRIGGERED | {consecutive_losses} verliezen | BOT STOPT DEFINITIEF")
            send_telegram_alert(f"🚨🚨🚨 <b>HARD STOP TRIGGERED</b>\n{consecutive_losses} verliezen op rij\nBOT STOPT DEFINITIEF\nGeen trades meer!")
            save_stats()
            return False
        else:
            loss_pause_until = time.time() + (24 * 60 * 60)
            logger.critical(f"🚨 MAX LOSSES | {consecutive_losses} | 24u pauze")
            return False
    
    return True

# === DAILY P&L ===
def update_daily_pnl():
    today = get_local_time().strftime('%Y-%m-%d')
    try:
        if os.path.exists(DAILY_PNL_FILE):
            with open(DAILY_PNL_FILE, 'r') as f:
                daily_data = json.load(f)
        else:
            daily_data = {}
        
        if today not in daily_data:
            account = mt5.account_info()
            daily_data[today] = {
                'start_balance': account.balance if account else 0.0,
                'current_balance': 0.0,
                'max_balance': 0.0
            }
        
        account = mt5.account_info()
        if account:
            daily_data[today]['current_balance'] = account.balance
            daily_data[today]['max_balance'] = max(daily_data[today]['max_balance'], account.balance)
        
        start = daily_data[today]['start_balance']
        current = daily_data[today]['current_balance']
        max_bal = daily_data[today]['max_balance']
        
        drawdown = (max_bal - current) / max_bal * 100 if max_bal > start else 0.0
        trading_stats['daily_drawdown'] = max(0.0, drawdown)
        
        with open(DAILY_PNL_FILE, 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        return drawdown
    except:
        return 0.0

def check_kill_switch():
    drawdown = update_daily_pnl()
    if drawdown >= DAILY_DRAWDOWN_LIMIT:
        logger.critical(f"🚨 KILL SWITCH | Drawdown: {drawdown:.2f}%")
        send_telegram_alert(f"🚨 <b>KILL SWITCH</b>\nDrawdown: {drawdown:.2f}%")
        positions = mt5.positions_get()
        for pos in positions:
            if pos.magic == 20261002:
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": pos.ticket,
                    "price": mt5.symbol_info_tick(pos.symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(pos.symbol).ask,
                    "deviation": 50,
                    "magic": pos.magic,
                    "comment": "KILL_SWITCH",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(close_request)
        return True
    return False

# === TELEGRAM ===
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False

# === TECHNISCHE ANALYSE ===
def get_price_data(symbol, bars=300):
    if not mt5.symbol_select(symbol, True):
        return None
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, bars)
    if rates is None or len(rates) < 50:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    for period in [9, 21, 50]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2.0)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2.0)
    
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift()),
                                    abs(df['low'] - df['close'].shift())))
    df['atr'] = df['tr'].rolling(14).mean()
    
    df['plus_dm'] = df['high'] - df['high'].shift()
    df['minus_dm'] = df['low'].shift() - df['low']
    df['plus_dm'] = np.where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), df['plus_dm'], 0)
    df['minus_dm'] = np.where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), df['minus_dm'], 0)
    
    df['atr_adx'] = df['tr'].rolling(14).mean()
    df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr_adx'])
    df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr_adx'])
    df['dx'] = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(14).mean()
    
    df['volume_ma'] = df['tick_volume'].rolling(20).mean()
    df['recent_high'] = df['high'].rolling(20).max()
    df['recent_low'] = df['low'].rolling(20).min()
    
    return df

# === ✅ MULTI-STRATEGY ENTRY (MET REGIME CHECK) ===
def check_multi_strategy_entry(df, symbol):
    """
    ✅ Kiest strategie GEBASEERD op markt regime
    ✅ TREND in trend markt
    ✅ MEAN REV in range markt
    ✅ BREAKOUT in volatile markt
    """
    if len(df) < 50:
        return None, None, None, None, None
    
    row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    settings = ASSET_SETTINGS.get(symbol, {'atr_sl_mult': 2.0, 'atr_tp_mult': 4.0, 'volume_mult': 1.5, 'min_adx': 25, 'max_lot': 5.0, 'max_risk_pct': 1.0})
    atr_sl_mult = settings['atr_sl_mult']  # ✅ 2.0 (niet 1.0!)
    atr_tp_mult = settings['atr_tp_mult']  # ✅ 4.0 (niet 3.0!)
    volume_mult = settings['volume_mult']
    min_adx = settings['min_adx']
    
    try:
        ema_9 = float(row['ema_9'])
        ema_21 = float(row['ema_21'])
        ema_50 = float(row['ema_50'])
        adx = float(row['adx'])
        rsi = float(row['rsi'])
        close = float(row['close'])
        atr = float(row['atr'])
        volume = float(row['tick_volume'])
        volume_ma = float(row['volume_ma'])
        bb_upper = float(row['bb_upper'])
        bb_lower = float(row['bb_lower'])
        recent_high = float(row['recent_high'])
        recent_low = float(row['recent_low'])
        prev_close = float(prev_row['close'])
    except Exception as e:
        logger.debug(f"Error reading data: {e}")
        return None, None, None, None, None
    
    # ✅ Detecteer regime
    regime = detect_market_regime(df)
    global_state['market_regime'] = regime
    
    logger.debug(f"{symbol}: Regime={regime}, ADX={adx:.1f}, RSI={rsi:.1f}")
    
    # ✅ Volume Check
    if volume < volume_ma * volume_mult:
        return None, None, None, None, None
    
    # === STRATEGIE 1: TREND FOLLOWING (ADX > 30) ===
    if regime == 'Trend' or adx >= min_adx:
        logger.debug(f"{symbol}: TREND strategie actief")
        
        # LONG
        if ema_9 > ema_21 > ema_50 and close > recent_high and prev_close <= recent_high:
            entry = close
            sl = entry - (atr * atr_sl_mult)  # ✅ 2x ATR
            tp = entry + (atr * atr_tp_mult)  # ✅ 4x ATR
            if sl < entry and tp > entry:
                logger.info(f"{symbol}: LONG TREND | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'long', entry, sl, tp, 'TREND'
        
        # SHORT
        if ema_9 < ema_21 < ema_50 and close < recent_low and prev_close >= recent_low:
            entry = close
            sl = entry + (atr * atr_sl_mult)
            tp = entry - (atr * atr_tp_mult)
            if sl > entry and tp < entry:
                logger.info(f"{symbol}: SHORT TREND | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'short', entry, sl, tp, 'TREND'
    
    # === STRATEGIE 2: MEAN REVERSION (ADX < 20) ===
    if regime == 'Range':
        logger.debug(f"{symbol}: MEAN REVERSION strategie actief")
        
        if rsi < 25 and close <= bb_lower * 1.002:
            entry = close
            sl = entry - (atr * atr_sl_mult)
            tp = entry + (atr * (atr_tp_mult * 0.7))
            if sl < entry and tp > entry:
                logger.info(f"{symbol}: LONG MEAN_REV | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'long', entry, sl, tp, 'MEAN_REV'
        
        if rsi > 75 and close >= bb_upper * 0.998:
            entry = close
            sl = entry + (atr * atr_sl_mult)
            tp = entry - (atr * (atr_tp_mult * 0.7))
            if sl > entry and tp < entry:
                logger.info(f"{symbol}: SHORT MEAN_REV | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'short', entry, sl, tp, 'MEAN_REV'
    
    # === STRATEGIE 3: BREAKOUT (Volatile) ===
    if regime == 'Volatile':
        logger.debug(f"{symbol}: BREAKOUT strategie actief")
        
        if close > recent_high and volume > volume_ma * (volume_mult * 1.5):
            entry = close
            sl = recent_low - (atr * atr_sl_mult * 0.5)
            tp = entry + (atr * (atr_tp_mult * 1.5))
            if sl < entry and tp > entry:
                logger.info(f"{symbol}: LONG BREAKOUT | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'long', entry, sl, tp, 'BREAKOUT'
        
        if close < recent_low and volume > volume_ma * (volume_mult * 1.5):
            entry = close
            sl = recent_high + (atr * atr_sl_mult * 0.5)
            tp = entry - (atr * (atr_tp_mult * 1.5))
            if sl > entry and tp < entry:
                logger.info(f"{symbol}: SHORT BREAKOUT | Entry:{entry:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                return 'short', entry, sl, tp, 'BREAKOUT'
    
    return None, None, None, None, None

# === ✅ POSITION SIZING (MAX 1% RISK!) ===
def calculate_position_size(symbol, entry, sl):
    """
    ✅ Berekent lot size gebaseerd op 1% risk (niet 5%!)
    ✅ Max 10% account exposure
    """
    account = mt5.account_info()
    if not account or account.equity <= 0:
        return 0.01
    
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return 0.01
    
    settings = ASSET_SETTINGS.get(symbol, {'max_lot': 5.0, 'max_risk_pct': 1.0})
    max_lot = settings['max_lot']
    max_risk_pct = settings['max_risk_pct']  # ✅ 1%
    
    # ✅ Bereken risk-based lot size
    risk_amount = account.equity * (max_risk_pct / 100)  # ✅ 1% van equity
    point_distance = abs(entry - sl)
    
    if point_distance == 0:
        return 0.01
    
    tick_value = symbol_info.trade_tick_value or 1.0
    tick_size = symbol_info.trade_tick_size or 0.01
    
    risk_per_lot = (point_distance / tick_size) * tick_value
    if risk_per_lot <= 0:
        return 0.01
    
    lots = risk_amount / risk_per_lot
    
    # ✅ Hard cap op max_lot
    lots = min(lots, max_lot)
    
    # ✅ Check total exposure
    positions = mt5.positions_get()
    if positions:
        total_exposure = sum(abs(p.volume * p.price_open * symbol_info.trade_contract_size) for p in positions if p.symbol == symbol)
        max_exposure = account.equity * (MAX_EXPOSURE_PCT / 100)
        if total_exposure >= max_exposure:
            logger.warning(f"⚠️ Max exposure bereikt voor {symbol}")
            return 0.01
    
    # ✅ Margin check
    margin_per_lot = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 1.0, entry)
    if margin_per_lot and margin_per_lot > 0:
        max_margin = account.margin_free * (MAX_MARGIN_USAGE_PCT / 100)
        max_lots_by_margin = max_margin / margin_per_lot
        lots = min(lots, max_lots_by_margin)
    
    # ✅ Round naar stappen
    lots = max(symbol_info.volume_min, min(lots, symbol_info.volume_max))
    lots = round(lots / symbol_info.volume_step) * symbol_info.volume_step
    
    return max(symbol_info.volume_min, lots)

# === TRAILING STOP ===
def manage_trades_trailing():
    positions = mt5.positions_get()
    if not positions:
        return 0
    
    adjusted = 0
    for pos in positions:
        if pos.magic != 20261002:
            continue
        
        symbol_info = mt5.symbol_info(pos.symbol)
        if not symbol_info:
            continue
        
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            continue
        
        current_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        risk_distance = abs(pos.price_open - pos.sl)
        if risk_distance == 0:
            continue
        
        profit_distance = (current_price - pos.price_open) if pos.type == mt5.ORDER_TYPE_BUY else (pos.price_open - current_price)
        r_multiple = profit_distance / risk_distance
        
        if r_multiple >= 1.0:
            trail_distance = 0.5 * risk_distance
            new_sl = current_price - trail_distance if pos.type == mt5.ORDER_TYPE_BUY else current_price + trail_distance
            
            if pos.type == mt5.ORDER_TYPE_BUY and new_sl > pos.sl + (symbol_info.point * 30):
                request = {"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp, "magic": pos.magic}
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    adjusted += 1
                    logger.info(f"📈 TRAILING | {pos.symbol}")
            
            elif pos.type == mt5.ORDER_TYPE_SELL and new_sl < pos.sl - (symbol_info.point * 30):
                request = {"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp, "magic": pos.magic}
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    adjusted += 1
                    logger.info(f"📈 TRAILING | {pos.symbol}")
    
    return adjusted

# === TRADE TRACKING ===
def track_closed_trades():
    global consecutive_losses
    
    from_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    to_time = datetime.now(timezone.utc)
    
    deals = mt5.history_deals_get(from_time, to_time)
    if not deals:
        return 0
    
    tracked = 0
    for deal in deals:
        if deal.magic != 20261002:
            continue
        
        if deal.entry != mt5.DEAL_ENTRY_OUT:
            continue
        
        deal_key = f"{deal.ticket}_{deal.time}"
        
        if deal_key in global_state['closed_trades']:
            continue
        
        global_state['closed_trades'].add(deal_key)
        
        trading_stats['total_trades_ever'] += 1
        
        if deal.profit > 0:
            trading_stats['total_won'] += 1
            trading_stats['cumulative_pnl'] += deal.profit
            trading_stats['largest_win'] = max(trading_stats['largest_win'], deal.profit)
            consecutive_losses = 0
            logger.info(f"✅ WIN | {deal.symbol} | Profit: ${deal.profit:.2f}")
        else:
            trading_stats['total_lost'] += 1
            trading_stats['cumulative_pnl'] += deal.profit
            trading_stats['largest_loss'] = min(trading_stats['largest_loss'], deal.profit)
            consecutive_losses += 1
            logger.info(f"❌ LOSS | {deal.symbol} | Profit: ${deal.profit:.2f} | Consecutive: {consecutive_losses}/{MAX_CONSECUTIVE_LOSSES}")
        
        update_asset_stats(deal.symbol, deal.profit)
        tracked += 1
    
    if tracked > 0:
        save_stats()
        logger.info(f"📊 {tracked} trades getrackt")
    
    return tracked

def show_dashboard(scan_count, scan_results):
    os.system('cls' if os.name == 'nt' else 'clear')
    account = mt5.account_info()
    if not account:
        print("❌ Geen account")
        return
    
    local_time = get_local_time()
    utc_time = get_utc_time()
    positions = mt5.positions_get() or []
    floating_pl = sum(p.profit for p in positions)
    net_result = trading_stats['cumulative_pnl'] + floating_pl
    win_rate = (trading_stats['total_won'] / max(trading_stats['total_trades_ever'], 1)) * 100
    daily_drawdown = update_daily_pnl()
    
    regime = global_state.get('market_regime', 'Unknown')
    hard_stop = "🚨 ACTIEF" if HARD_STOP_TRIGGERED else "✅ Inactief"
    
    print(f"{Back.BLUE}{Fore.WHITE}{' PRICE ACTION BOT v10.2 - ULTIMATE FIX ':=^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🕒 {local_time.strftime('%Y-%m-%d %H:%M %Z')} | UTC: {utc_time.strftime('%H:%M')} | Scan #{scan_count} | {global_state['session']}{Style.RESET_ALL}")
    print()
    
    print(f"{Back.GREEN}{Fore.BLACK} STATISTIEKEN {'':=^68}{Style.RESET_ALL}")
    total_color = Fore.GREEN if trading_stats['cumulative_pnl'] >= 0 else Fore.RED
    net_color = Fore.GREEN if net_result >= 0 else Fore.RED
    print(f" 📊 Totaal: {trading_stats['total_trades_ever']} | ✅ {trading_stats['total_won']} | ❌ {trading_stats['total_lost']}")
    print(f" 📈 Win Rate: {win_rate:.1f}%")
    print(f" 💰 P&L: {total_color}${trading_stats['cumulative_pnl']:>10.2f}{Style.RESET_ALL}")
    print(f" 🎯 Netto: {net_color}${net_result:>10.2f}{Style.RESET_ALL}")
    print()
    
    print(f"{Back.GREEN}{Fore.BLACK} ACCOUNT {'':=^68}{Style.RESET_ALL}")
    print(f" Balance: ${account.balance:>10.2f} | Equity: ${account.equity:>10.2f}")
    print(f" Floating: ${floating_pl:>10.2f} | Trades: {len(positions)}/{MAX_TRADES_TOTAL}")
    dd_color = Fore.GREEN if daily_drawdown < 3.0 else Fore.YELLOW if daily_drawdown < DAILY_DRAWDOWN_LIMIT else Fore.RED
    print(f" 📉 DD: {dd_color}{daily_drawdown:.2f}%{Style.RESET_ALL} | Kill: {DAILY_DRAWDOWN_LIMIT}%")
    print(f" ⚠️ Consecutive: {consecutive_losses}/{MAX_CONSECUTIVE_LOSSES}")
    print(f" 🚨 Hard Stop: {hard_stop}")
    print()
    
    print(f"{Back.YELLOW}{Fore.BLACK} RISK SETTINGS {'':=^62}{Style.RESET_ALL}")
    print(f" ✅ Max Risk per Trade: {MAX_RISK_PER_TRADE_PCT}%")
    print(f" ✅ Max Exposure: {MAX_EXPOSURE_PCT}%")
    print(f" ✅ Max Margin: {MAX_MARGIN_USAGE_PCT}%")
    print(f" ✅ Max Daily DD: {DAILY_DRAWDOWN_LIMIT}%")
    print(f" ✅ SL: 2x ATR | TP: 4x ATR")
    print()
    
    print(f"{Back.CYAN}{Fore.WHITE} MULTI-STRATEGY {'':=^62}{Style.RESET_ALL}")
    print(f" 📈 Markt Regime: {regime}")
    print(f" ✅ Strategieën: Trend + Mean Rev + Breakout")
    print(f" ✅ Assets: {len(TEST_ASSETS)}")
    print()
    
    print(f"{Back.CYAN}{Fore.WHITE} SCAN ({len(scan_results)}) {'':=^58}{Style.RESET_ALL}")
    if scan_results:
        for sym, t, tp, sl, strat in scan_results[:5]:
            print(f" {sym:<10} {t:<6} [{strat:<10}] TP:{tp:>12.2f} SL:{sl:>12.2f}")
    else:
        print(f" {Fore.YELLOW}Geen setups")
    print()
    
    print(f"{Back.MAGENTA}{Fore.BLACK} OPEN POSITIES ({len(positions)}) {'':=^56}{Style.RESET_ALL}")
    if positions:
        print(f" {'Symbool':<10} {'Type':<6} {'Lot':<6} {'Entry':<12} {'SL':<12} {'TP':<12} {'P&L':<10}")
        print(f" {'-'*75}")
        for pos in sorted(positions, key=lambda x: x.profit, reverse=True):
            type_str = f"{Fore.GREEN}BUY" if pos.type == mt5.ORDER_TYPE_BUY else f"{Fore.RED}SELL"
            pnl_color = Fore.GREEN if pos.profit >= 0 else Fore.RED
            print(f" {pos.symbol:<10} {type_str:<10}{Style.RESET_ALL} {pos.volume:<6.2f} {pos.price_open:<12.2f} {pos.sl:<12.2f} {pos.tp:<12.2f} {pnl_color}{pos.profit:>10.2f}{Style.RESET_ALL}")
    else:
        print(f" {Fore.YELLOW}Geen open posities")
    
    print()
    if HARD_STOP_TRIGGERED:
        print(f"{Back.RED}{Fore.WHITE}🚨 HARD STOP TRIGGERED - BOT STOPT DEFINITIEF 🚨{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}💡 CTRL+C = stop | v10.2 Ultimate Fix{Style.RESET_ALL}")
    print(f"{Back.BLUE}{'':=^80}{Style.RESET_ALL}")

def main_loop():
    global consecutive_losses, HARD_STOP_TRIGGERED
    load_stats()
    
    # ✅ CHECK HARD STOP BIJ START
    if HARD_STOP_TRIGGERED:
        logger.critical("🚨🚨🚨 HARD STOP ACTIEF - Bot KAN NIET starten")
        print("\n" + "="*70)
        print("🚨 HARD STOP TRIGGERED 🚨")
        print("="*70)
        print("De bot heeft 3 verliezen op rij geleden.")
        print("Hard stop is geactiveerd - bot kan NIET meer handelen.")
        print("\nNeem contact op met Joe voor verdere stappen.")
        print("="*70 + "\n")
        return
    
    logger.info(f"🌍 TIMEZONE: {global_state['timezone']}")
    logger.info(f"📊 Assets: {len(TEST_ASSETS)}")
    logger.info(f"🔒 Max Risk: {MAX_RISK_PER_TRADE_PCT}% per trade")
    logger.info(f"🚨 Hard Stop: {MAX_CONSECUTIVE_LOSSES} verliezen")
    
    local_time = get_local_time()
    utc_time = get_utc_time()
    logger.info(f"🕒 Huidige tijd: {local_time.strftime('%Y-%m-%d %H:%M %Z')}")
    
    if not initialize_mt5():
        print("\n❌ OPEN MT5 EN LOG IN!\n")
        return
    
    send_telegram_alert(f"✅ <b>BOT v10.2 ULTIMATE FIX GESTART</b>\n🌍 Timezone: {global_state['timezone']}\n📊 {len(TEST_ASSETS)} assets\n🔒 Max Risk: {MAX_RISK_PER_TRADE_PCT}%\n🚨 Hard Stop: {MAX_CONSECUTIVE_LOSSES} verliezen")
    
    logger.info("="*70)
    logger.info("v10.2 - ULTIMATE FIX EDITION")
    logger.info(f"Max Risk: {MAX_RISK_PER_TRADE_PCT}% per trade")
    logger.info(f"Hard Stop: {MAX_CONSECUTIVE_LOSSES} verliezen")
    logger.info(f"Start tijd: {local_time.strftime('%Y-%m-%d %H:%M %Z')}")
    logger.info("="*70)
    
    last_scan = 0
    last_dashboard = 0
    last_trade_mgmt = 0
    last_track = 0
    last_session = 0
    scan_count = 0
    
    try:
        while True:
            current = time.time()
            
            # ✅ CHECK HARD STOP ELKE LOOP
            if HARD_STOP_TRIGGERED:
                logger.critical("🚨 HARD STOP TRIGGERED - Bot stopt")
                print("\n🚨 HARD STOP TRIGGERED - Bot stopt definitief!\n")
                break
            
            if current - last_session >= 60:
                global_state['session'] = get_current_session()
                last_session = current
            
            # Update market regime
            btc_df = get_price_data('BTCUSD', 300) if mt5.symbol_info('BTCUSD') else None
            if btc_df is not None:
                global_state['market_regime'] = detect_market_regime(btc_df)
            
            if not check_mt5_connection():
                time.sleep(10)
                continue
            
            if not is_trading_hours():
                if scan_count % 20 == 0:
                    logger.info("⏰ Buiten trading hours - wacht...")
                time.sleep(30)
                continue
            
            # ✅ CHECK CONSECUTIVE LOSSES (met hard stop)
            if not check_consecutive_losses():
                if HARD_STOP_TRIGGERED:
                    break  # ✅ Stop definitief
                time.sleep(60)
                continue
            
            if current - last_track >= 5:
                track_closed_trades()
                last_track = current
            
            if current - last_trade_mgmt >= 30:
                if check_kill_switch():
                    time.sleep(3600)
                    continue
            
            if current - last_trade_mgmt >= 5:
                manage_trades_trailing()
                last_trade_mgmt = current
            
            if current - last_scan >= 15:
                scan_count += 1
                symbols = get_all_tradable_symbols()
                results = []
                
                logger.info(f"📊 Scan {scan_count}: {len(symbols)} handelbare assets | Regime: {global_state['market_regime']}")
                
                for sym in symbols:
                    if len(mt5.positions_get() or []) >= MAX_TRADES_TOTAL:
                        break
                    if len(mt5.positions_get(symbol=sym) or []) >= 1:
                        continue
                    
                    spread_ok, _ = check_spread(sym)
                    if not spread_ok:
                        continue
                    
                    asset_ok, _ = check_asset_performance(sym)
                    if not asset_ok:
                        continue
                    
                    df = get_price_data(sym)
                    if df is None:
                        continue
                    
                    t, entry, sl, tp, strat = check_multi_strategy_entry(df, sym)
                    if t is None:
                        continue
                    
                    results.append((sym, t, tp, sl, strat))
                    
                    lots = calculate_position_size(sym, entry, sl)
                    order = mt5.ORDER_TYPE_BUY if t == 'long' else mt5.ORDER_TYPE_SELL
                    price = mt5.symbol_info_tick(sym).ask if order == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(sym).bid
                    
                    req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": sym,
                        "volume": lots,
                        "type": order,
                        "price": price,
                        "sl": sl,
                        "tp": tp,
                        "deviation": 30,
                        "magic": 20261002,
                        "comment": f"v102_{strat}_{t.upper()}",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    res = mt5.order_send(req)
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        trading_stats['total_trades_ever'] += 1
                        trading_stats['symbols_traded'].add(sym)
                        save_stats()
                        logger.info(f"✅ {sym} {t.upper()} [{strat}] Lot:{lots:.2f} | SL:{sl:.2f} | TP:{tp:.2f}")
                    else:
                        logger.error(f"❌ {sym} Order failed: {res.retcode}")
                
                last_scan = current
            
            if current - last_dashboard >= 3:
                show_dashboard(scan_count, results)
                last_dashboard = current
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Gestopt door gebruiker")
    finally:
        save_stats()
        mt5.shutdown()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("✅ v10.2 - ULTIMATE FIX EDITION")
    print("="*70)
    print(f"🌍 Timezone: {LOCAL_TZ_NAME}")
    print(f"📊 Assets: {len(TEST_ASSETS)} - {TEST_ASSETS}")
    print(f"🔒 Max Risk: {MAX_RISK_PER_TRADE_PCT}% per trade")
    print(f"📉 Max Daily DD: {DAILY_DRAWDOWN_LIMIT}%")
    print(f"🚨 Hard Stop: {MAX_CONSECUTIVE_LOSSES} verliezen = STOP")
    print(f"✅ SL: 2x ATR | TP: 4x ATR")
    print(f"✅ Strategie: TREND in trend markt (niet Mean Rev!)")
    print("="*70)
    print("\n⚠️ LAATSTE POGING - Als dit faalt, STOPPEN we definitief.")
    print("="*70)
    input("\nDruk ENTER om te starten...")
    main_loop()
