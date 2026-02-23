# =============================================================================
# YAVE BOT - TRADE MONITOR
# =============================================================================

import json
import os
from datetime import datetime

def show_stats():
    """Toon trade statistieken."""
    log_file = "logs/trade_log.json"
    
    print("="*70)
    print("📊 YAVE BOT - FORWARD TEST STATS")
    print("="*70)
    print(f"📅 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    if not os.path.exists(log_file):
        print("\n⏳ No trades yet. Waiting for signals...")
        return
    
    with open(log_file, 'r') as f:
        try:
            trades = json.load(f)
        except:
            print("\n⏳ No trades yet.")
            return
    
    print(f"📈 Total Trades: {len(trades)}")
    
    if len(trades) == 0:
        print("\n⏳ No trades yet.")
        return
    
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losses = sum(1 for t in trades if t.get('pnl', 0) <= 0)
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    
    win_rate = (wins / len(trades)) * 100 if len(trades) > 0 else 0
    
    print(f"\n✅ Wins: {wins}")
    print(f"❌ Losses: {losses}")
    print(f"📊 Win Rate: {win_rate:.1f}%")
    print(f"💰 Total PnL: ${total_pnl:.2f}")
    
    print(f"\n📋 Backtest Comparison (V4.2):")
    print(f"   Backtest Win Rate: 61.0%")
    print(f"   Forward Test Win Rate: {win_rate:.1f}%")
    print(f"   Difference: {win_rate - 61.0:+.1f}%")
    
    print(f"\n📝 Last 5 Trades:")
    for trade in trades[-5:]:
        pnl = trade.get('pnl', 0)
        symbol = '✅' if pnl > 0 else '❌'
        print(f"   {symbol} {trade.get('type', '?')} | PnL: ${pnl:.2f}")
    
    print("="*70)

if __name__ == "__main__":
    show_stats()
