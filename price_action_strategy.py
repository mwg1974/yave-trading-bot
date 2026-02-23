# =============================================================================
# INVERSE PRICE ACTION STRATEGY — FADE THE BREAKOUT
# =============================================================================
# Strategie: Doe het OMGEKEERDE van breakout
# - LONG wanneer prijs ONDER support breekt (mean reversion)
# - SHORT wanneer prijs BOVEN resistance breekt (fade the breakout)
# =============================================================================

import backtrader as bt
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

class InversePriceActionStrategy(bt.Strategy):
    params = (
        ('lookback', 50),
        ('risk_reward', 2.0),
        ('stop_loss_pips', 50),
    )
    
    def __init__(self):
        self.resistance = bt.indicators.Highest(self.data.high(-1), period=self.params.lookback)
        self.support = bt.indicators.Lowest(self.data.low(-1), period=self.params.lookback)
        
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.order = None
        # ✅ FIX: Geen self.buy_bracket of self.sell_bracket variabelen!
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED @ {order.executed.price:.5f}')
            else:
                self.log(f'SELL EXECUTED @ {order.executed.price:.5f}')
            self.order = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        if trade.pnl > 0:
            self.win_count += 1
            self.log(f'✅ WINNER: ${trade.pnl:.2f}')
        else:
            self.loss_count += 1
            self.log(f'❌ LOSER: ${trade.pnl:.2f}')
    
    def next(self):
        # Geen open orders
        if self.order:
            return
        
        # Geen positie → check entry
        if not self.position:
            current_price = self.data.close[0]
            resistance = self.resistance[0]
            support = self.support[0]
            
            # =========================================================
            # INVERSE LOGIC:
            # - SHORT wanneer prijs BOVEN resistance breekt (fade breakout)
            # - LONG wanneer prijs ONDER support breekt (mean reversion)
            # =========================================================
            
            # SHORT: Prijs breekt BOVEN resistance → Wij SHORTEN (fade)
            if current_price > resistance:
                sl_price = current_price + (self.params.stop_loss_pips * 0.0001)
                tp_price = current_price - ((sl_price - current_price) * self.params.risk_reward)
                
                self.order = self.sell()
                # ✅ FIX: Gebruik lokale variabele, niet self.buy_bracket
                bracket_orders = self.sell_bracket(
                    price=current_price,
                    stopprice=sl_price,
                    limitprice=tp_price,
                    plimit=tp_price
                )
                
                self.trade_count += 1
                self.log(f'📉 SHORT (FADE) #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {sl_price:.5f} | TP: {tp_price:.5f}')
            
            # LONG: Prijs breekt ONDER support → Wij KOPEN (mean reversion)
            elif current_price < support:
                sl_price = current_price - (self.params.stop_loss_pips * 0.0001)
                tp_price = current_price + ((current_price - sl_price) * self.params.risk_reward)
                
                self.order = self.buy()
                # ✅ FIX: Gebruik lokale variabele
                bracket_orders = self.buy_bracket(
                    price=current_price,
                    stopprice=sl_price,
                    limitprice=tp_price,
                    plimit=tp_price
                )
                
                self.trade_count += 1
                self.log(f'📈 LONG (REVERSION) #{self.trade_count} @ {current_price:.5f}')
                self.log(f'   SL: {sl_price:.5f} | TP: {tp_price:.5f}')
    
    def stop(self):
        print(f"\n{'='*70}")
        print(f"📊 INVERSE STRATEGY RESULTS")
        print(f"{'='*70}")
        print(f"Total Trades: {self.trade_count}")
        print(f"Winning: {self.win_count} | Losing: {self.loss_count}")
        
        total = self.win_count + self.loss_count
        if total > 0:
            win_rate = (self.win_count / total) * 100
            print(f"Win Rate: {win_rate:.1f}%")
            
            # Verwachte P/L met 1:2 RR
            avg_win = 2 * self.params.stop_loss_pips * 100000 * 0.1
            avg_loss = self.params.stop_loss_pips * 100000 * 0.1
            expected_pnl = (self.win_count * avg_win) - (self.loss_count * avg_loss)
            print(f"Expected P/L (theoretical): ${expected_pnl:.2f}")
        print(f"{'='*70}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 INVERSE PRICE ACTION — FADE THE BREAKOUT")
    print("="*70)
    
    # Forceer bar-by-bar execution
    cerebro = bt.Cerebro(runonce=False, preload=False, exactbars=1)
    
    cerebro.addstrategy(
        InversePriceActionStrategy,
        lookback=50,
        risk_reward=2.0,
        stop_loss_pips=50,
    )
    
    print("\n📡 Loading data...")
    
    if not mt5.initialize():
        print("❌ MT5 init failed")
        exit()
    
    symbol = "EURUSD"
    start = datetime(2024, 10, 1)
    end = datetime.now()
    
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("❌ No data")
        exit()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    df.to_csv("eurusd_m15_inverse.csv")
    print(f"✅ {len(df)} candles")
    
    data = bt.feeds.GenericCSVData(
        dataname="eurusd_m15_inverse.csv",
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
    cerebro.broker.set_slippage_perc(0.0001)
    
    print(f"\n💰 Start: ${cerebro.broker.getvalue():.2f}")
    print(f"\n🔄 Running...\n")
    
    cerebro.run()
    
    print(f"\n💰 Final: ${cerebro.broker.getvalue():.2f}")
    print(f"📈 P/L: ${cerebro.broker.getvalue() - 10000:.2f}")
    print("\n" + "="*70)
    print("✅ INVERSE STRATEGY TEST COMPLETED")
    print("="*70)