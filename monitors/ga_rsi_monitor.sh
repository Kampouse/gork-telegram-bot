#!/bin/bash
# GA-Optimized RSI Monitor
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Checks BTC, NEAR, ZEC using Feb 27, 2026 optimized parameters

cd "$SCRIPT_DIR"
source zscore-env/bin/activate
python3 backtesting/ga_rsi_monitor.py
