#!/usr/bin/env python3
"""
Regime Filter Module
Checks if asset is in downtrend (MA50 < MA200) before SHORT signals
"""

import requests

def check_regime(symbol: str) -> dict:
    """
    Check if asset is in downtrend for SHORT signals
    Returns: {"downtrend": bool, "ma20": float, "ma50": float, "price": float}
    
    Uses faster regime filter (MA20 vs MA50) instead of slow MA50/MA200
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1d", "limit": 100}
    data = requests.get(url, params=params, timeout=30).json()

    closes = [float(c[4]) for c in data]

    if len(closes) < 50:
        return {"downtrend": False, "error": "Insufficient data"}

    # Calculate MAs
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    current_price = closes[-1]

    # Downtrend = price below MA20 AND MA20 below MA50
    downtrend = current_price < ma20 and ma20 < ma50

    return {
        "downtrend": downtrend,
        "ma20": ma20,
        "ma50": ma50,
        "price": current_price,
        "regime": "DOWNTREND" if downtrend else "UPTREND"
    }


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "ZECUSDT"

    result = check_regime(symbol)

    print(f"{symbol}:")
    print(f"  Price: ${result.get('price', 0):.2f}")
    print(f"  MA20: ${result.get('ma20', 0):.2f}")
    print(f"  MA50: ${result.get('ma50', 0):.2f}")
    print(f"  Regime: {result.get('regime', 'unknown')}")
    print(f"  Downtrend: {result.get('downtrend', False)}")
