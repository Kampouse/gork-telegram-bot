#!/bin/bash
# GA-Optimized RSI Monitor
# Checks BTC, NEAR, ZEC using Feb 27, 2026 optimized parameters

cd /Users/asil/.openclaw/workspace
source zscore-env/bin/activate
python3 backtesting/ga_rsi_monitor.py
