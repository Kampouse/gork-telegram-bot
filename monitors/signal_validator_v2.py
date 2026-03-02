#!/usr/bin/env python3
"""
SIGNAL VALIDATOR with Auto-Expiration
- Logs signals with timestamps
- Auto-expires after hold period
- Tracks hit/miss/stopped
"""

import json
import requests
from datetime import datetime, timedelta
import os

SIGNAL_LOG = "/Users/asil/.openclaw/workspace/backtesting/signal_validation_log.json"

# Hold periods (hours)
HOLD_PERIODS = {
    "breakdown": 24,
    "death_cross": 72,
    "reversal": 72,
    "ga_rsi": 72,
    "donchian": 72,
    "default": 72
}

def load_signals():
    if os.path.exists(SIGNAL_LOG):
        with open(SIGNAL_LOG, "r") as f:
            return json.load(f)
    return {"signals": [], "stats": {"total": 0, "correct": 0, "pending": 0, "missed": 0}}

def save_signals(data):
    with open(SIGNAL_LOG, "w") as f:
        json.dump(data, f, indent=2)

def get_price(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": 1}
    data = requests.get(url, params=params, timeout=30).json()
    return float(data[0][4])

def add_signal(symbol, signal_type, entry_price, target_price, stop_price, strategy, win_rate, leverage=1, hold_hours=None):
    """Add a new signal with timestamp and expiration"""
    data = load_signals()
    
    # Determine hold period
    if hold_hours is None:
        hold_hours = HOLD_PERIODS.get(strategy.lower().replace(" ", "_"), HOLD_PERIODS["default"])
    
    now = datetime.now()
    expires_at = now + timedelta(hours=hold_hours)
    
    signal = {
        "id": f"{symbol}_{int(now.timestamp())}",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "symbol": symbol,
        "type": signal_type,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_price": stop_price,
        "strategy": strategy,
        "win_rate": win_rate,
        "leverage": leverage,
        "hold_hours": hold_hours,
        "status": "pending",
        "checks": []
    }
    
    data["signals"].append(signal)
    data["stats"]["total"] += 1
    data["stats"]["pending"] += 1
    
    save_signals(data)
    
    print(f"✅ Signal logged: {symbol} {signal_type} @ ${entry_price:.2f}")
    print(f"   Target: ${target_price:.2f} | Stop: ${stop_price:.2f}")
    print(f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M')}")
    
    return signal

def check_signals():
    """Check all pending signals and auto-expire"""
    data = load_signals()
    now = datetime.now()
    updated = False
    
    for signal in data["signals"]:
        if signal["status"] != "pending":
            continue
        
        # Get current price
        try:
            current_price = get_price(signal["symbol"])
        except:
            continue
        
        # Log check
        check = {
            "at": now.isoformat(),
            "price": current_price
        }
        signal["checks"].append(check)
        
        # Check if hit target or stopped
        hit_target = False
        hit_stop = False
        
        if signal["type"] == "SHORT":
            hit_target = current_price <= signal["target_price"]
            hit_stop = current_price >= signal["stop_price"]
            pnl = (signal["entry_price"] - current_price) / signal["entry_price"] * 100
        else:  # LONG
            hit_target = current_price >= signal["target_price"]
            hit_stop = current_price <= signal["stop_price"]
            pnl = (current_price - signal["entry_price"]) / signal["entry_price"] * 100
        
        # Check expiration
        expires_at = datetime.fromisoformat(signal["expires_at"])
        expired = now >= expires_at
        
        if hit_target:
            signal["status"] = "hit"
            signal["final_price"] = current_price
            signal["final_pnl_pct"] = pnl
            signal["closed_at"] = now.isoformat()
            signal["close_reason"] = "target_hit"
            data["stats"]["correct"] += 1
            data["stats"]["pending"] -= 1
            updated = True
            print(f"✅ HIT: {signal['symbol']} {signal['type']} @ ${current_price:.2f} (PnL: {pnl:+.1f}%)")
            
        elif hit_stop:
            signal["status"] = "stopped"
            signal["final_price"] = current_price
            signal["final_pnl_pct"] = pnl
            signal["closed_at"] = now.isoformat()
            signal["close_reason"] = "stop_hit"
            data["stats"]["pending"] -= 1
            updated = True
            print(f"🛑 STOPPED: {signal['symbol']} {signal['type']} @ ${current_price:.2f} (PnL: {pnl:+.1f}%)")
            
        elif expired:
            signal["status"] = "expired"
            signal["final_price"] = current_price
            signal["final_pnl_pct"] = pnl
            signal["closed_at"] = now.isoformat()
            signal["close_reason"] = "expired"
            if pnl > 0:
                data["stats"]["correct"] += 1
            else:
                data["stats"]["missed"] += 1
            data["stats"]["pending"] -= 1
            updated = True
            print(f"⏰ EXPIRED: {signal['symbol']} {signal['type']} @ ${current_price:.2f} (PnL: {pnl:+.1f}%)")
    
    if updated:
        save_signals(data)
    
    return data

def print_stats():
    """Print current stats"""
    data = load_signals()
    
    print("\n" + "=" * 60)
    print("📊 SIGNAL ACCURACY")
    print("=" * 60)
    print(f"Total: {data['stats']['total']}")
    print(f"✅ Hit: {data['stats']['correct']}")
    print(f"🛑 Stopped: {data['stats'].get('missed', 0)}")
    print(f"⏳ Pending: {data['stats']['pending']}")
    
    closed = data['stats']['correct'] + data['stats'].get('missed', 0)
    if closed > 0:
        hit_rate = data['stats']['correct'] / closed * 100
        print(f"\nHit Rate: {hit_rate:.1f}%")
    
    # Show recent signals
    print("\n📋 Recent Signals:")
    for signal in data["signals"][-5:]:
        status_emoji = {"hit": "✅", "stopped": "🛑", "expired": "⏰", "pending": "⏳"}.get(signal["status"], "❓")
        print(f"  {status_emoji} {signal['symbol']} {signal['type']} @ ${signal['entry_price']:.2f}")
        print(f"     Status: {signal['status']} | Strategy: {signal.get('strategy', 'unknown')}")
        if signal['status'] == 'pending' and 'expires_at' in signal:
            expires = datetime.fromisoformat(signal['expires_at'])
            remaining = expires - datetime.now()
            hours = remaining.total_seconds() / 3600
            print(f"     Expires in: {hours:.1f}h")
        elif signal.get('final_pnl_pct'):
            print(f"     PnL: {signal['final_pnl_pct']:+.1f}%")
    
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            check_signals()
            print_stats()
        elif sys.argv[1] == "stats":
            print_stats()
    else:
        print_stats()
