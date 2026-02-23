# =============================================================================
# FORWARD TEST LOGGER — Live Demo Tracking & Backtest Comparison
# =============================================================================
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import config

class ForwardLogger:
    """
    Logt live trades van demo account en vergelijkt met backtest verwachtingen.
    """
    
    def __init__(self, log_file=None, backtest_result=None):
        self.log_file = log_file or config.FORWARD_LOG_FILE
        self.backtest = backtest_result
        self.trades = []
        self.metrics = {
            'start_equity': config.INITIAL_CAPITAL,
            'current_equity': config.INITIAL_CAPITAL,
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0,
            'start_time': datetime.now().isoformat()
        }
        self._load_existing()
    
    def _load_existing(self):
        """Laad bestaande log indien aanwezig."""
        path = Path(self.log_file)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.trades = data.get('trades', [])
                    self.metrics.update(data.get('metrics', {}))
                print(f"✅ Forward log geladen: {len(self.trades)} trades")
            except:
                print("⚠️  Kon forward log niet laden, start nieuw")
    
    def log_trade_open(self, symbol, side, entry_price, lot_size, sl, tp, timestamp=None):
        """Log opening van trade."""
        trade = {
            'id': len(self.trades) + 1,
            'timestamp': timestamp or datetime.now().isoformat(),
            'symbol': symbol,
            'side': side,  # 'BUY' or 'SELL'
            'entry_price': entry_price,
            'lot_size': lot_size,
            'sl': sl,
            'tp': tp,
            'status': 'OPEN',
            'exit_price': None,
            'pnl': None,
            'exit_reason': None
        }
        self.trades.append(trade)
        self._save()
        print(f"📝 Trade #{trade['id']} logged: {side} {symbol} @ {entry_price}")
        return trade['id']
    
    def log_trade_close(self, trade_id, exit_price, exit_reason, pnl, timestamp=None):
        """Update trade met sluiting."""
        for trade in self.trades:
            if trade['id'] == trade_id:
                trade.update({
                    'status': 'CLOSED',
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl,
                    'closed_at': timestamp or datetime.now().isoformat()
                })
                # Update metrics
                self.metrics['total_trades'] += 1
                if pnl > 0:
                    self.metrics['winning_trades'] += 1
                self.metrics['total_pnl'] += pnl
                self.metrics['current_equity'] += pnl
                self._save()
                print(f"✅ Trade #{trade_id} closed: {exit_reason} | PnL: ${pnl:.2f}")
                return True
        print(f"❌ Trade ID {trade_id} niet gevonden")
        return False
    
    def update_equity(self, current_equity):
        """Update huidige equity (voor drawdown tracking)."""
        self.metrics['current_equity'] = current_equity
        self._save()
    
    def _save(self):
        """Sla log op naar JSON."""
        data = {
            'metrics': self.metrics,
            'trades': self.trades,
            'last_updated': datetime.now().isoformat()
        }
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def generate_comparison_report(self, output_file=None):
        """
        Genereer markdown rapport: backtest vs forward test performance.
        """
        output = output_file or config.FORWARD_COMPARE_REPORT
        
        # Bereken forward metrics
        fwd_trades = [t for t in self.trades if t['status'] == 'CLOSED']
        if fwd_trades:
            fwd_win_rate = sum(1 for t in fwd_trades if t['pnl'] > 0) / len(fwd_trades)
            fwd_avg_pnl = sum(t['pnl'] for t in fwd_trades) / len(fwd_trades)
            fwd_total_pnl = sum(t['pnl'] for t in fwd_trades)
        else:
            fwd_win_rate = fwd_avg_pnl = fwd_total_pnl = 0
        
        # Backtest metrics (indien beschikbaar)
        if self.backtest:
            bt_win_rate = self.backtest.get('win_rate', 0)
            bt_avg_pnl = (self.backtest.get('avg_win', 0) * self.backtest.get('win_rate', 0) + 
                         self.backtest.get('avg_loss', 0) * (1 - self.backtest.get('win_rate', 0)))
            bt_total_pnl = self.backtest.get('net_profit', 0)
        else:
            bt_win_rate = bt_avg_pnl = bt_total_pnl = None
        
        # Build report
        report = f"""# YAVE BOT — Backtest vs Forward Test Comparison
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 Summary
| Metric | Backtest | Forward Test | Difference |
|--------|----------|--------------|------------|
| Total Trades | {self.backtest.get('total_trades', 'N/A') if self.backtest else 'N/A'} | {len(fwd_trades)} | {len(fwd_trades) - (self.backtest.get('total_trades', 0) if self.backtest else 0)} |
| Win Rate | {bt_win_rate:.1% if bt_win_rate else 'N/A'} | {fwd_win_rate:.1%} | {(fwd_win_rate - bt_win_rate):.1% if bt_win_rate else 'N/A'} |
| Avg PnL/Trade | ${bt_avg_pnl:.2f if bt_avg_pnl else 'N/A'} | ${fwd_avg_pnl:.2f} | ${fwd_avg_pnl - bt_avg_pnl:.2f if bt_avg_pnl else 'N/A'} |
| Total PnL | ${bt_total_pnl:.2f if bt_total_pnl else 'N/A'} | ${fwd_total_pnl:.2f} | ${fwd_total_pnl - bt_total_pnl:.2f if bt_total_pnl else 'N/A'} |
| Max Drawdown | {self.backtest.get('max_drawdown', 'N/A') if self.backtest else 'N/A'} | N/A* | - |

*Drawdown tracking vereist equity snapshots

## 🎯 Verdict
"""
        if bt_win_rate and abs(fwd_win_rate - bt_win_rate) < 0.15:
            report += "✅ **Consistent**: Forward test binnen 15% van backtest verwachting.\n"
        elif bt_win_rate:
            report += "⚠️  **Deviation**: Forward test wijkt >15% af van backtest. Onderzoek oorzaken:\n"
            report += "- Slippage hoger dan geschat?\n"
            "- Marktregime veranderd?\n"
            "- Bug in live uitvoering?\n"
        else:
            report += "⏳ **Insufficient data**: Verzamel minimaal 20 forward trades voor vergelijking.\n"
        
        # Trade log preview
        if fwd_trades:
            report += f"\n## 📋 Recent Trades (laatste 5)\n"
            report += "| ID | Time | Side | Entry | Exit | PnL | Reason |\n"
            report += "|----|------|------|-------|------|-----|--------|\n"
            for t in fwd_trades[-5:]:
                report += f"| {t['id']} | {t['closed_at'][:16]} | {t['side']} | {t['entry_price']} | {t['exit_price']} | ${t['pnl']:.2f} | {t['exit_reason']} |\n"
        
        # Save
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            f.write(report)
        
        print(f"💾 Comparison report saved: {output}")
        return report
