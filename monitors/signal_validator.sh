#!/bin/bash
# Signal Validator with Auto-Expiration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source zscore-env/bin/activate
python3 backtesting/signal_validator_v2.py check
