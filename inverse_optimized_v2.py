# =============================================================================
# INVERSE PRICE ACTION — OPTIMIZED V2 (SL/TP ZONDER BRACKET ORDERS)
# =============================================================================
# Wat werkt:
# - Simpele buy()/sell() (geen bracket orders)
# - Handmatige SL/TP check in next()
# - Exit na N candles als backup
# =============================================================================

import backtrader as bt
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

class InverseOptimizedV2Strategy(bt.Strategy):
    params = (
        ('lookback', 50),
        ('stop_loss_pips', 50),
        ('take_profit_pips', 100),
        ('max_candles', 50),  # Max 50 candles in trade (backup exit)
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
                
                self.trade_count += 1
                self.log(f'📉 SHORT #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} | TP: {self.tp_price:.5f}')
            
            # LONG: Prijs breekt ONDER support
            elif current_price < support:
                self.order = self.buy()
                self.entry_price = current_price
                self.position_type = 'LONG'
                self.sl_price = current_price - (self.params.stop_loss_pips * 0.0001)
                self.tp_price = current_price + (self.params.take_profit_pips * 0.0001)
                self.in_position = True
                self.candle_counter = 0
                
                self.trade_count += 1
                self.log(f'📈 LONG #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {self.sl_price:.5f} | TP: {self.tp_price:.5f}')
        
        # Als we WEL in positie zitten, check SL/TP
        else:
            self.candle_counter += 1
            current_price = self.data.close[0]
            
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
        print(f"📊 INVERSE OPTIMIZED V2 RESULTS")
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
            
            if self.win_count > 0 and self.loss_count > 0:
                avg_win = self.total_pnl / self.win_count
                avg_loss = abs(self.total_pnl / self.loss_count)
                print(f"\n📈 Risk/Reward:")
                print(f"   Avg Win: ${avg_win:.2f}")
                print(f"   Avg Loss: ${avg_loss:.2f}")
                if avg_loss > 0:
                    print(f"   Win/Loss Ratio: {avg_win/avg_loss:.2f}:1")
        print(f"{'='*70}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 INVERSE PRICE ACTION — OPTIMIZED V2 (SL/TP MANUAL)")
    print("="*70)
    
    cerebro = bt.Cerebro(runonce=False, preload=False, exactbars=1)
    
    cerebro.addstrategy(
        InverseOptimizedV2Strategy,
        lookback=50,
        stop_loss_pips=50,
        take_profit_pips=100,
        max_candles=50,
    )
    
    print("\n📡 Loading M15 data...")
    
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_M15  # ← TERUG NAAR M15 (werkt!)
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
    df.to_csv("eurusd_m15_inverse_v2.csv")
    print(f"✅ {len(df)} M15 candles")
    
    data = bt.feeds.GenericCSVData(
        dataname="eurusd_m15_inverse_v2.csv",
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
    print(f"\n🔄 Running...\n")
    
    cerebro.run()
    
    print(f"\n💰 Final: ${cerebro.broker.getvalue():.2f}")
    print(f"📈 P/L: ${cerebro.broker.getvalue() - 10000:.2f}")
    print(f"📊 Return: {((cerebro.broker.getvalue() / 10000) - 1) * 100:.2f}%")
    print("\n" + "="*70)
    print("✅ TEST COMPLETED")
    print("="*70)
