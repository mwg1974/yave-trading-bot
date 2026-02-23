# =============================================================================
# BACKTRADER TEST — EMA 5/20 Crossover op EURUSD
# =============================================================================
# Dit is de ZELFDE strategie als jouw custom engine, maar dan met Backtrader
# Als dit WEL werkt → jouw engine had een bug
# Als dit OOK faalt → de strategie deugt niet (niet de code)
# =============================================================================

import backtrader as bt
from datetime import datetime

# =============================================================================
# STRATEGY — EMA 5/20 Crossover
# =============================================================================
class EMA520Strategy(bt.Strategy):
    params = (
        ('ema_fast', 5),
        ('ema_slow', 20),
    )
    
    def __init__(self):
        # Bereken EMA's
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)
        
        # Crossover signal (1 = bullish cross, -1 = bearish cross)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        
        # Debug counters
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
    
    def next(self):
        # Geen positie → check voor entry
        if not self.position:
            if self.crossover > 0:  # EMA fast kruist boven slow → LONG
                self.buy()
                self.trade_count += 1
                print(f"   📈 BUY @ {self.data.close[0]:.5f} (Trade #{self.trade_count})")
            elif self.crossover < 0:  # EMA fast kruist onder slow → SHORT
                self.sell()
                self.trade_count += 1
                print(f"   📉 SELL @ {self.data.close[0]:.5f} (Trade #{self.trade_count})")
        
        # Wel positie → check voor exit
        else:
            if self.position.size > 0:  # Long positie
                if self.crossover < 0:  # Bearish cross → sluit long
                    self.close()
                    self.trade_count += 1
                    print(f"   ❌ CLOSE LONG @ {self.data.close[0]:.5f}")
            elif self.position.size < 0:  # Short positie
                if self.crossover > 0:  # Bullish cross → sluit short
                    self.close()
                    self.trade_count += 1
                    print(f"   ❌ CLOSE SHORT @ {self.data.close[0]:.5f}")
    
    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            if pnl > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            print(f"   💰 Trade Closed: PnL = ${pnl:.2f}")
    
    def stop(self):
        print(f"\n{'='*60}")
        print(f"📊 STRATEGY RESULTS")
        print(f"{'='*60}")
        print(f"Total Trades: {self.trade_count}")
        print(f"Winning Trades: {self.win_count}")
        print(f"Losing Trades: {self.loss_count}")
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            print(f"Win Rate: {win_rate:.1f}%")
        print(f"{'='*60}")

# =============================================================================
# MAIN — Run Backtest
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BACKTRADER TEST — EMA 5/20 EURUSD M15")
    print("="*70)
    
    # Create Cerebro (backtest engine)
    cerebro = bt.Cerebro()
    
    # Add strategy
    cerebro.addstrategy(EMA520Strategy, ema_fast=5, ema_slow=20)
    
    # =============================================================================
    # DATA — Haal data van MT5 en exporteer naar CSV
    # =============================================================================
    print("\n📡 Loading data from MT5...")
    
    import MetaTrader5 as mt5
    import pandas as pd
    
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_M15
    start = datetime(2024, 10, 1)
    end = datetime.now()
    
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("❌ No data received")
        exit()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Backtrader verwacht specifieke kolomnamen
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Sla op als CSV (Backtrader leest CSV)
    csv_file = "eurusd_m15.csv"
    df.to_csv(csv_file)
    print(f"✅ Data exported to {csv_file} ({len(df)} candles)")
    
    # =============================================================================
    # DATA FEED — Laad CSV in Backtrader
    # =============================================================================
    data = bt.feeds.GenericCSVData(
        dataname=csv_file,
        dtformat='%Y-%m-%d %H:%M:%S',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=15,  # M15 candles
    )
    
    cerebro.adddata(data)
    
    # =============================================================================
    # BROKER — Setup
    # =============================================================================
    # Start capital
    cerebro.broker.setcash(10000.0)
    
    # Commission (0.01% voor forex)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Position sizing (fixed size voor nu)
    cerebro.addsizer(bt.sizers.FixedSize, stake=10000)  # 10,000 units per trade
    
    # =============================================================================
    # RUN BACKTEST
    # =============================================================================
    print(f"\n💰 Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    print(f"\n🔄 Running backtest...\n")
    
    results = cerebro.run()
    
    # =============================================================================
    # RESULTS
    # =============================================================================
    final_value = cerebro.broker.getvalue()
    print(f"\n💰 Final Portfolio Value: ${final_value:.2f}")
    print(f"📈 Profit/Loss: ${final_value - 10000:.2f}")
    print(f"📊 Return: {((final_value / 10000) - 1) * 100:.2f}%")
    
    # Plot (optioneel)
    # cerebro.plot(style='candle', volume=True)
    
    print("\n" + "="*70)
    print("✅ BACKTRADER TEST COMPLETED")
    print("="*70)
