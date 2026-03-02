# Gork Trading Monitors

Automated trading signal monitors for cryptocurrency markets. Runs via macOS launchd.

## Active Monitors

| Monitor | Asset | Strategy | Interval | Win Rate |
|---------|-------|----------|----------|----------|
| ga_rsi_monitor | BTC, NEAR, ZEC | GA-optimized RSI mean reversion | 15 min | 76-94% |
| btc_reversal_monitor | BTC | RSI oversold bounce | 15 min | 94.1% |
| near_reversal_monitor | NEAR | Support bounce | 15 min | 76.7% |
| zec_breakdown_monitor | ZEC | Support breakdown SHORT | 15 min | 71.4% |
| zec_ma_short_monitor | ZEC | MA5/MA20 death cross SHORT | 15 min | 80% |
| zscore_monitor | BTC, NEAR, ZEC | Multi-metric Z-Score heatmap | 15 min | 61.9% |
| head_shoulders_monitor | ZEC | Head & Shoulders pattern | 15 min | Experimental |
| signal_validator | All | Track signal accuracy | 15 min | N/A |

## Strategy Details

### GA-Optimized RSI (Mean Reversion)
- **LONG:** RSI < threshold (asset-specific)
- **SHORT:** RSI > threshold (asset-specific)
- Thresholds optimized via genetic algorithm on 1000-day backtest
- BTC: RSI(8) < 30 = LONG, RSI(8) > 79 = SHORT
- NEAR: RSI(26) < 31 = LONG, RSI(26) > 80 = SHORT
- ZEC: RSI(10) < 38 = LONG, RSI(10) > 76 = SHORT

### BTC Reversal (LONG)
- Entry: RSI was oversold (<30), now recovering
- Hold: 72 hours
- Backtest: 94.1% win rate, +61.5% total PnL

### NEAR Support Bounce (LONG)
- Entry: Price touches 20-period support, closes higher
- Hold: 72 hours
- Backtest: 76.7% win rate, +443.7% total PnL

### ZEC MA5/MA20 Death Cross (SHORT)
- Entry: MA5 crosses below MA20
- Hold: 72 hours
- Backtest: 80% win rate, 7.77 R/R
- **Works across all market regimes**

### ZEC Breakdown (SHORT)
- Entry: Price breaks below 20-period support
- Hold: 24 hours
- **Regime filter:** Only trade when MA20 < MA50 (downtrend)

### Z-Score Heatmap
- Multi-metric analysis: Price, CVD, OI, Funding, Volume
- Signal strength: 0-10 based on extreme Z-Scores (<-2 or >2)
- Best for BTC (61.9% WR), marginal for ZEC, avoid for NEAR

## Requirements

- Python 3.x with: requests, pandas, numpy, scipy
- Environment variables:
  - `TELEGRAM_BOT_TOKEN` - Bot token for alerts
  - `TELEGRAM_CHAT_ID` - Chat ID to send alerts to
- Binance API (public endpoints, no key needed)

## Manual Testing

```bash
# Run individual monitors
./ga_rsi_monitor.sh
./zec_ma_short_monitor.sh

# Check all monitor status
./gork-monitors.sh status
```

## Signal Output Format

When a signal is triggered, monitors send alerts via Telegram:

```
🚨 ZEC MA5/20 SHORT SIGNAL
Price: $219.42
MA5: $215.89 | MA20: $219.13
Cross: MA5 below MA20 by 1.5%
Target: 72h hold
Win Rate: 80%
```

## Signal Validation

The `signal_validator` tracks all triggered signals and checks outcomes:
- Records entry price and time
- Checks price after hold period (24-72h depending on strategy)
- Calculates win rate and P&L

## Regime Filters

Some strategies only work in specific market conditions:
- **ZEC SHORT strategies:** Require downtrend (MA20 < MA50 or MA50 < MA200)
- **Mean reversion:** Works across regimes but thresholds vary

## License

MIT
