# =============================================================================
# WALK-FORWARD VALIDATION MODULE
# Simuleert real-world performance door rolling train/test periodes
# =============================================================================
import pandas as pd
import numpy as np
from datetime import timedelta
import config
import backtest_engine
import itertools

def walk_forward_validation(df, param_grid, train_months=None, test_months=None):
    """
    Voert walk-forward validation uit:
    1. Split data in rolling train/test windows
    2. Optimaliseer params op train set
    3. Test op out-of-sample test set
    4. Aggregeer resultaten
    
    Returns: DataFrame met per-period metrics + overall stats
    """
    train_m = train_months or config.WF_TRAIN_MONTHS
    test_m = test_months or config.WF_TEST_MONTHS
    
    results = []
    dates = df.index
    
    if len(dates) < 100:
        print("❌ Te weinig data voor walk-forward")
        return None
    
    start_ptr = 0
    iteration = 0
    
    print(f"🔄 Start walk-forward: {train_m}m train / {test_m}m test")
    
    while True:
        # Bepaal train periode
        train_start = dates[start_ptr]
        train_end_candidates = dates[dates >= train_start + pd.DateOffset(months=train_m)]
        if len(train_end_candidates) == 0:
            break
        train_end = train_end_candidates[0]
        
        # Bepaal test periode
        test_start = train_end
        test_end_candidates = dates[dates >= test_start + pd.DateOffset(months=test_m)]
        if len(test_end_candidates) == 0:
            # Gebruik rest van data als test
            test_end = dates[-1]
        else:
            test_end = test_end_candidates[0]
        
        train_data = df[(df.index >= train_start) & (df.index < train_end)]
        test_data = df[(df.index >= test_start) & (df.index < test_end)]
        
        # Check minimum data
        if len(train_data) < config.WF_MIN_TRAIN_CANDLES or len(test_data) < config.WF_MIN_TEST_CANDLES:
            start_ptr += 50  # Shift en probeer opnieuw
            continue
        
        # Optimaliseer op train set (beperkte search voor snelheid)
        print(f"   [{iteration+1}] Train: {train_start.date()} → {train_end.date()}")
        best_params = _find_best_params_quick(train_data, param_grid)
        
        # Test op out-of-sample
        test_result = backtest_engine.run_backtest(test_data, best_params)
        test_result['period'] = f"{test_start.date()} → {test_end.date()}"
        test_result['train_period'] = f"{train_start.date()} → {train_end.date()}"
        test_result['in_sample_pf'] = _calc_pf_on_data(train_data, best_params)
        results.append(test_result)
        
        print(f"        Test PF: {test_result['profit_factor']:.2f} | "
              f"Net: ${test_result['net_profit']:.0f} | "
              f"DD: {test_result['max_drawdown']:.1%}")
        
        # Move forward
        start_ptr = dates.get_loc(test_end) if test_end in dates else start_ptr + 100
        iteration += 1
        
        if test_end >= dates[-1]:
            break
    
    if not results:
        print("⚠️  Geen geldige walk-forward periodes gevonden")
        return None
    
    # Aggregeer resultaten
    summary = _aggregate_wf_results(results)
    return pd.DataFrame(results), summary

def _find_best_params_quick(df, param_grid):
    """Snelle parameter search voor walk-forward (beperkte combinaties)."""
    best_pf = -1
    best_params = None
    
    # Sample max 12 combinaties voor snelheid
    combos = list(itertools.product(*param_grid.values()))[:12]
    
    for combo in combos:
        params = dict(zip(param_grid.keys(), combo))
        result = backtest_engine.run_backtest(df, params)
        if result['profit_factor'] > best_pf and result['total_trades'] >= 10:
            best_pf = result['profit_factor']
            best_params = params
    
    return best_params or {
        'ema_fast': config.EMA_FAST_DEFAULT,
        'ema_slow': config.EMA_SLOW_DEFAULT,
        'use_trend_filter': config.USE_TREND_FILTER,
        'use_fvg_filter': config.USE_FVG_FILTER
    }

def _calc_pf_on_data(df, params):
    """Helper: bereken profit factor op gegeven data."""
    result = backtest_engine.run_backtest(df, params)
    return result['profit_factor']

def _aggregate_wf_results(results):
    """Aggregeer walk-forward resultaten naar overall metrics."""
    if not results:
        return {}
    
    total_net = sum(r['net_profit'] for r in results)
    total_trades = sum(r['total_trades'] for r in results)
    avg_pf = np.mean([r['profit_factor'] for r in results if r['profit_factor'] > 0])
    worst_dd = min(r['max_drawdown'] for r in results)
    
    # Consistency metric: std van monthly returns
    monthly_nets = [r['net_profit'] for r in results]
    consistency = 1 - (np.std(monthly_nets) / (np.abs(np.mean(monthly_nets)) + 1))
    
    return {
        'total_net_profit': total_net,
        'total_trades': total_trades,
        'avg_profit_factor': avg_pf,
        'worst_drawdown': worst_dd,
        'consistency_score': consistency,
        'periods_tested': len(results)
    }
