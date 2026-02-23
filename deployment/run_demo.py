# =============================================================================
# YAVE BOT - DEMO TRADING RUNNER
# =============================================================================

import MetaTrader5 as mt5
from datetime import datetime
import json
import os
import time

def initialize_mt5():
    """Initialiseer MT5 verbinding."""
    if not mt5.initialize():
        print("❌ MT5 init failed")
        return False
    
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ No account info")
        return False
    
    print(f"✅ MT5 Connected")
    print(f"   Account: {account_info.login}")
    print(f"   Balance: ${account_info.balance:.2f}")
    print(f"   Server: {account_info.server}")
    
    return True

def main():
    print("="*70)
    print("🚀 YAVE BOT v4.2 - DEMO TRADING")
    print("="*70)
    print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    if not initialize_mt5():
        print("\n❌ Failed to initialize. Check MT5 is running.")
        return
    
    print("\n✅ Demo trading started!")
    print("   Strategy: Inverse Price Action v4.2")
    print("   Symbol: EURUSD M15")
    print("\n⚠️  Press Ctrl+C to stop")
    print("="*70)
    
    try:
        while True:
            # Wacht op nieuwe candle (elke 15 minuten)
            time.sleep(900)  # 15 minuten = 900 seconden
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Bot active...")
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    finally:
        mt5.shutdown()
        print("✅ MT5 disconnected")

if __name__ == "__main__":
    main()
