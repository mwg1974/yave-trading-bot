# =============================================================================
# VISUALIZER — Professional Charts & Reports
# =============================================================================
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
import config

def plot_equity_and_drawdown(equity_df, title="YAVE Bot Performance"):
    """Maakt equity curve + drawdown subplot."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})
    
    # Equity curve
    ax1.plot(equity_df.index, equity_df['equity'], label='Equity', color='#2E86AB', linewidth=2)
    ax1.axhline(y=config.INITIAL_CAPITAL, color='gray', linestyle='--', alpha=0.5, label='Start')
    ax1.set_title(f"{title}\nFinal: ${equity_df['equity'].iloc[-1]:,.2f} | "
                  f"Return: {(equity_df['equity'].iloc[-1]/config.INITIAL_CAPITAL - 1):.1%}")
    ax1.set_ylabel("Equity (USD)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Drawdown
    if 'drawdown' in equity_df.columns:
        ax2.fill_between(equity_df.index, equity_df['drawdown']*100, 0, 
                        color='#E63946', alpha=0.3, label='Drawdown')
        ax2.set_title(f"Max Drawdown: {equity_df['drawdown'].min():.1%}")
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Time")
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_trades_on_price(df_with_signals, trades, symbol, limit=1000):
    """Plot prijs met entry/exit markers (beperkt tot laatste N candles)."""
    plot_df = df_with_signals.iloc[-limit:].copy()
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 6))
    
    # Prijslijn
    ax.plot(plot_df.index, plot_df['close'], label='Price', color='#1D3557', linewidth=1)
    
    # Trades markers
    for trade in trades:
        if trade['entry_time'] in plot_df.index:
            entry_idx = plot_df.index.get_loc(trade['entry_time'])
            entry_price = trade['entry_price']
            color = 'green' if trade['pnl'] > 0 else 'red'
            marker = '^' if trade.get('pnl', 0) >= 0 else 'v'
            ax.scatter(plot_df.index[entry_idx], entry_price, 
                      color=color, marker=marker, s=100, zorder=5,
                      edgecolors='white', linewidth=1.5)
    
    # EMA's indien aanwezig
    for ema in [9, 21, 200]:
        col = f'ema_{ema}'
        if col in plot_df.columns:
            ax.plot(plot_df.index, plot_df[col], label=f'EMA {ema}', 
                   linestyle='--', alpha=0.6, linewidth=1)
    
    ax.set_title(f"{symbol} Price Action with Trades (last {limit} candles)")
    ax.set_ylabel("Price")
    ax.set_xlabel("Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def save_all_charts(backtest_result, output_dir=None):
    """Slaat alle visualisaties op."""
    out_dir = Path(output_dir or config.RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Equity + Drawdown
    fig1 = plot_equity_and_drawdown(backtest_result['equity_curve'])
    fig1.savefig(out_dir / "equity_drawdown.png", dpi=config.PLOT_DPI, bbox_inches='tight')
    plt.close(fig1)
    
    # 2. Trades on price
    if 'df_with_signals' in backtest_result and backtest_result['trades']:
        fig2 = plot_trades_on_price(
            backtest_result['df_with_signals'], 
            backtest_result['trades'],
            config.SYMBOL
        )
        fig2.savefig(out_dir / "trades_on_price.png", dpi=config.PLOT_DPI, bbox_inches='tight')
        plt.close(fig2)
    
    print(f"📊 Charts saved to {out_dir}/")
