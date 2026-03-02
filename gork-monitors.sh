#!/bin/bash
# Gork Monitors Control Script
# Manage all monitoring services via launchd

COMMAND=${1:-status}

SERVICES=(
    "com.gork.standalone-bot"
    "com.gork.zec-breakdown"
    "com.gork.btc-reversal"
    "com.gork.near-reversal"
    "com.gork.ga-rsi"
    "com.gork.zec-ma-short"
    "com.gork.zscore"
    "com.gork.signal-validator"
    "com.gork.head-shoulders-monitor"
)

LOGS=(
    "/Users/asil/.openclaw/workspace/logs/standalone-bot.log"
    "/Users/asil/.openclaw/workspace/logs/zec_breakdown.log"
    "/Users/asil/.openclaw/workspace/logs/btc_reversal.log"
    "/Users/asil/.openclaw/workspace/logs/near_reversal.log"
    "/Users/asil/.openclaw/workspace/logs/ga_rsi.log"
    "/Users/asil/.openclaw/workspace/logs/zec_ma_short.log"
    "/Users/asil/.openclaw/workspace/logs/zscore.log"
    "/Users/asil/.openclaw/workspace/logs/signal_validator.log"
    "/Users/asil/.openclaw/workspace/logs/head_shoulders.log"
)

status() {
    echo "⚡ Gork Monitors Status"
    echo "======================="
    echo ""
    
    for i in "${!SERVICES[@]}"; do
        service="${SERVICES[$i]}"
        status_line=$(launchctl list | grep "$service")
        
        if [ -n "$status_line" ]; then
            pid=$(echo "$status_line" | awk '{print $1}')
            exit_code=$(echo "$status_line" | awk '{print $2}')
            
            if [ "$pid" = "-" ]; then
                if [ "$exit_code" = "0" ]; then
                    echo "✅ ${service}"
                else
                    echo "⚠️  ${service} (exit: $exit_code)"
                fi
            else
                echo "✅ ${service} (PID: $pid)"
            fi
        else
            echo "❌ ${service} (not loaded)"
        fi
    done
    
    echo ""
    echo "Total: ${#SERVICES[@]} services"
}

start_all() {
    echo "Starting all monitors..."
    for service in "${SERVICES[@]}"; do
        launchctl start "$service" 2>/dev/null && echo "✅ Started $service"
    done
}

stop_all() {
    echo "Stopping all monitors..."
    for service in "${SERVICES[@]}"; do
        launchctl stop "$service" 2>/dev/null && echo "⏹️  Stopped $service"
    done
}

reload_all() {
    echo "Reloading all monitors..."
    cd ~/Library/LaunchAgents
    for plist in com.gork.*.plist; do
        launchctl unload "$plist" 2>/dev/null
        launchctl load "$plist" 2>/dev/null && echo "🔄 Reloaded $plist"
    done
}

logs() {
    service_idx=$1
    if [ -z "$service_idx" ]; then
        echo "Usage: $0 logs <0-8>"
        echo ""
        for i in "${!SERVICES[@]}"; do
            echo "  $i: ${SERVICES[$i]}"
        done
        return
    fi
    
    log_file="${LOGS[$service_idx]}"
    if [ -f "$log_file" ]; then
        tail -20 "$log_file"
    else
        echo "Log file not found: $log_file"
    fi
}

case "$COMMAND" in
    status)
        status
        ;;
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    reload)
        reload_all
        ;;
    logs)
        logs "$2"
        ;;
    *)
        echo "Usage: $0 {status|start|stop|reload|logs <idx>}"
        echo ""
        echo "Commands:"
        echo "  status  - Show status of all monitors"
        echo "  start   - Start all monitors"
        echo "  stop    - Stop all monitors"
        echo "  reload  - Reload all monitors from plist files"
        echo "  logs N  - Show last 20 lines of log for service N"
        ;;
esac
