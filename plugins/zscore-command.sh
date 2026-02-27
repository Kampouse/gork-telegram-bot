#!/bin/bash
# Z-Score Command - Multi-metric analysis for crypto trading
# Usage: ./zscore-command.sh SYMBOL
# Example: ./zscore-command.sh ZECUSDT

SYMBOL="${1:-ZECUSDT}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python zscore script exists
ZSCORE_PY="${SCRIPT_DIR}/zscore_heatmap.py"

if [ ! -f "$ZSCORE_PY" ]; then
    echo "❌ Z-Score script not found: $ZSCORE_PY"
    echo ""
    echo "To set up Z-Score analysis:"
    echo "1. Create a virtual environment: python3 -m venv venv"
    echo "2. Activate it: source venv/bin/activate"
    echo "3. Install dependencies: pip install requests pandas numpy"
    echo "4. Create zscore_heatmap.py with your analysis logic"
    exit 1
fi

# Run the analysis
cd "$SCRIPT_DIR"
python3 "$ZSCORE_PY" "$SYMBOL" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "⚠️ Error running Z-Score analysis"
    echo "Check that all dependencies are installed"
fi
