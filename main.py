#!/usr/bin/env python3
# =============================================================================
# YAVE BOT v3.0 — MAIN EXECUTION
# =============================================================================
import sys
import json
import config
import data_handler
import backtest_engine
import walk_forward
import forward_logger
import visualizer
from pathlib import Path
from datetime import datetime

def main():
    print("="*70)
    print("🚀 YAVE TRADING BOT v3.0 — PROFESSIONAL AUDITED EDITION")
    print("="*70)
    
    # 1. Initialiseer
    if not data_handler.initialize_mt5():
        sys.exit(1)
    
    try:
        # 2. Haal data op
        print(f"\n📡 Loading  {config.SYMBOL} {config.TIMEFRAME_MT5}")
        df = data_handler.get_data(
            config.SYMBOL, 
            config.TIMEFRAME_MT5, 
            config.START_DATE, 
            config.END_DATE
        )
        if df is None:
            print("❌ Failed to load data. Exiting.")
            sys.exit(1)
        
        # 3. Kies modus
        if config.FORWARD_TEST_MODE:
            print("\n🔁 FORWARD TEST MODE")
            run_forward_test(df)
        else:
            print("\n🔍 BACKTEST + WALK-FORWARD MODE")
            run_backtest_suite(df)
            
    finally:
        data_handler.shutdown_mt5()
        print("\n✅ Yave Bot finished")

def run_backtest_suite(df):
    """Voert backtest + walk-forward validatie uit."""
    
    # A. Single backtest met default params
    print("\n📊 Running baseline backtest...")
    default_params = {
        'ema_fast': config.EMA_FAST_DEFAULT,
        'ema_slow': config.EMA_SLOW_DEFAULT,
        'use_trend_filter': config.USE_TREND_FILTER,
        'use_fvg_filter': config.USE_FVG_FILTER
    }
    baseline = backtest_engine.run_backtest(df, default_params)
    
    print(f"\n📈 Baseline Results (EMA {default_params['ema_fast']}/{default_params['ema_slow']}):")
    print(f"   Net Profit: ${baseline['net_profit']:.2f}")
    print(f"   Trades: {baseline['total_trades']}")
    print(f"   Win Rate: {baseline['win_rate']:.1%}")
    print(f"   Profit Factor: {baseline['profit_factor']:.2f}")
    print(f"   Max Drawdown: {baseline['max_drawdown']:.1%}")
    
    # B. Walk-forward validation
    print(f"\n🔄 Running walk-forward validation...")
    wf_results, wf_summary = walk_forward.walk_forward_validation(
        df, config.OPTIMIZE_RANGES
    )
    
    if wf_summary:
        print(f"\n🏆 Walk-Forward Summary:")
        print(f"   Periods Tested: {wf_summary['periods_tested']}")
        print(f"   Total Net Profit: ${wf_summary['total_net_profit']:.2f}")
        print(f"   Avg Profit Factor: {wf_summary['avg_profit_factor']:.2f}")
        print(f"   Worst Drawdown: {wf_summary['worst_drawdown']:.1%}")
        print(f"   Consistency Score: {wf_summary['consistency_score']:.1%}")
    
    # C. Visualisaties
    if config.SAVE_RESULTS:
        print(f"\n💾 Saving results...")
        try:
            visualizer.save_all_charts(baseline)
        except Exception as e:
            print(f"⚠️  Chart saving failed: {str(e)}")
        
        # Sla trades log op (met JSON fix)
        if baseline['trades']:
            out_dir = Path(config.RESULTS_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                # FIX: Converteer Timestamps naar strings voor JSON
                trades_serializable = []
                for t in baseline['trades']:
                    t_copy = {}
                    for key, value in t.items():
                        if hasattr(value, 'isoformat'):  # Timestamp check
                            t_copy[key] = value.isoformat()
                        elif isinstance(value, dict):
                            t_copy[key] = value
                        else:
                            t_copy[key] = value
                    trades_serializable.append(t_copy)
                
                with open(out_dir / "trades_log.json", 'w', encoding='utf-8') as f:
                    json.dump(trades_serializable, f, indent=2, ensure_ascii=False)
                print(f"💾 Trades log saved: {len(trades_serializable)} trades")
            except Exception as e:
                print(f"⚠️  Trades log saving failed: {str(e)}")
    
    # D. Joe's verdict
    print(f"\n" + "="*70)
    print("🧠 JOE'S VERDICT")
    print("="*70)
    if wf_summary:
        if wf_summary['avg_profit_factor'] > 1.3 and wf_summary['worst_drawdown'] > -0.25:
            print("✅ Strategie is ROBUST. Klaar voor forward test op demo.")
        elif wf_summary['avg_profit_factor'] > 1.0:
            print("⚠️  Strategie is MARGINAL. Overweeg:")
            print("   - Strengere filters")
            print("   - Langere timeframe (H1)")
            print("   - Andere EMA combinaties")
        else:
            print("❌ Strategie is NIET WINSTGEVEND in out-of-sample test.")
            print("   Niet gebruiken voor live trading.")
            print("\n💡 Overweeg:")
            print("   - Verhoog TP/SL ratio (bijv. 1:2 of 1:3)")
            print("   - Test op H1 timeframe (minder ruis)")
            print("   - Voeg trend filter toe (EMA 200)")
    else:
        print("⚠️  Walk-forward niet voltooid. Test handmatig op meerdere periodes.")
    
    print("="*70)

def run_forward_test(df):
    """Forward test mode: log trades voor demo vergelijking."""
    print("⚠️  Forward test vereist MT5 terminal met actieve trading.")
    print("   Deze modus is een skeleton — implementeer MT5 order execution.")
    
    # Initialize logger
    logger = forward_logger.ForwardLogger()
    
    # Placeholder: in echte implementatie, subscribe to MT5 events
    print("\n📡 Forward test logger ready.")
    print("   - Gebruik logger.log_trade_open() bij entry")
    print("   - Gebruik logger.log_trade_close() bij exit")
    print("   - Run generate_comparison_report() na 20+ trades")
    
    # Demo: genereer voorbeeld rapport
    if logger.trades:
        logger.generate_comparison_report()

if __name__ == "__main__":
    main()