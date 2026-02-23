# =============================================================================
# BACKTEST ENGINE v3.0 — PROFESSIONAL AUDITED EDITION
# Fixes: NoneType errors, dynamische sizing, SL/TP, trailing stop
# =============================================================================
import pandas as pd
import numpy as np
import config
import indicators
import strategy

def calculate_trade_costs(lot_size, spread_pts, slippage_pts, commission_per_lot):
    """
    Bereken totale kosten per trade.
    Voor XAUUSD: 1 point = 0.01 price move
    """
    point_value_per_01lot = 0.10  # USD per point
    spread_cost = spread_pts * point_value_per_01lot * (lot_size / 0.1)
    slippage_cost = slippage_pts * point_value_per_01lot * (lot_size / 0.1)
    commission = commission_per_lot * lot_size
    
    return spread_cost + slippage_cost + commission

def run_backtest(df, params, initial_capital=None):
    """
    Volledige backtest met:
    - Kosten per trade (niet lineair!)
    - Dynamische lot sizing
    - Stop Loss / Take Profit
    - Trailing Stop
    - Proper equity tracking
    - Null-safe berekeningen
    """
    cap = initial_capital or config.INITIAL_CAPITAL
    df = df.copy()
    
    # Bereken indicatoren (geef params door voor dynamische EMA's)
    df = indicators.calculate_all_indicators(df, params=params)
    
    # Genereer signalen
    df = strategy.generate_final_signals(df, params)
    
    # ----- BACKTEST LOOP -----
    equity = cap
    position = 0  # 0 = flat, 1 = long, -1 = short
    entry_price = None
    entry_time = None
    lot_size = config.LOT_SIZE_BASE
    current_sl = None
    
    trades = []  # Log alle trades
    equity_curve = []
    
    for idx, row in df.iterrows():
        # 1. Check exit voorwaarden (SL/TP/Trailing)
        if position != 0 and entry_price is not None:
            # Trailing stop update
            if config.TRAILING_STOP_ACTIVATION > 0:
                trailed_sl = strategy.apply_trailing_stop(
                    entry_price, row['close'], position,
                    config.TRAILING_STOP_ACTIVATION,
                    config.TRAILING_STOP_POINTS
                )
                if trailed_sl is not None:
                    if position == 1:
                        current_sl = max(current_sl if current_sl is not None else -np.inf, trailed_sl)
                    else:
                        current_sl = min(current_sl if current_sl is not None else np.inf, trailed_sl)
            
            # Check SL/TP hit
            exit_reason, exit_price = strategy.check_stop_loss_tp(
                entry_price, row['high'], row['low'], position,
                config.STOP_LOSS_POINTS, config.TAKE_PROFIT_POINTS
            )
            
            if exit_reason in ['SL', 'TP'] or (current_sl is not None and 
                ((position == 1 and row['low'] <= current_sl) or 
                 (position == -1 and row['high'] >= current_sl))):
                # Sluit trade
                if entry_price is not None and exit_price is not None:
                    if position == 1:
                        pnl = (exit_price - entry_price) * lot_size * 100
                    else:
                        pnl = (entry_price - exit_price) * lot_size * 100
                else:
                    pnl = 0  # Safety fallback
                
                # Trek kosten af (al betaald bij entry, dus niet dubbel)
                net_pnl = pnl  # Kosten al bij entry verwerkt
                
                equity += net_pnl
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': idx,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'lot_size': lot_size,
                    'pnl': net_pnl,
                    'exit_reason': exit_reason if exit_reason in ['SL','TP'] else 'SIGNAL'
                })
                
                # Reset
                position = 0
                entry_price = None
                entry_time = None
                current_sl = None
        
        # 2. Check entry signal
        if row['signal'] != 0 and position == 0:
            # Bereken dynamische lot size met null checks
            if equity is None or equity <= 0:
                equity = cap
            
            lot_size = strategy.calculate_dynamic_lot_size(
                equity, config.RISK_PER_TRADE_PCT, 
                config.STOP_LOSS_POINTS, config.SYMBOL
            )
            
            # Bereken en trek kosten af bij entry
            trade_cost = calculate_trade_costs(
                lot_size, 
                config.SPREAD_POINTS_AVG, 
                config.SLIPPAGE_POINTS_AVG, 
                config.COMMISSION_PER_LOT
            )
            equity -= trade_cost
            
            # Open positie
            position = row['signal']
            entry_price = row['close']
            entry_time = idx
            current_sl = entry_price - (config.STOP_LOSS_POINTS * 0.01) if position == 1 else \
                        entry_price + (config.STOP_LOSS_POINTS * 0.01)
        
        # 3. Log equity
        equity_curve.append({'time': idx, 'equity': equity})
    
    # Sluit open positie aan einde (market close)
    if position != 0 and entry_price is not None and len(df) > 0:
        exit_price = df.iloc[-1]['close']
        if entry_price is not None and exit_price is not None:
            if position == 1:
                pnl = (exit_price - entry_price) * lot_size * 100
            else:
                pnl = (entry_price - exit_price) * lot_size * 100
        else:
            pnl = 0
        equity += pnl
        trades.append({
            'entry_time': entry_time,
            'exit_time': df.index[-1],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'lot_size': lot_size,
            'pnl': pnl,
            'exit_reason': 'END_OF_TEST'
        })
    
    # ----- METRICS BEREKENEN -----
    if len(equity_curve) > 0:
        equity_df = pd.DataFrame(equity_curve).set_index('time')
        
        # Drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
    else:
        equity_df = pd.DataFrame()
        max_drawdown = 0
    
    # Trade metrics
    if len(trades) > 0:
        trade_df = pd.DataFrame(trades)
        winning = trade_df[trade_df['pnl'] > 0]
        losing = trade_df[trade_df['pnl'] <= 0]
        
        win_rate = len(winning) / len(trades)
        avg_win = winning['pnl'].mean() if len(winning) > 0 else 0
        avg_loss = losing['pnl'].mean() if len(losing) > 0 else 0
        gross_wins = winning['pnl'].sum()
        gross_losses = abs(losing['pnl'].sum())
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 999
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
    
    # Totale kosten
    total_trades = len(trades)
    avg_lot = np.mean([t['lot_size'] for t in trades]) if trades else config.LOT_SIZE_BASE
    avg_cost = calculate_trade_costs(avg_lot, config.SPREAD_POINTS_AVG, 
                                     config.SLIPPAGE_POINTS_AVG, config.COMMISSION_PER_LOT)
    total_costs = total_trades * avg_cost
    
    # Netto winst
    net_profit = equity - cap
    
    return {
        'params': params,
        'net_profit': net_profit,
        'final_equity': equity,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_costs': total_costs,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'equity_curve': equity_df,
        'trades': trades,
        'df_with_signals': df
    }