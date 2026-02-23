# =============================================================================
# SESSION_FILTER.py — Check Trading Uren (London/NY Overlap)
# =============================================================================
from datetime import datetime

def is_trading_session(timestamp=None):
    """
    Check of een timestamp binnen de trading sessie valt.
    
    ✅ TRADE TIJDEN (Amsterdam tijd):
    - London Open: 08:00 - 10:00
    - London/NY Overlap: 14:00 - 17:00
    - Dinsdag t/m Donderdag (optioneel, voor nu alle dagen behalve weekend)
    
    ❌ NIET TRADE TIJDEN:
    - Aziatische sessie: 00:00 - 07:00
    - Lunch dip: 12:00 - 13:00
    - Avond: na 20:00
    - Vrijdag na 16:00 (weekend gap risk)
    - Weekend: Zaterdag & Zondag
    
    Returns: True als binnen trading sessie, False als niet
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Check weekend (Saterdag=5, Zondag=6)
    if timestamp.weekday() >= 5:
        return False
    
    hour = timestamp.hour
    
    # ✅ TRADE WINDOWS (Amsterdam tijd)
    # London Open: 08:00 - 10:00
    london_open = (8 <= hour < 10)
    
    # London/NY Overlap: 14:00 - 17:00
    london_ny_overlap = (14 <= hour < 17)
    
    # Combineer trade windows
    is_in_session = london_open or london_ny_overlap
    
    # ❌ Vrijdag restrictie: stop om 16:00 (weekend risk)
    if timestamp.weekday() == 4:  # Vrijdag
        if hour >= 16:
            return False
    
    return is_in_session

def get_session_name(timestamp=None):
    """
    Returns de naam van de huidige sessie.
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    if timestamp.weekday() >= 5:
        return "WEEKEND"
    
    hour = timestamp.hour
    
    if 0 <= hour < 7:
        return "ASIAN_EARLY"
    elif 7 <= hour < 8:
        return "ASIAN_LATE"
    elif 8 <= hour < 10:
        return "LONDON_OPEN"  # ✅ Trade
    elif 10 <= hour < 12:
        return "LONDON_MID"
    elif 12 <= hour < 14:
        return "LUNCH_DIP"
    elif 14 <= hour < 17:
        return "LONDON_NY_OVERLAP"  # ✅ Trade
    elif 17 <= hour < 20:
        return "NY_AFTERNOON"
    else:
        return "EVENING"

def is_optimal_trade_time(timestamp=None):
    """
    Check of het een OPTIMALE trade tijd is (binnen de beste windows).
    Returns: True voor London Open + London/NY Overlap, False anders
    """
    return is_trading_session(timestamp)

# =============================================================================
# TEST FUNCTIE
# =============================================================================
if __name__ == "__main__":
    print("="*60)
    print("SESSION FILTER TEST")
    print("="*60)
    
    # Test verschillende tijden
    test_times = [
        datetime(2026, 2, 23, 3, 0),   # Aziatische sessie (nacht)
        datetime(2026, 2, 23, 9, 0),   # London Open ✅
        datetime(2026, 2, 23, 12, 0),  # Lunch dip
        datetime(2026, 2, 23, 15, 0),  # London/NY Overlap ✅
        datetime(2026, 2, 23, 20, 0),  # Avond
        datetime(2026, 2, 23, 23, 0),  # Nacht
        datetime(2026, 2, 28, 15, 0),  # Vrijdag 15:00 ✅
        datetime(2026, 2, 28, 17, 0),  # Vrijdag 17:00 ❌
        datetime(2026, 2, 21, 15, 0),  # Zaterdag ❌
        datetime(2026, 2, 22, 15, 0),  # Zondag ❌
    ]
    
    print(f"\nHuidige tijd: {datetime.now()}")
    print(f"Huidige sessie: {get_session_name()}")
    print(f"Trade nu? {is_trading_session()}\n")
    
    print("-"*60)
    print(f"{'Tijd':<25} {'Dag':<12} {'Sessie':<20} {'Trade?':<10}")
    print("-"*60)
    
    for t in test_times:
        day_name = t.strftime('%A')
        session = get_session_name(t)
        trade = "✅ JA" if is_trading_session(t) else "❌ NEE"
        print(f"{t.strftime('%Y-%m-%d %H:%M'):<25} {day_name:<12} {session:<20} {trade:<10}")
    
    print("-"*60)
    print("\n✅ Session filter test voltooid!")
