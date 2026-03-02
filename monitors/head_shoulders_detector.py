#!/usr/bin/env python3
"""
Head & Shoulders Pattern Detector
Detects both regular (bearish) and inverse (bullish) patterns
"""

import requests
import pandas as pd
import numpy as np
from scipy.signal import find_peaks, argrelextrema

def fetch_candles(symbol: str, interval: str = "1h", limit: int = 200):
    """Fetch price data from Binance"""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = requests.get(url, params=params, timeout=30).json()
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    
    return df


def find_swings(df: pd.DataFrame, order: int = 5):
    """Find local highs and lows using argrelextrema"""
    # Find local highs (peaks)
    highs_idx = argrelextrema(df["high"].values, np.greater, order=order)[0]
    
    # Find local lows (troughs)
    lows_idx = argrelextrema(df["low"].values, np.less, order=order)[0]
    
    return highs_idx, lows_idx


def detect_head_shoulders(df: pd.DataFrame, tolerance: float = 0.03):
    """
    Detect Head & Shoulders pattern (bearish reversal)
    
    Pattern rules:
    1. Left shoulder peak
    2. Higher head peak
    3. Right shoulder peak (similar height to left shoulder)
    4. Neckline connects the two troughs between shoulders and head
    5. Price breaks below neckline = bearish signal
    
    Returns: dict with pattern info or None
    """
    highs_idx, lows_idx = find_swings(df, order=5)
    
    if len(highs_idx) < 3 or len(lows_idx) < 2:
        return None
    
    # Get recent highs
    recent_highs = highs_idx[-5:] if len(highs_idx) >= 5 else highs_idx
    recent_lows = lows_idx[-5:] if len(lows_idx) >= 5 else lows_idx
    
    # Look for 3 peaks pattern
    for i in range(len(recent_highs) - 2):
        left_idx = recent_highs[i]
        head_idx = recent_highs[i + 1]
        right_idx = recent_highs[i + 2]
        
        left_high = df.iloc[left_idx]["high"]
        head_high = df.iloc[head_idx]["high"]
        right_high = df.iloc[right_idx]["high"]
        
        # Check if head is higher than both shoulders
        if not (head_high > left_high and head_high > right_high):
            continue
        
        # Check if shoulders are roughly equal (within tolerance)
        shoulder_diff = abs(left_high - right_high) / left_high
        if shoulder_diff > tolerance:
            continue
        
        # Find neckline (lows between peaks)
        neckline_lows = df.iloc[head_idx:right_idx + 1]["low"]
        neckline_low = neckline_lows.min()
        neckline_idx = df.iloc[head_idx:right_idx + 1]["low"].idxmin()
        
        # Also find the low between left shoulder and head
        left_neckline_low = df.iloc[left_idx:head_idx + 1]["low"].min()
        
        # Neckline should be roughly horizontal
        neckline = (neckline_low + left_neckline_low) / 2
        
        # Calculate pattern height (head to neckline)
        pattern_height = head_high - neckline
        pattern_pct = (pattern_height / neckline) * 100
        
        # Check if price has broken neckline (confirmation)
        current_price = df.iloc[-1]["close"]
        confirmed = current_price < neckline
        
        # Calculate target (pattern height below neckline)
        target = neckline - pattern_height
        
        return {
            "pattern": "HEAD_AND_SHOULDERS",
            "signal": "BEARISH" if confirmed else "FORMING",
            "left_shoulder": left_high,
            "head": head_high,
            "right_shoulder": right_high,
            "neckline": neckline,
            "current_price": current_price,
            "target": target,
            "pattern_height_pct": pattern_pct,
            "confirmed": confirmed,
            "left_idx": int(left_idx),
            "head_idx": int(head_idx),
            "right_idx": int(right_idx)
        }
    
    return None


def detect_inverse_head_shoulders(df: pd.DataFrame, tolerance: float = 0.03):
    """
    Detect Inverse Head & Shoulders pattern (bullish reversal)
    
    Pattern rules:
    1. Left shoulder trough
    2. Lower head trough
    3. Right shoulder trough (similar depth to left shoulder)
    4. Neckline connects the two peaks between shoulders and head
    5. Price breaks above neckline = bullish signal
    
    Returns: dict with pattern info or None
    """
    highs_idx, lows_idx = find_swings(df, order=5)
    
    if len(lows_idx) < 3 or len(highs_idx) < 2:
        return None
    
    # Get recent lows
    recent_lows = lows_idx[-5:] if len(lows_idx) >= 5 else lows_idx
    recent_highs = highs_idx[-5:] if len(highs_idx) >= 5 else highs_idx
    
    # Look for 3 troughs pattern
    for i in range(len(recent_lows) - 2):
        left_idx = recent_lows[i]
        head_idx = recent_lows[i + 1]
        right_idx = recent_lows[i + 2]
        
        left_low = df.iloc[left_idx]["low"]
        head_low = df.iloc[head_idx]["low"]
        right_low = df.iloc[right_idx]["low"]
        
        # Check if head is lower than both shoulders
        if not (head_low < left_low and head_low < right_low):
            continue
        
        # Check if shoulders are roughly equal (within tolerance)
        shoulder_diff = abs(left_low - right_low) / left_low
        if shoulder_diff > tolerance:
            continue
        
        # Find neckline (highs between troughs)
        neckline_highs = df.iloc[head_idx:right_idx + 1]["high"]
        neckline_high = neckline_highs.max()
        
        # Also find the high between left shoulder and head
        left_neckline_high = df.iloc[left_idx:head_idx + 1]["high"].max()
        
        # Neckline should be roughly horizontal
        neckline = (neckline_high + left_neckline_high) / 2
        
        # Calculate pattern height (neckline to head)
        pattern_height = neckline - head_low
        pattern_pct = (pattern_height / neckline) * 100
        
        # Check if price has broken neckline (confirmation)
        current_price = df.iloc[-1]["close"]
        confirmed = current_price > neckline
        
        # Calculate target (pattern height above neckline)
        target = neckline + pattern_height
        
        return {
            "pattern": "INVERSE_HEAD_AND_SHOULDERS",
            "signal": "BULLISH" if confirmed else "FORMING",
            "left_shoulder": left_low,
            "head": head_low,
            "right_shoulder": right_low,
            "neckline": neckline,
            "current_price": current_price,
            "target": target,
            "pattern_height_pct": pattern_pct,
            "confirmed": confirmed,
            "left_idx": int(left_idx),
            "head_idx": int(head_idx),
            "right_idx": int(right_idx)
        }
    
    return None


def scan_patterns(symbols: list = None):
    """Scan multiple symbols for H&S patterns"""
    if symbols is None:
        symbols = ["BTCUSDT", "NEARUSDT", "ZECUSDT", "ETHUSDT", "SOLUSDT"]
    
    results = []
    
    for symbol in symbols:
        try:
            df = fetch_candles(symbol)
            
            # Check regular H&S (bearish)
            hs = detect_head_shoulders(df)
            if hs:
                results.append({**hs, "symbol": symbol, "type": "bearish"})
            
            # Check inverse H&S (bullish)
            ihs = detect_inverse_head_shoulders(df)
            if ihs:
                results.append({**ihs, "symbol": symbol, "type": "bullish"})
                
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
    
    return results


if __name__ == "__main__":
    import sys
    
    symbol = sys.argv[1] if len(sys.argv) > 1 else "ZECUSDT"
    
    print(f"Scanning {symbol} for Head & Shoulders patterns...")
    print("=" * 60)
    
    df = fetch_candles(symbol)
    
    # Check regular H&S
    hs = detect_head_shoulders(df)
    if hs:
        print(f"\n🔴 HEAD & SHOULDERS (Bearish)")
        print(f"   Signal: {hs['signal']}")
        print(f"   Left Shoulder: ${hs['left_shoulder']:.2f}")
        print(f"   Head: ${hs['head']:.2f}")
        print(f"   Right Shoulder: ${hs['right_shoulder']:.2f}")
        print(f"   Neckline: ${hs['neckline']:.2f}")
        print(f"   Current: ${hs['current_price']:.2f}")
        print(f"   Target: ${hs['target']:.2f}")
        print(f"   Pattern Height: {hs['pattern_height_pct']:.1f}%")
        print(f"   Confirmed: {'✅' if hs['confirmed'] else '⏳'}")
    
    # Check inverse H&S
    ihs = detect_inverse_head_shoulders(df)
    if ihs:
        print(f"\n🟢 INVERSE HEAD & SHOULDERS (Bullish)")
        print(f"   Signal: {ihs['signal']}")
        print(f"   Left Shoulder: ${ihs['left_shoulder']:.2f}")
        print(f"   Head: ${ihs['head']:.2f}")
        print(f"   Right Shoulder: ${ihs['right_shoulder']:.2f}")
        print(f"   Neckline: ${ihs['neckline']:.2f}")
        print(f"   Current: ${ihs['current_price']:.2f}")
        print(f"   Target: ${ihs['target']:.2f}")
        print(f"   Pattern Height: {ihs['pattern_height_pct']:.1f}%")
        print(f"   Confirmed: {'✅' if ihs['confirmed'] else '⏳'}")
    
    if not hs and not ihs:
        print("\n⚪ No Head & Shoulders patterns detected")
    
    print("\n" + "=" * 60)
