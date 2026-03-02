# Gork Trading Monitors

Automated trading signal monitors for BTC, NEAR, and ZEC.

## Monitors (15 min intervals)

| Monitor | Signal | Win Rate | Script |
|---------|--------|----------|--------|
| ZEC Breakdown | SHORT | 60% (75% w/ filter) | `zec_breakdown_monitor.sh` |
| ZEC MA5/20 | SHORT | 80% | `zec_ma_short_monitor.sh` |
| BTC Reversal | LONG | 94.1% | `btc_reversal_monitor.sh` |
| NEAR Reversal | LONG | 76.7% | `near_reversal_monitor.sh` |
| GA RSI | LONG/SHORT | Varies | `ga_rsi_monitor.sh` |
| Z-Score | LONG/SHORT | Multi-metric | `zscore-monitor.sh` |
| Head & Shoulders | Pattern | TBD | `head_shoulders_monitor.sh` |
| Signal Validator | Tracking | 100% | `signal_validator.sh` |

## Requirements

- Python 3 with: `requests`, `pandas`, `numpy`, `scipy`
- Virtual env at: `/Users/asil/.openclaw/workspace/zscore-env`

## Setup

All monitors run via macOS launchd:

```bash
# Check status
./gork-monitors.sh status

# Reload all
./gork-monitors.sh reload
```

## Key Files

- `signal_validator_v2.py` - Auto-expiring signal tracker
- `head_shoulders_detector.py` - Pattern recognition
- `regime_filter.py` - MA20/MA50 regime detection

## Regime Filter

**IMPORTANT:** ZEC SHORT signals require downtrend (MA20 < MA50).

The `regime_filter.py` module checks this automatically in:
- `zec_breakdown_monitor.sh`
- `zec_ma_short_monitor.sh`

## Signal Accuracy

Tracked in: `/Users/asil/.openclaw/workspace/backtesting/signal_validation_log.json`

Current: 1 signal, 1 hit, 100% win rate

## Logs

Permanent logs at: `/Users/asil/.openclaw/workspace/logs/`
