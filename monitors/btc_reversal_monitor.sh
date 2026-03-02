#!/bin/bash
# BTC Reversal LONG Monitor - VALIDATED STRATEGY
# RSI Oversold Bounce: RSI was < 30, now recovering
#
# Backtest results (out-of-sample):
# - Win Rate: 94.1%
# - R/R: 1.14
# - Expectancy: 3.62%
# - Total PnL: +61.5% (17 trades)
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

def check_btc_reversal():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "1h", "limit": 50}
    data = requests.get(url, params=params, timeout=30).json()
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    
    # Calculate RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    
    current_rsi = df.iloc[-1]["rsi"]
    prev_rsi = df.iloc[-2]["rsi"]
    current_price = df.iloc[-1]["close"]
    
    # Signal: RSI was oversold (<30), now recovering (rising)
    was_oversold = prev_rsi < 30
    is_recovering = current_rsi > prev_rsi
    
    if was_oversold and is_recovering:
        print(f"🚨 BTC REVERSAL SIGNAL - LONG")
        print(f"")
        print(f"Price: ${current_price:,.2f}")
        print(f"RSI: {current_rsi:.1f} (was {prev_rsi:.1f})")
        print(f"")
        print(f"Strategy: LONG (RSI Bounce)")
        print(f"Hold: 72 hours")
        print(f"Win Rate: 94.1%")
        print(f"Expectancy: 3.62%")
        print(f"Validated: Out-of-sample +61.5%")
        
        # AUTO-REGISTER SIGNAL
        target = current_price * 1.05  # +5%
        stop = current_price * 0.97  # -3%
        
        add_signal(
            symbol="BTCUSDT",
            signal_type="LONG",
            entry_price=current_price,
            target_price=target,
            stop_price=stop,
            strategy="reversal",
            win_rate=94.1,
            leverage=3,
            hold_hours=72
        )
    else:
        # Show status
        oversold_status = "WAS OVERSOLD" if prev_rsi < 30 else "Not oversold"
        recovery_status = "RECOVERING" if current_rsi > prev_rsi else "Declining"
        
        print(f"BTC: ${current_price:,.2f} | RSI: {current_rsi:.1f}")
        print(f"Previous RSI: {prev_rsi:.1f} ({oversold_status})")
        print(f"Direction: {recovery_status}")
        
        if prev_rsi < 30:
            print(f"⚠️ Was oversold - watching for recovery")
        elif current_rsi < 35:
            print(f"Near oversold - watching for RSI < 30")

check_btc_reversal()
EOF
