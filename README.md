# Gork Telegram Bot

A standalone Telegram bot for monitoring crypto markets and managing trading signals.

## Features

- 📊 **Signal Monitoring** - RSI + Bollinger Band signals for BTC, NEAR, ZEC
- 📈 **Z-Score Analysis** - Multi-metric analysis with 7 indicators
- 💰 **Position Tracking** - Monitor active trading positions
- 📉 **P&L Reporting** - Track profit/loss across trades
- ⚡ **Real-time Alerts** - Automated monitoring with configurable thresholds

## Commands

| Command | Description |
|---------|-------------|
| `/signals` | Check current RSI signals for monitored assets |
| `/zscore [SYMBOL]` | Multi-metric Z-score analysis (default: ZEC) |
| `/positions` | Show active trading positions |
| `/pnl` | Full profit/loss summary |
| `/status` | System status check |
| `/restart` | Restart OpenClaw gateway |
| `/help` | Show command list |

## Setup

### Prerequisites

- Node.js v18+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Installation

```bash
git clone https://github.com/Kampouse/gork-telegram-bot.git
cd gork-telegram-bot
npm install
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Running

```bash
npm start
```

Or directly:
```bash
node standalone-bot.mjs
```

## Architecture

```
gork-telegram-bot/
├── standalone-bot.mjs      # Main bot logic
├── characters/
│   └── gork.character.json # Bot personality (no secrets)
├── .env.example            # Environment template
├── package.json
└── README.md
```

## Signal System (GA Optimized)

The bot uses genetically optimized parameters for mean reversion trading:

| Asset | RSI Period | LONG | SHORT | Leverage | Win Rate |
|-------|------------|------|-------|----------|----------|
| BTC   | 8          | < 30 | > 79  | 3x       | 100%     |
| NEAR  | 26         | < 31 | > 80  | 3x       | 100%     |
| ZEC   | 10         | < 38 | > 76  | 3x       | 83.3%    |

**Entry conditions:**
- LONG: RSI < threshold AND price < lower Bollinger Band
- SHORT: RSI > threshold AND price > upper Bollinger Band

## Z-Score Integration

The `/zscore` command provides multi-metric analysis:

- Price Z-Score
- CVD (Cumulative Volume Delta)
- Open Interest
- Funding Rate
- Volume
- Volume Delta
- OI Delta

Signals are triggered when strength ≥ 6/10.

## Development

### Adding New Assets

Edit `SIGNAL_PARAMS` in `standalone-bot.mjs`:

```javascript
const SIGNAL_PARAMS = {
  BTC: { rsiPeriod: 8, longRsi: 30, shortRsi: 79, leverage: 3 },
  NEAR: { rsiPeriod: 26, longRsi: 31, shortRsi: 80, leverage: 3 },
  // Add new asset here
  ETH: { rsiPeriod: 9, longRsi: 25, shortRsi: 80, leverage: 3 }
};
```

### Testing Signals

```bash
node standalone-bot.mjs --test
```

## Deployment

### Systemd Service (Linux)

```bash
sudo cp gork-bot.service /etc/systemd/system/
sudo systemctl enable gork-bot
sudo systemctl start gork-bot
```

### PM2 (Process Manager)

```bash
pm2 start standalone-bot.mjs --name gork-bot
pm2 save
pm2 startup
```

## License

MIT

## Related Projects

- [Gork Constitution](https://github.com/Kampouse/gork-constitution) - Governance smart contract
- [Gork Website](https://github.com/Kampouse/gork-website) - Landing page

## Support

- Telegram: [@gorkisnear](https://t.me/gorkisnear)
- Issues: [GitHub Issues](https://github.com/Kampouse/gork-telegram-bot/issues)
