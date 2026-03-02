#!/usr/bin/env python3
"""
Multi-Metric Z-Score Heatmap for Trading Signals
Visualizes statistical extremes across 7 indicators simultaneously.
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# ANSI color codes for terminal heatmap
COLORS = {
    'extreme_high': '\033[48;5;196m',    # Red (Z >= 2.0)
    'high': '\033[48;5;208m',             # Orange (1.0 <= Z < 2.0)
    'neutral': '\033[48;5;240m',          # Gray (-0.5 <= Z < 0.5)
    'low': '\033[48;5;33m',               # Blue (-2.0 < Z <= -1.0)
    'extreme_low': '\033[48;5;129m',      # Purple (Z < -2.0)
    'reset': '\033[0m',
    'white': '\033[97m',
    'bold': '\033[1m'
}

class ZScoreHeatmap:
    def __init__(self, symbol: str = "BTCUSDT", lookback: int = 50):
        self.symbol = symbol
        self.lookback = lookback
        self.metrics = ['Price', 'CVD', 'OI', 'Funding', 'Volume', 'VolDelta', 'OIDelta']
        
    def fetch_klines(self, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
        """Fetch OHLCV data from Binance"""
        url = f"https://fapi.binance.com/fapi/v1/klines"
        params = {
            'symbol': self.symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base', 'quote_volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return None
    
    def fetch_open_interest(self, limit: int = 200) -> pd.DataFrame:
        """Fetch open interest history"""
        # Try historical endpoint first
        url = f"https://fapi.binance.com/fapi/v1/openInterestHist"
        params = {
            'symbol': self.symbol,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['openInterest'] = df['openInterest'].astype(float)
                return df
        except:
            pass
        
        # Fallback: get current OI only (no history)
        url = f"https://fapi.binance.com/fapi/v1/openInterest"
        try:
            response = requests.get(url, params={'symbol': self.symbol}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Return single value as DataFrame
                return pd.DataFrame([{
                    'timestamp': pd.Timestamp.now(),
                    'openInterest': float(data['openInterest'])
                }])
        except Exception as e:
            print(f"Error fetching OI: {e}")
            
        return None
    
    def fetch_funding_rate(self, limit: int = 200) -> pd.DataFrame:
        """Fetch funding rate history"""
        url = f"https://fapi.binance.com/fapi/v1/fundingRate"
        params = {
            'symbol': self.symbol,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['fundingTime'], unit='ms')
            df['fundingRate'] = df['fundingRate'].astype(float)
            
            return df
        except Exception as e:
            print(f"Error fetching funding: {e}")
            return None
    
    def calculate_cvd(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Cumulative Volume Delta"""
        # CVD = cumulative(taker_buy_volume - (total_volume - taker_buy_volume))
        df['vol_delta'] = df['taker_buy_base'] - (df['volume'] - df['taker_buy_base'])
        return df['vol_delta'].cumsum()
    
    def calculate_zscore(self, series: pd.Series, window: int = None) -> float:
        """Calculate Z-Score for the latest value"""
        if window is None:
            window = self.lookback
            
        if len(series) < window:
            return 0.0
            
        recent = series.tail(window)
        mean = recent.mean()
        std = recent.std()
        
        if std == 0 or pd.isna(std):
            return 0.0
            
        current = series.iloc[-1]
        zscore = (current - mean) / std
        
        return zscore
    
    def get_all_metrics(self) -> Dict[str, float]:
        """Fetch all data and calculate Z-Scores"""
        import sys
        print(f"Fetching data for {self.symbol}...", file=sys.stderr)
        
        # Fetch klines
        klines = self.fetch_klines()
        if klines is None:
            return {}
        
        # Fetch OI and funding
        oi_data = self.fetch_open_interest()
        funding_data = self.fetch_funding_rate()
        
        # Calculate CVD
        cvd = self.calculate_cvd(klines)
        
        # Calculate metrics
        metrics = {}
        
        # 1. Price Z-Score
        metrics['Price'] = self.calculate_zscore(klines['close'])
        
        # 2. CVD Z-Score
        metrics['CVD'] = self.calculate_zscore(cvd)
        
        # 3. Open Interest Z-Score
        if oi_data is not None and len(oi_data) > 0:
            metrics['OI'] = self.calculate_zscore(oi_data['openInterest'])
        else:
            metrics['OI'] = 0.0
        
        # 4. Funding Rate Z-Score
        if funding_data is not None and len(funding_data) > 0:
            metrics['Funding'] = self.calculate_zscore(funding_data['fundingRate'] * 100)  # Scale for readability
        else:
            metrics['Funding'] = 0.0
        
        # 5. Volume Z-Score
        metrics['Volume'] = self.calculate_zscore(klines['volume'])
        
        # 6. Volume Delta Z-Score
        metrics['VolDelta'] = self.calculate_zscore(klines['taker_buy_base'] - (klines['volume'] - klines['taker_buy_base']))
        
        # 7. OI Delta Z-Score
        if oi_data is not None and len(oi_data) > 1:
            oi_delta = oi_data['openInterest'].diff()
            metrics['OIDelta'] = self.calculate_zscore(oi_delta.dropna())
        else:
            metrics['OIDelta'] = 0.0
        
        # Store current price for display
        metrics['_price'] = klines['close'].iloc[-1]
        metrics['_timestamp'] = klines['timestamp'].iloc[-1]
        
        return metrics
    
    def get_color(self, zscore: float) -> Tuple[str, str]:
        """Get color code and description for Z-Score"""
        if zscore >= 2.0:
            return COLORS['extreme_high'], '🔴 EXTREME HIGH'
        elif zscore >= 1.0:
            return COLORS['high'], '🟠 HIGH'
        elif zscore >= -0.5 and zscore <= 0.5:
            return COLORS['neutral'], '⚪ NEUTRAL'
        elif zscore <= -2.0:
            return COLORS['extreme_low'], '💜 EXTREME LOW'
        elif zscore < -1.0:
            return COLORS['low'], '🔵 LOW'
        else:
            return COLORS['neutral'], '⚪ NEUTRAL'
    
    def render_heatmap_bar(self, zscore: float, width: int = 30) -> str:
        """Render a single heatmap bar with position marker"""
        # Clamp zscore to display range (-3 to 3)
        display_z = max(-3, min(3, zscore))
        
        # Calculate position (0 to width)
        position = int((display_z + 3) / 6 * width)
        position = max(0, min(width - 1, position))
        
        # Build bar
        color, _ = self.get_color(zscore)
        bar = color + ' ' * width + COLORS['reset']
        
        # Add white line marker
        bar_list = list(bar)
        marker_pos = len(color) + position
        if marker_pos < len(bar_list):
            bar_list[marker_pos] = '|'
        
        return ''.join(bar_list)
    
    def analyze_signals(self, metrics: Dict[str, float]) -> Dict:
        """Analyze metrics for trading signals"""
        signals = {
            'signal': None,
            'strength': 0,
            'reasons': [],
            'warnings': []
        }
        
        # Count extremes
        high_count = sum(1 for k, v in metrics.items() if not k.startswith('_') and v >= 2.0)
        low_count = sum(1 for k, v in metrics.items() if not k.startswith('_') and v <= -2.0)
        
        # Count moderate extremes (>=1.5 or <=-1.5)
        moderate_high = sum(1 for k, v in metrics.items() if not k.startswith('_') and 1.5 <= v < 2.0)
        moderate_low = sum(1 for k, v in metrics.items() if not k.startswith('_') and -2.0 < v <= -1.5)
        
        # SHORT signals
        if high_count >= 3:
            signals['signal'] = 'STRONG SHORT'
            signals['strength'] = high_count + moderate_high
            signals['reasons'].append(f"{high_count} metrics extremely high")
        elif high_count >= 2 and moderate_high >= 1:
            signals['signal'] = 'SHORT'
            signals['strength'] = high_count + moderate_high
            signals['reasons'].append(f"{high_count} extreme + {moderate_high} moderate high")
        
        if metrics.get('Price', 0) >= 2.0 and metrics.get('CVD', 0) >= 2.0:
            if signals['strength'] < 8:
                signals['signal'] = 'STRONG SHORT'
                signals['strength'] = 8
            signals['reasons'].append("Price + CVD both extreme")
        
        if metrics.get('Funding', 0) >= 2.0:
            signals['reasons'].append("Funding highly positive")
        
        # LONG signals
        if low_count >= 3:
            signals['signal'] = 'STRONG LONG'
            signals['strength'] = low_count + moderate_low
            signals['reasons'].append(f"{low_count} metrics extremely low")
        elif low_count >= 2 and moderate_low >= 1:
            signals['signal'] = 'LONG'
            signals['strength'] = low_count + moderate_low
            signals['reasons'].append(f"{low_count} extreme + {moderate_low} moderate low")
        
        if metrics.get('Price', 0) <= -2.0 and metrics.get('CVD', 0) <= -2.0:
            if signals['strength'] < 8:
                signals['signal'] = 'STRONG LONG'
                signals['strength'] = 8
            signals['reasons'].append("Price + CVD both extreme")
        
        if metrics.get('Funding', 0) <= -2.0:
            signals['reasons'].append("Funding highly negative")
        
        # Divergences
        if abs(metrics.get('Price', 0)) > 1.5 and abs(metrics.get('CVD', 0)) < 0.5:
            signals['warnings'].append("Price/CVD divergence - weak move")
        
        if metrics.get('Price', 0) > 1.0 and metrics.get('OIDelta', 0) < -1.0:
            signals['warnings'].append("OI dropping while price rising - exhausted trend")
        
        return signals
    
    def display(self, metrics: Dict[str, float]):
        """Display the heatmap"""
        print("\n" + "=" * 60)
        print(f"  {COLORS['bold']}Z-SCORE HEATMAP{COLORS['reset']} | {self.symbol}")
        print(f"  Price: ${metrics.get('_price', 0):,.2f} | {metrics.get('_timestamp', 'N/A')}")
        print("=" * 60)
        print()
        
        # Header
        print(f"  {'Metric':<12} {'Z-Score':>8}  {'Heatmap':<35} {'Status'}")
        print("  " + "-" * 70)
        
        # Display each metric
        for metric in self.metrics:
            if metric in metrics:
                zscore = metrics[metric]
                color, desc = self.get_color(zscore)
                bar = self.render_heatmap_bar(zscore)
                
                print(f"  {metric:<12} {zscore:>8.2f}  {bar} {desc}")
        
        print()
        print("  " + "-" * 70)
        
        # Scale legend
        print(f"\n  {COLORS['extreme_high']}  {COLORS['reset']} Z≥2.0  ", end='')
        print(f"{COLORS['high']}  {COLORS['reset']} 1.0≤Z<2.0  ", end='')
        print(f"{COLORS['neutral']}  {COLORS['reset']} -0.5<Z<0.5  ", end='')
        print(f"{COLORS['low']}  {COLORS['reset']} -2.0<Z≤-1.0  ", end='')
        print(f"{COLORS['extreme_low']}  {COLORS['reset']} Z<-2.0")
        print()
        
        # Signal analysis
        signals = self.analyze_signals(metrics)
        
        if signals['signal']:
            signal_color = COLORS['extreme_high'] if 'SHORT' in signals['signal'] else COLORS['extreme_low']
            print(f"  {COLORS['bold']}SIGNAL: {signal_color}{signals['signal']}{COLORS['reset']} (Strength: {signals['strength']}/10)")
            
            if signals['reasons']:
                print(f"\n  {COLORS['bold']}Reasons:{COLORS['reset']}")
                for reason in signals['reasons']:
                    print(f"    • {reason}")
            
            if signals['warnings']:
                print(f"\n  {COLORS['bold']}Warnings:{COLORS['reset']}")
                for warning in signals['warnings']:
                    print(f"    ⚠️  {warning}")
        else:
            print(f"  {COLORS['bold']}SIGNAL: NONE{COLORS['reset']} (No extreme readings)")
        
        print("\n" + "=" * 60 + "\n")
    
    def run(self):
        """Main execution"""
        metrics = self.get_all_metrics()
        
        if not metrics:
            print("Failed to fetch metrics")
            return None
        
        self.display(metrics)
        
        # Return for programmatic use
        return {
            'symbol': self.symbol,
            'timestamp': metrics.get('_timestamp'),
            'price': metrics.get('_price'),
            'zscores': {k: v for k, v in metrics.items() if not k.startswith('_')},
            'signals': self.analyze_signals(metrics)
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Metric Z-Score Heatmap')
    parser.add_argument('symbol', nargs='?', default='BTCUSDT', help='Trading symbol (e.g., BTCUSDT, NEARUSDT)')
    parser.add_argument('--lookback', type=int, default=50, help='Lookback period for Z-Score calculation')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    heatmap = ZScoreHeatmap(symbol=args.symbol, lookback=args.lookback)
    result = heatmap.run()
    
    if args.json and result:
        print(json.dumps(result, indent=2, default=str))
    
    return result


if __name__ == "__main__":
    main()
