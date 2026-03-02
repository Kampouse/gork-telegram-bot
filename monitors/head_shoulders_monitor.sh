#!/bin/bash
# Head & Shoulders Pattern Monitor
# Detects both regular (bearish) and inverse (bullish) patterns
# Scans BTC, NEAR, ZEC for confirmed patterns

cd /Users/asil/.openclaw/workspace
source zscore-env/bin/activate

python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/asil/.openclaw/workspace/backtesting')
from head_shoulders_detector import fetch_candles, detect_head_shoulders, detect_inverse_head_shoulders

SYMBOLS = ["BTCUSDT", "NEARUSDT", "ZECUSDT"]

print("=" * 60)
print("HEAD & SHOULDERS PATTERN MONITOR")
print("=" * 60)

signals_found = []

for symbol in SYMBOLS:
    try:
        df = fetch_candles(symbol)
        price = df.iloc[-1]["close"]
        
        # Check regular H&S (bearish)
        hs = detect_head_shoulders(df)
        if hs and hs['confirmed']:
            print(f"\n🔴 {symbol}: HEAD & SHOULDERS (BEARISH) CONFIRMED")
            print(f"   Price: ${price:.2f}")
            print(f"   Neckline: ${hs['neckline']:.2f}")
            print(f"   Target: ${hs['target']:.2f} ({((hs['target'] - price) / price * 100):.1f}%)")
            signals_found.append({"symbol": symbol, "type": "BEARISH", **hs})
        
        # Check inverse H&S (bullish)
        ihs = detect_inverse_head_shoulders(df)
        if ihs and ihs['confirmed']:
            print(f"\n🟢 {symbol}: INVERSE HEAD & SHOULDERS (BULLISH) CONFIRMED")
            print(f"   Price: ${price:.2f}")
            print(f"   Neckline: ${ihs['neckline']:.2f}")
            print(f"   Target: ${ihs['target']:.2f} ({((ihs['target'] - price) / price * 100):.1f}%)")
            signals_found.append({"symbol": symbol, "type": "BULLISH", **ihs})
            
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")

if not signals_found:
    print("\n✅ No confirmed Head & Shoulders patterns")
    print("   Monitoring BTC, NEAR, ZEC...")
else:
    print(f"\n{'='*60}")
    print(f"⚠️ {len(signals_found)} CONFIRMED PATTERN(S)")
    print(f"{'='*60}")

print("\n" + "=" * 60)
EOF
