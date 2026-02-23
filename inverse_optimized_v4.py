# =============================================================================
# INVERSE PRICE ACTION — OPTIMIZED V4 (REALISTIC RR + AGGRESSIVE TRAIL)
# =============================================================================
# Verbeteringen t.o.v. V3:
# - Trailing activeert eerder (40 pips i.p.v. 60)
# - Tighter trail (20 pips i.p.v. 30)
# - Realistische TP (80 pips i.p.v. 120)
# - Sneller cut (25 candles i.p.v. 30)
# - 1:2 RR (nog steeds uitstekend!)
# =============================================================================

import backtrader as bt
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

class InverseOptimizedV4Strategy(bt.Strategy):
    params = (
        ('lookback', 50),
        ('stop_loss_pips', 40),       # 40 pips SL
        ('take_profit_pips', 80),     # 80 pips TP (1:2 RR - realistischer!)
        ('max_candles', 25),          # Max 25 candles (sneller cut)
        ('trail_activation_pips', 40), # Start trail na 40 pips (i.p.v. 60)
        ('trail_distance_pips', 20),   # Trail afstand 20 pips (tighter!)
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
        self.candle_counter = 0
        self.order = None
        
        # Trailing stop tracking
        self.trailing_active = False
        self.best_price = 0
        self.current_sl = 0
    
    def log(self, txt, dt=None):
        try:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
        except:
            print(f'{datetime.now().strftime("%Y-%m-%d")} {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY @ {order.executed.price:.5f}')
            else:
                self.log(f'SELL @ {order.executed.price:.5f}')
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
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
    
    def update_trailing_stop(self, current_price):
        """Update trailing stop als winst groot genoeg is."""
        if self.position_type == 'LONG':
            unrealized_pips = (current_price - self.entry_price) / 0.0001
            
            # Activeer trailing na 40 pips winst (i.p.v. 60)
            if unrealized_pips >= self.params.trail_activation_pips:
                self.trailing_active = True
                
                # Track beste prijs
                if current_price > self.best_price:
                    self.best_price = current_price
                    # Nieuwe SL = beste prijs - trail distance
                    self.current_sl = self.best_price - (self.params.trail_distance_pips * 0.0001)
                    
                    # SL mag alleen omhoog (voor long)
                    if self.current_sl > self.sl_price:
                        self.sl_price = self.current_sl
                        self.log(f'   📈 Trailing SL → {self.sl_price:.5f}')
        
        elif self.position_type == 'SHORT':
            unrealized_pips = (self.entry_price - current_price) / 0.0001
            
            # Activeer trailing na 40 pips winst (i.p.v. 60)
            if unrealized_pips >= self.params.trail_activation_pips:
                self.trailing_active = True
                
                # Track beste prijs
                if current_price < self.best_price or self.best_price == 0:
                    self.best_price = current_price
                    # Nieuwe SL = beste prijs + trail distance
                    self.current_sl = self.best_price + (self.params.trail_distance_pips * 0.0001)
                    
                    # SL mag alleen omlaag (voor short)
                    if self.current_sl < self.sl_price:
                        self.sl_price = self.current_sl
                        self.log(f'   📉 Trailing SL → {self.sl_price:.5f}')
    
    def next(self):
        # Als we niet in positie zitten, check voor entry
        if not self.in_position:
            if self.order:
                return
            
            current_price = self.data.close[0]
            resistance = self.resistance[0]
            support = self.support[0]
            
            # SHORT: Prijs breekt BOVEN resistance
            if current_price > resistance:
                self.order = self.sell()
                self.entry_price = current_price
                self.position_type = 'SHORT'
                self.sl_price = current_price + (self.params.stop_loss_pips * 0.0001)
                self.tp_price = current_price - (self.params.take_profit_pips * 0.0001)
                self.in_position = True
                self.candle_counter = 0
                self.trailing_active = False
                self.best_price = 0
                self.current_sl = self.sl_price
                
                self.trade_count += 1
                self.log(f'📉 SHORT #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} ({self.params.stop_loss_pips} pips)')
                self.log(f'   TP: {self.tp_price:.5f} ({self.params.take_profit_pips} pips) | 1:{self.params.take_profit_pips/self.params.stop_loss_pips:.0f} RR')
            
            # LONG: Prijs breekt ONDER support
            elif current_price < support:
                self.order = self.buy()
                self.entry_price = current_price
                self.position_type = 'LONG'
                self.sl_price = current_price - (self.params.stop_loss_pips * 0.0001)
                self.tp_price = current_price + (self.params.take_profit_pips * 0.0001)
                self.in_position = True
                self.candle_counter = 0
                self.trailing_active = False
                self.best_price = 0
                self.current_sl = self.sl_price
                
                self.trade_count += 1
                self.log(f'📈 LONG #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} ({self.params.stop_loss_pips} pips)')
                self.log(f'   TP: {self.tp_price:.5f} ({self.params.take_profit_pips} pips) | 1:{self.params.take_profit_pips/self.params.stop_loss_pips:.0f} RR')
        
        # Als we WEL in positie zitten, check SL/TP/Trailing/Time
        else:
            self.candle_counter += 1
            current_price = self.data.close[0]
            
            # Update trailing stop (check eerst!)
            self.update_trailing_stop(current_price)
            
            # Check Stop Loss
            if self.position_type == 'LONG' and current_price <= self.sl_price:
                self.log(f'❌ SL HIT (LONG) @ {current_price:.5f}')
                self.close()
                self.in_position = False
                self.order = None
                return
            
            elif self.position_type == 'SHORT' and current_price >= self.sl_price:
                self.log(f'❌ SL HIT (SHORT) @ {current_price:.5f}')
                self.close()
                self.in_position = False
                self.order = None
                return
            
            # Check Take Profit
            if self.position_type == 'LONG' and current_price >= self.tp_price:
                self.log(f'✅ TP HIT (LONG) @ {current_price:.5f}')
                self.close()
                self.in_position = False
                self.order = None
                return
            
            elif self.position_type == 'SHORT' and current_price <= self.tp_price:
                self.log(f'✅ TP HIT (SHORT) @ {current_price:.5f}')
                self.close()
                self.in_position = False
                self.order = None
                return
            
            # Backup: Exit na max_candles
            if self.candle_counter >= self.params.max_candles:
                self.log(f'⏰ TIME EXIT @ {current_price:.5f} ({self.candle_counter} candles)')
                self.close()
                self.in_position = False
                self.order = None
                return
    
    def stop(self):
        if self.in_position:
            try:
                self.close()
                self.log(f'⚠️  Position closed at end')
            except:
                print('⚠️  Position close skipped')
        
        print(f"\n{'='*70}")
        print(f"📊 INVERSE OPTIMIZED V4 RESULTS")
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
            if self.win_count > 0 and self.loss_count > 0:
                avg_win = self.total_pnl / self.win_count
                avg_loss = abs(self.total_pnl / self.loss_count)
                print(f"\n📈 Risk/Reward Analyse:")
                print(f"   Avg Win: ${avg_win:.2f}")
                print(f"   Avg Loss: ${avg_loss:.2f}")
                if avg_loss > 0:
                    print(f"   Win/Loss Ratio: {avg_win/avg_loss:.2f}:1")
                    print(f"   Target RR: 1:{self.params.take_profit_pips/self.params.stop_loss_pips:.0f}")
            
            # Profit Factor
            if self.loss_count > 0:
                gross_wins = self.win_count * avg_win
                gross_losses = self.loss_count * avg_loss
                pf = gross_wins / gross_losses
                print(f"   Profit Factor: {pf:.2f}")
                
                # Oordeel
                if pf > 1.5:
                    print(f"   🏆 EXCELLENT! (>1.5) — Professioneel niveau!")
                elif pf > 1.2:
                    print(f"   ✅ GOOD! (>1.2) — Winstgevend!")
                elif pf > 1.0:
                    print(f"   ⚠️  Break-even — Kan beter")
                else:
                    print(f"   ❌ Needs work (<1.0)")
        print(f"{'='*70}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 INVERSE PRICE ACTION — OPTIMIZED V4 (REALISTIC RR)")
    print("="*70)
    
    cerebro = bt.Cerebro(runonce=False, preload=False, exactbars=1)
    
    cerebro.addstrategy(
        InverseOptimizedV4Strategy,
        lookback=50,
        stop_loss_pips=40,        # 40 pips SL
        take_profit_pips=80,      # 80 pips TP (1:2 RR)
        max_candles=25,           # Max 25 candles
        trail_activation_pips=40, # Start trail na 40 pips
        trail_distance_pips=20,   # Trail afstand 20 pips
    )
    
    print("\n📡 Loading M15 data...")
    
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
        print("❌ No data")
        exit()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    df.to_csv("eurusd_m15_inverse_v4.csv")
    print(f"✅ {len(df)} M15 candles")
    
    data = bt.feeds.GenericCSVData(
        dataname="eurusd_m15_inverse_v4.csv",
        dtformat='%Y-%m-%d %H:%M:%S',
        datetime=0, open=1, high=2, low=3, close=4, volume=5,
        openinterest=-1,
        timeframe=bt.TimeFrame.Minutes,
        compression=15,
    )
    
    cerebro.adddata(data)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0001)
    cerebro.addsizer(bt.sizers.FixedSize, stake=10000)
    
    print(f"\n💰 Start: ${cerebro.broker.getvalue():.2f}")
    print(f"\n🔄 Running V4 optimized backtest...\n")
    
    cerebro.run()
    
    print(f"\n💰 Final: ${cerebro.broker.getvalue():.2f}")
    print(f"📈 P/L: ${cerebro.broker.getvalue() - 10000:.2f}")
    print(f"📊 Return: {((cerebro.broker.getvalue() / 10000) - 1) * 100:.2f}%")
    print("\n" + "="*70)
    print("✅ V4 TEST COMPLETED")
    print("="*70)
