#!/bin/bash
# ZEC Breakdown Monitor - VALIDATED STRATEGY
# Alerts on breakdown below 20-period support for SHORT entry
#
# Backtest results (regime-neutral 1000d):
# - Win Rate: 60% (all regimes)
# - Win Rate: 75% with regime filter (downtrend only)
# - Hold: 24 hours
# - Costs: 0.4% per trade included

cd /Users/asil/.openclaw/workspace
source zscore-env/bin/activate

# Fetch ZEC data and detect breakdown
python3 << 'EOF'
import requests
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/Users/asil/.openclaw/workspace/backtesting')
from regime_filter import check_regime
from signal_validator_v2 import add_signal

def check_zec_breakdown():
    # Check regime FIRST
    regime = check_regime("ZECUSDT")
    if not regime.get("downtrend", False):
        print(f"⚠️ REGIME FILTER: ZEC in UPTREND")
        print(f"   Skipping SHORT signal (requires MA20 < MA50)")
        print(f"   Current: MA20 ${regime.get('ma20', 0):.2f} vs MA50 ${regime.get('ma50', 0):.2f}")
        return
    
    # Fetch 50 candles
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "ZECUSDT", "interval": "1h", "limit": 50}
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    
    df["close"] = df["close"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    
    # Calculate support (20-period low)
    df["support_20"] = df["low"].rolling(window=20, min_periods=1).min()
    
    # Current values
    current_close = df.iloc[-1]["close"]
    prev_close = df.iloc[-2]["close"]
    prev_support = df.iloc[-2]["support_20"]
    
    # Detect breakdown: close < previous support, but previous close was >= support
    breakdown = (current_close < prev_support) and (prev_close >= df.iloc[-3]["support_20"])
    
    # Also check RSI for context
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    current_rsi = df.iloc[-1]["rsi"]
    
    if breakdown:
        print(f"🚨 ZEC BREAKDOWN SIGNAL")
        print(f"Price: ${current_close:.2f}")
        print(f"Support Broken: ${prev_support:.2f}")
        print(f"RSI: {current_rsi:.1f}")
        print(f"")
        print(f"Strategy: SHORT")
        print(f"Hold: 24 hours")
        print(f"Expected Win Rate: 60% (75% with regime filter)")
        print(f"Validated: Out-of-sample test +4%")
        
        # AUTO-REGISTER SIGNAL
        target = current_close * 0.94  # -6%
        stop = current_close * 1.04  # +4%
        
        add_signal(
            symbol="ZECUSDT",
            signal_type="SHORT",
            entry_price=current_close,
            target_price=target,
            stop_price=stop,
            strategy="breakdown",
            win_rate=60,
            leverage=3,
            hold_hours=24
        )
    else:
        # Show status
        distance = ((current_close - prev_support) / prev_support) * 100
        print(f"ZEC: ${current_close:.2f} | Support: ${prev_support:.2f} | Distance: +{distance:.1f}% | RSI: {current_rsi:.1f}")
        print(f"No breakdown signal")

check_zec_breakdown()
EOF
