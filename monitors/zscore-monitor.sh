#!/bin/bash
# Multi-symbol Z-Score monitor
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Checks BTC, NEAR, ZEC and alerts on strong signals

cd "$SCRIPT_DIR"

# Use env var for venv path, or fallback to relative path
ZSCORE_ENV="${ZSCORE_ENV:-$SCRIPT_DIR/../zscore-env}"
if [ -d "$ZSCORE_ENV" ]; then
  source "$ZSCORE_ENV/bin/activate"
fi

# Telegram bot token
BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

SYMBOLS="BTC NEAR ZEC"
ALERT_STRENGTH=6  # Alert on strength >= 6

for SYMBOL in $SYMBOLS; do
    SIGNAL=$(python3 zscore_signals.py "${SYMBOL}USDT" 2>/dev/null)

    if [ -z "$SIGNAL" ]; then
        continue
    fi

    # Check for error
    ERROR=$(echo "$SIGNAL" | jq -r '.error // empty' 2>/dev/null)
    if [ -n "$ERROR" ]; then
        continue
    fi

    SIGNAL_TYPE=$(echo "$SIGNAL" | jq -r '.signal // empty')
    STRENGTH=$(echo "$SIGNAL" | jq -r '.strength')

    # Alert on strong signals
    if [ -n "$SIGNAL_TYPE" ] && [ "$STRENGTH" -ge $ALERT_STRENGTH ]; then
        PRICE=$(echo "$SIGNAL" | jq -r '.price')

        # Build alert message
        ALERT="🚨 Z-SCORE ALERT: ${SYMBOL}USDT

"
        ALERT+="Signal: $SIGNAL_TYPE (Strength: $STRENGTH/10)
"
        ALERT+="Price: \$$PRICE

"
        ALERT+="Z-Scores:
"

        # Add key metrics
        for metric in Price CVD Funding; do
            value=$(echo "$SIGNAL" | jq -r ".zscores.$metric")

            # Emoji based on value
            if (( $(echo "$value >= 2.0" | bc -l 2>/dev/null || echo 0) )); then
                EMOJI="🔴"
            elif (( $(echo "$value >= 1.0" | bc -l 2>/dev/null || echo 0) )); then
                EMOJI="🟠"
            elif (( $(echo "$value <= -2.0" | bc -l 2>/dev/null || echo 0) )); then
                EMOJI="💜"
            elif (( $(echo "$value <= -1.0" | bc -l 2>/dev/null || echo 0) )); then
                EMOJI="🔵"
            else
                EMOJI="⚪"
            fi

            ALERT+="$EMOJI $metric: $value
"
        done

        # Add reasons
        REASONS=$(echo "$SIGNAL" | jq -r '.reasons[]' 2>/dev/null)
        if [ -n "$REASONS" ]; then
            ALERT+="
Reasons:
"
            while IFS= read -r reason; do
                ALERT+="• $reason
"
            done <<< "$REASONS"
        fi

        # Send to Telegram
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="$ALERT" \
            > /dev/null 2>&1

        echo "Alert sent for ${SYMBOL}: ${SIGNAL_TYPE} (${STRENGTH}/10)"
    fi
done
