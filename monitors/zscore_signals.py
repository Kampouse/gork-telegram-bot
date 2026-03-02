#!/usr/bin/env python3
"""
Z-Score Signal Generator for Trading Bot Integration
Returns signals in a format compatible with the trading system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from zscore_heatmap import ZScoreHeatmap
import json


def get_trading_signal(symbol: str = "NEARUSDT", lookback: int = 50) -> dict:
    """
    Get trading signal from Z-Score analysis.
    
    Returns:
        {
            'signal': 'LONG' | 'SHORT' | 'STRONG LONG' | 'STRONG SHORT' | None,
            'strength': 0-10,
            'price': float,
            'zscores': {...},
            'reasons': [...],
            'warnings': [...]
        }
    """
    heatmap = ZScoreHeatmap(symbol=symbol, lookback=lookback)
    metrics = heatmap.get_all_metrics()
    
    if not metrics:
        return {
            'signal': None,
            'strength': 0,
            'error': 'Failed to fetch data'
        }
    
    analysis = heatmap.analyze_signals(metrics)
    
    return {
        'signal': analysis['signal'],
        'strength': analysis['strength'],
        'price': metrics.get('_price'),
        'timestamp': str(metrics.get('_timestamp')),
        'zscores': {k: round(v, 2) for k, v in metrics.items() if not k.startswith('_')},
        'reasons': analysis['reasons'],
        'warnings': analysis['warnings']
    }


def check_signal_conditions(symbol: str, signal_type: str = "SHORT") -> tuple:
    """
    Check if specific signal conditions are met.
    
    Args:
        symbol: Trading pair (e.g., "NEARUSDT")
        signal_type: "LONG" or "SHORT"
    
    Returns:
        (should_trade: bool, details: dict)
    """
    result = get_trading_signal(symbol)
    
    if result.get('signal') is None:
        return False, result
    
    # Check if signal matches what we're looking for
    if signal_type == "SHORT" and "SHORT" in result['signal']:
        # Additional filters for SHORT
        zscores = result['zscores']
        
        # Require at least Price + CVD extremes
        price_extreme = zscores.get('Price', 0) >= 1.5
        cvd_extreme = zscores.get('CVD', 0) >= 1.5
        
        if price_extreme and cvd_extreme:
            return True, result
        else:
            result['reasons'].append(f"Insufficient extremes: Price={zscores.get('Price')}, CVD={zscores.get('CVD')}")
            return False, result
    
    elif signal_type == "LONG" and "LONG" in result['signal']:
        # Additional filters for LONG
        zscores = result['zscores']
        
        # Require at least Price + CVD extremes
        price_extreme = zscores.get('Price', 0) <= -1.5
        cvd_extreme = zscores.get('CVD', 0) <= -1.5
        
        if price_extreme and cvd_extreme:
            return True, result
        else:
            result['reasons'].append(f"Insufficient extremes: Price={zscores.get('Price')}, CVD={zscores.get('CVD')}")
            return False, result
    
    return False, result


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python3 zscore_signals.py SYMBOL [--check LONG|SHORT]")
        print("Example: python3 zscore_signals.py NEARUSDT --check SHORT")
        sys.exit(1)
    
    symbol = sys.argv[1]
    
    if '--check' in sys.argv:
        idx = sys.argv.index('--check')
        signal_type = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "SHORT"
        
        should_trade, details = check_signal_conditions(symbol, signal_type)
        
        print(json.dumps({
            'symbol': symbol,
            'signal_type': signal_type,
            'should_trade': should_trade,
            'details': details
        }, indent=2))
    else:
        # Just get the signal
        result = get_trading_signal(symbol)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
