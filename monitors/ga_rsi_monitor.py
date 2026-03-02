#!/usr/bin/env python3
import os
"""
GA-Optimized RSI Signal Monitor
Uses Feb 27, 2026 optimized parameters (100% WR for BTC/MSTR)
Alerts via Telegram when signals detected
"""

import json
import requests
import sys
from datetime import datetime

# ============================================
# GA-OPTIMIZED PARAMETERS (Feb 27, 2026)
# ============================================

GA_PARAMS = {
    'BTC': {
        'rsi_period': 8,
        'rsi_long': 30,
        'rsi_short': 79,
        'leverage': 3,
        'win_rate': 100.0,
    },
    'PLTR': {
        'rsi_period': 9,
        'rsi_long': 26,
        'rsi_short': 62,
        'leverage': 3,
        'win_rate': 92.9,
    },
    'MSTR': {
        'rsi_period': 10,
        'rsi_long': 38,
        'rsi_short': 66,
        'leverage': 3,
        'win_rate': 100.0,
    },
    'NEAR': {
        'rsi_period': 26,
        'rsi_long': 31,
        'rsi_short': 80,
        'leverage': 3,
        'win_rate': 100.0,
    },
    'ZEC': {
        'rsi_period': 10,
        'rsi_long': 38,
        'rsi_short': 76,
        'leverage': 3,
        'win_rate': 83.3,
    },
}

# Symbols to monitor (crypto only for now)
MONITOR = ['BTC', 'NEAR', 'ZEC']

# Telegram config
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ============================================
# FUNCTIONS
# ============================================

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bb(prices, period=20, std_dev=2.0):
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return None, None, None

    sma = sum(prices[-period:]) / period
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std = variance ** 0.5

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    return upper, lower, sma

def fetch_candles(symbol):
    """Fetch hourly candles from Binance"""
    # Map symbol to Binance pair
    pair_map = {
        'BTC': 'BTCUSDT',
        'NEAR': 'NEARUSDT',
        'ZEC': 'ZECUSDT',
        'PLTR': None,  # Not on Binance
        'MSTR': None,  # Not on Binance
    }

    pair = pair_map.get(symbol)
    if not pair:
        return None

    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&limit=100"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def send_telegram(message):
    """Send Telegram alert"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# ============================================
# MAIN
# ============================================

def main():
    signals = []

    print(f"\n{'='*60}")
    print(f"GA-OPTIMIZED RSI MONITOR — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    for symbol in MONITOR:
        params = GA_PARAMS[symbol]

        # Fetch candles
        prices = fetch_candles(symbol)
        if not prices:
            print(f"{symbol}: Failed to fetch data")
            continue

        current_price = prices[-1]

        # Calculate indicators
        rsi = calculate_rsi(prices, params['rsi_period'])
        bb_upper, bb_lower, bb_middle = calculate_bb(prices)

        if rsi is None or bb_upper is None:
            print(f"{symbol}: Insufficient data")
            continue

        print(f"\n{symbol}: ${current_price:,.2f}")
        print(f"  RSI({params['rsi_period']}): {rsi:.1f} (LONG <{params['rsi_long']}, SHORT >{params['rsi_short']})")
        print(f"  BB: ${bb_lower:,.2f} - ${bb_upper:,.2f}")

        # Check signals
        long_signal = rsi < params['rsi_long'] and current_price < bb_lower
        short_signal = rsi > params['rsi_short'] and current_price > bb_upper

        if long_signal:
            signal_info = {
                'symbol': symbol,
                'type': 'LONG',
                'price': current_price,
                'rsi': rsi,
                'target': bb_middle,
                'leverage': params['leverage'],
                'win_rate': params['win_rate'],
            }
            signals.append(signal_info)
            print(f"  ✅ LONG SIGNAL!")

        elif short_signal:
            signal_info = {
                'symbol': symbol,
                'type': 'SHORT',
                'price': current_price,
                'rsi': rsi,
                'target': bb_middle,
                'leverage': params['leverage'],
                'win_rate': params['win_rate'],
            }
            signals.append(signal_info)
            print(f"  ✅ SHORT SIGNAL!")
        else:
            print(f"  ⏸️ No signal")

    # Send alerts
    if signals:
        msg_lines = [f"🚨 *GA-OPTIMIZED SIGNALS* ({datetime.now().strftime('%H:%M')})\n"]

        for sig in signals:
            pnl_pct = abs(sig['target'] - sig['price']) / sig['price'] * 100 * sig['leverage']
            msg_lines.append(f"\n*{sig['type']} {sig['symbol']}*")
            msg_lines.append(f"Price: ${sig['price']:,.2f}")
            msg_lines.append(f"RSI: {sig['rsi']:.1f}")
            msg_lines.append(f"Target: ${sig['target']:,.2f}")
            msg_lines.append(f"Expected: +{pnl_pct:.1f}% @ {sig['leverage']}x")
            msg_lines.append(f"Win Rate: {sig['win_rate']:.1f}%")

        msg_lines.append(f"\n_Conditions: RSI + BB confirmation_")

        send_telegram('\n'.join(msg_lines))
        print(f"\n📤 Alert sent to Telegram")

    # Save status
    status = {
        'timestamp': datetime.now().isoformat(),
        'signals': signals,
        'checked': MONITOR,
    }

    with open('/Users/asil/.openclaw/workspace/backtesting/ga_rsi_status.json', 'w') as f:
        json.dump(status, f, indent=2)

    # Also log signals to validation log for tracking
    if signals:
        log_file = '/Users/asil/.openclaw/workspace/backtesting/signal_validation_log.json'
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        except:
            log_data = {'signals': [], 'stats': {'total': 0, 'correct': 0, 'pending': 0}}

        for sig in signals:
            # Calculate stop loss (5% from entry)
            stop_pct = 0.05
            if sig['type'] == 'LONG':
                stop_loss = sig['price'] * (1 - stop_pct)
            else:
                stop_loss = sig['price'] * (1 + stop_pct)
            
            entry = {
                'id': f"{sig['symbol']}_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'symbol': sig['symbol'],
                'type': sig['type'],
                'entry_price': sig['price'],
                'entry_rsi': sig['rsi'],
                'target_price': sig['target'],
                'stop_loss': stop_loss,
                'outcomes': {},
                'status': 'pending',
                'source': 'ga_rsi_monitor',
                'win_rate': sig['win_rate'],
                'leverage': sig['leverage'],
            }
            log_data['signals'].append(entry)
            log_data['stats']['pending'] += 1
            log_data['stats']['total'] += 1
            print(f"📝 Logged to validation: {sig['type']} {sig['symbol']}")

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

    print(f"\n✅ Monitor complete — {len(signals)} signals")

if __name__ == '__main__':
    main()
