# =============================================================================
# INVERSE PRICE ACTION — OPTIMIZED VERSION (GEFIXT)
# =============================================================================
# Verbeteringen:
# - Echte SL/TP (niet time-based)
# - 1:2 Risk/Reward ratio
# - H1 timeframe (minder ruis)
# - FIX: Alleen bracket orders (niet dubbele orders)
# - FIX: Stop() crash aan einde
# =============================================================================

import backtrader as bt
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

class InverseOptimizedStrategy(bt.Strategy):
    params = (
        ('lookback', 50),
        ('stop_loss_pips', 50),      # 50 pips SL
        ('take_profit_pips', 100),   # 100 pips TP (1:2 ratio)
    )
    
    def __init__(self):
        self.resistance = bt.indicators.Highest(self.data.high(-1), period=self.params.lookback)
        self.support = bt.indicators.Lowest(self.data.low(-1), period=self.params.lookback)
        
        # Stats
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_pnl = 0.0
        
        # Position tracking
        self.in_position = False
        self.entry_price = 0
        self.position_type = ''
        self.sl_price = 0
        self.tp_price = 0
        self.order = None
        self.bracket_orders = None
    
    def log(self, txt, dt=None):
        try:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
        except:
            print(f'{datetime.now().strftime("%Y-%m-%d")} {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY @ {order.executed.price:.5f}')
            else:
                self.log(f'SELL @ {order.executed.price:.5f}')
            self.order = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected')
            self.order = None
    
    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            self.total_pnl += pnl
            
            if pnl > 0:
                self.win_count += 1
                self.log(f'✅ WIN: ${pnl:.2f}')
            else:
                self.loss_count += 1
                self.log(f'❌ LOSS: ${pnl:.2f}')
    
    def next(self):
        # Geen nieuwe entries als we al in positie zitten
        if self.in_position:
            return
        
        # Geen open orders
        if self.order:
            return
        
        # Check voor entry
        if not self.in_position and self.order is None:
            current_price = self.data.close[0]
            resistance = self.resistance[0]
            support = self.support[0]
            
            # =========================================================
            # INVERSE LOGIC:
            # SHORT bij breakout boven resistance (fade)
            # LONG bij breakout onder support (reversion)
            # =========================================================
            
            # SHORT: Prijs breekt BOVEN resistance → Wij SHORTEN
            if current_price > resistance:
                self.sl_price = current_price + (self.params.stop_loss_pips * 0.0001)
                self.tp_price = current_price - (self.params.take_profit_pips * 0.0001)
                
                # ✅ FIX: Alleen bracket order (niet eerst self.sell())
                self.bracket_orders = self.sell_bracket(
                    price=current_price,
                    stopprice=self.sl_price,
                    limitprice=self.tp_price,
                    plimit=self.tp_price
                )
                
                self.entry_price = current_price
                self.position_type = 'SHORT'
                self.in_position = True
                
                self.trade_count += 1
                self.log(f'📉 SHORT #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} ({self.params.stop_loss_pips} pips)')
                self.log(f'   TP: {self.tp_price:.5f} ({self.params.take_profit_pips} pips)')
            
            # LONG: Prijs breekt ONDER support → Wij KOPEN
            elif current_price < support:
                self.sl_price = current_price - (self.params.stop_loss_pips * 0.0001)
                self.tp_price = current_price + (self.params.take_profit_pips * 0.0001)
                
                # ✅ FIX: Alleen bracket order (niet eerst self.buy())
                self.bracket_orders = self.buy_bracket(
                    price=current_price,
                    stopprice=self.sl_price,
                    limitprice=self.tp_price,
                    plimit=self.tp_price
                )
                
                self.entry_price = current_price
                self.position_type = 'LONG'
                self.in_position = True
                
                self.trade_count += 1
                self.log(f'📈 LONG #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} ({self.params.stop_loss_pips} pips)')
                self.log(f'   TP: {self.tp_price:.5f} ({self.params.take_profit_pips} pips)')
    
    def stop(self):
        # ✅ FIX: Sluit open positie aan einde (met try/except)
        if self.in_position:
            try:
                self.close()
                self.log(f'⚠️  Position closed at end')
            except Exception as e:
                print(f'⚠️  Position close skipped (end of data)')
        
        print(f"\n{'='*70}")
        print(f"📊 INVERSE OPTIMIZED STRATEGY RESULTS")
        print(f"{'='*70}")
        print(f"Total Trades: {self.trade_count}")
        print(f"Winning Trades: {self.win_count}")
        print(f"Losing Trades: {self.loss_count}")
        
        total_closed = self.win_count + self.loss_count
        if total_closed > 0:
            win_rate = (self.win_count / total_closed) * 100
            print(f"Win Rate: {win_rate:.1f}%")
            print(f"Total PnL: ${self.total_pnl:.2f}")
            print(f"Average PnL per Trade: ${self.total_pnl / self.trade_count:.2f}")
            
            # Risk/Reward analyse
            if self.win_count > 0:
                avg_win = self.total_pnl / self.win_count
                print(f"\n📈 Risk/Reward Analyse:")
                print(f"   Average Win: ${avg_win:.2f}")
                if self.loss_count > 0:
                    avg_loss = abs(self.total_pnl / self.loss_count)
                    print(f"   Average Loss: ${avg_loss:.2f}")
                    if avg_loss > 0:
                        print(f"   Win/Loss Ratio: {avg_win/avg_loss:.2f}:1")
        print(f"{'='*70}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 INVERSE PRICE ACTION — OPTIMIZED (H1 + SL/TP)")
    print("="*70)
    
    # Forceer bar-by-bar execution
    cerebro = bt.Cerebro(runonce=False, preload=False, exactbars=1)
    
    cerebro.addstrategy(
        InverseOptimizedStrategy,
        lookback=50,
        stop_loss_pips=50,      # 50 pips SL
        take_profit_pips=100,   # 100 pips TP (1:2 ratio)
    )
    
    print("\n📡 Loading H1 data...")
    
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_H1  # ← H1 timeframe
    start = datetime(2024, 1, 1)
    end = datetime.now()
    
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("❌ No data")
        exit()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    df.to_csv("eurusd_h1_inverse.csv")
    print(f"✅ {len(df)} H1 candles geladen")
    
    data = bt.feeds.GenericCSVData(
        dataname="eurusd_h1_inverse.csv",
        dtformat='%Y-%m-%d %H:%M:%S',
        datetime=0, open=1, high=2, low=3, close=4, volume=5,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=60,  # H1 = 60 minuten
    )
    
    cerebro.adddata(data)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0001)
    cerebro.addsizer(bt.sizers.FixedSize, stake=10000)
    
    print(f"\n💰 Start: ${cerebro.broker.getvalue():.2f}")
    print(f"\n🔄 Running optimized backtest...\n")
    
    cerebro.run()
    
    print(f"\n💰 Final: ${cerebro.broker.getvalue():.2f}")
    print(f"📈 P/L: ${cerebro.broker.getvalue() - 10000:.2f}")
    print(f"📊 Return: {((cerebro.broker.getvalue() / 10000) - 1) * 100:.2f}%")
    print("\n" + "="*70)
    print("✅ OPTIMIZED TEST COMPLETED")
    print("="*70)