#!/bin/bash
# Signal Validator with Auto-Expiration
cd /Users/asil/.openclaw/workspace
source zscore-env/bin/activate
python3 backtesting/signal_validator_v2.py check
