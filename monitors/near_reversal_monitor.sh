#!/bin/bash
# NEAR Reversal LONG Monitor - VALIDATED STRATEGY
# Support Bounce: Price touches 20-period support then closes higher
#
# Backtest results (out-of-sample):
# - Win Rate: 76.7%
# - R/R: 1.63
# - Expectancy: 5.16%
# - Total PnL: +443.7% (86 trades)
# - Hold: 72 hours

cd /Users/asil/.openclaw/workspace
source zscore-env/bin/activate

python3 << 'EOF'
import requests
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/Users/asil/.openclaw/workspace/backtesting')
from signal_validator_v2 import add_signal

def check_near_reversal():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "NEARUSDT", "interval": "1h", "limit": 50}
    data = requests.get(url, params=params, timeout=30).json()
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["low"] = df["low"].astype(float)
    
    # Calculate 20-period support
    df["support_20"] = df["low"].rolling(window=20, min_periods=1).min()
    
    current_price = df.iloc[-1]["close"]
    current_low = df.iloc[-1]["low"]
    current_support = df.iloc[-2]["support_20"]
    
    # Signal: touched support (within 1%), closed higher
    touched_support = current_low <= current_support * 1.01
    closed_higher = current_price > current_low
    support_bounce = touched_support and closed_higher
    
    # RSI for context
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    current_rsi = df.iloc[-1]["rsi"]
    
    if support_bounce:
        print(f"🚨 NEAR REVERSAL SIGNAL - LONG")
        print(f"")
        print(f"Price: ${current_price:.4f}")
        print(f"Support: ${current_support:.4f}")
        print(f"Low: ${current_low:.4f} (touched support)")
        print(f"RSI: {current_rsi:.1f}")
        print(f"")
        print(f"Strategy: LONG (Support Bounce)")
        print(f"Hold: 72 hours")
        print(f"Win Rate: 76.7%")
        print(f"Expectancy: 5.16%")
        print(f"Validated: Out-of-sample +443.7%")
        
        # AUTO-REGISTER SIGNAL
        target = current_price * 1.06  # +6%
        stop = current_support * 0.97  # -3% below support
        
        add_signal(
            symbol="NEARUSDT",
            signal_type="LONG",
            entry_price=current_price,
            target_price=target,
            stop_price=stop,
            strategy="reversal",
            win_rate=76.7,
            leverage=2,
            hold_hours=72
        )
    else:
        distance = ((current_price - current_support) / current_support) * 100
        near_support = distance < 5
        
        print(f"NEAR: ${current_price:.4f} | Support: ${current_support:.4f}")
        print(f"Distance: +{distance:.1f}% | RSI: {current_rsi:.1f}")
        
        if near_support:
            print(f"⚠️ Near support - watching for bounce")
        else:
            print(f"Waiting for price to approach support")

check_near_reversal()
EOF
