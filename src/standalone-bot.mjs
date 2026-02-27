#!/usr/bin/env node
/**
 * Gork Telegram Bot - Trading signals and market monitoring
 * 
 * Usage:
 *   TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=xxx node standalone-bot.mjs
 */

import { writeFileSync, existsSync, readFileSync, mkdirSync } from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const execAsync = promisify(exec);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration from environment
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;

if (!BOT_TOKEN || !CHAT_ID) {
  console.error('❌ Missing required environment variables:');
  console.error('   TELEGRAM_BOT_TOKEN - Get from @BotFather');
  console.error('   TELEGRAM_CHAT_ID - Your Telegram chat ID');
  process.exit(1);
}

const API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// State file (use XDG_DATA_HOME or ~/.local/share)
const STATE_DIR = process.env.XDG_DATA_HOME || join(process.env.HOME, '.local', 'share', 'gork-bot');
const STATE_FILE = join(STATE_DIR, 'state.json');
let state = { lastUpdateId: 0 };

function loadState() {
  try {
    if (existsSync(STATE_FILE)) {
      state = JSON.parse(readFileSync(STATE_FILE, 'utf-8'));
    }
  } catch (e) {
    console.error('State load error:', e.message);
  }
}

function saveState() {
  try {
    if (!existsSync(STATE_DIR)) {
      mkdirSync(STATE_DIR, { recursive: true });
    }
    writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  } catch (e) {
    console.error('State save error:', e.message);
  }
}

// Telegram API using native fetch
async function tg(method, params = {}) {
  try {
    const res = await fetch(`${API}/${method}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return await res.json();
  } catch (e) {
    console.error(`TG error (${method}):`, e.message);
    return { ok: false };
  }
}

// Get price from Binance
async function getPrice(symbol) {
  try {
    const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}USDT`);
    const data = await res.json();
    return parseFloat(data.price);
  } catch {
    return 0;
  }
}

// Optimized parameters from GA RSI + Z-Score backtesting
const SIGNAL_PARAMS = {
  BTC: { rsiPeriod: 8, longRsi: 30, shortRsi: 79, leverage: 3 },
  ZEC: { rsiPeriod: 10, longRsi: 38, shortRsi: 76, leverage: 3 },
  NEAR: { rsiPeriod: 26, longRsi: 31, shortRsi: 80, leverage: 3 },
  ETH: { rsiPeriod: 9, longRsi: 25, shortRsi: 80, leverage: 3 },
  SOL: { rsiPeriod: 28, longRsi: 22, shortRsi: 71, leverage: 3 },
  PLTR: { rsiPeriod: 9, longRsi: 26, shortRsi: 62, leverage: 3 },
  MSTR: { rsiPeriod: 10, longRsi: 38, shortRsi: 66, leverage: 3 }
};

// Get RSI using native fetch with configurable period
async function getRSI(symbol, period = 14) {
  try {
    const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}USDT&interval=1h&limit=100`);
    const candles = await res.json();
    const closes = candles.map(c => parseFloat(c[4]));
    
    // Calculate RSI with configurable period
    let gains = 0, losses = 0;
    for (let i = 1; i <= period; i++) {
      const diff = closes[closes.length - i] - closes[closes.length - i - 1];
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const avgGain = gains / period;
    const avgLoss = losses / period;
    const rs = avgLoss > 0 ? avgGain / avgLoss : 100;
    const rsi = 100 - (100 / (1 + rs));
    
    // Bollinger Bands (20-period, 2 std)
    const sma = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const std = Math.sqrt(closes.slice(-20).reduce((sum, c) => sum + (c - sma) ** 2, 0) / 20);
    
    return { price: closes[closes.length - 1], rsi, bbUpper: sma + 2 * std, bbLower: sma - 2 * std };
  } catch (e) {
    return { price: 0, rsi: 50, bbUpper: 0, bbLower: 0 };
  }
}

// Commands
async function cmdSignals() {
  const [near, zec, btc] = await Promise.all([
    getRSI('NEAR', SIGNAL_PARAMS.NEAR.rsiPeriod),
    getRSI('ZEC', SIGNAL_PARAMS.ZEC.rsiPeriod),
    getRSI('BTC', SIGNAL_PARAMS.BTC.rsiPeriod)
  ]);
  
  const lines = ['📊 Current Signals (GA Optimized)', ''];
  
  for (const [name, data] of [['NEAR', near], ['ZEC', zec], ['BTC', btc]]) {
    const params = SIGNAL_PARAMS[name];
    let signal = '⚪ NONE';
    let strength = '';
    
    if (data.rsi > params.shortRsi && data.price > data.bbUpper) {
      signal = '🔴 SHORT';
      strength = ` (RSI > ${params.shortRsi})`;
    } else if (data.rsi < params.longRsi && data.price < data.bbLower) {
      signal = '🟢 LONG';
      strength = ` (RSI < ${params.longRsi})`;
    }
    
    lines.push(`${name}: $${data.price.toFixed(name === 'BTC' ? 0 : name === 'ZEC' ? 2 : 4)} | RSI(${params.rsiPeriod}): ${data.rsi.toFixed(1)} | ${signal}${strength}`);
  }
  
  return lines.join('\n');
}

function cmdHelp() {
  return `📖 Commands

/signals - Check RSI signals
/zscore [SYMBOL] - Z-Score heatmap analysis
/positions - Show active positions
/pnl - Full P&L summary
/status - System status
/help - Show this message`;
}

function cmdStatus() {
  return `⚡ Gork Status

✅ Bot running
✅ Signal monitor: 15 min
✅ Position check: 60 min

Type /signals or /positions`;
}

async function cmdPositions() {
  try {
    const [nearPrice, zecPrice] = await Promise.all([getPrice('NEAR'), getPrice('ZEC')]);
    
    // Note: In production, fetch from your trading platform's API
    return `📊 *Active Positions*

Prices:
  NEAR: $${nearPrice.toFixed(4)}
  ZEC: $${zecPrice.toFixed(2)}

Connect to your trading platform for live positions.`;
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

async function cmdPnL() {
  try {
    // Note: In production, fetch from your trading platform's API
    return `📊 *P&L Summary*

Connect to your trading platform for live P&L data.`;
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

async function cmdZscore(symbol = 'ZECUSDT') {
  try {
    const scriptPath = join(__dirname, '..', 'plugins', 'zscore-command.sh');
    const { stdout, stderr } = await execAsync(`${scriptPath} ${symbol}`, { timeout: 30000 });
    
    if (stderr && !stdout) {
      return `Error: ${stderr}`;
    }
    
    return stdout;
  } catch (e) {
    return `Error fetching Z-Score: ${e.message}`;
  }
}

// Main
async function main() {
  console.log('🚀 Gork Bot starting...');
  console.log(`   Chat: ${CHAT_ID}`);
  
  loadState();
  
  const me = await tg('getMe');
  if (!me.ok) {
    console.error('❌ Bot token invalid');
    process.exit(1);
  }
  console.log(`   Bot: @${me.result.username}`);
  
  await tg('sendMessage', { chat_id: CHAT_ID, text: '⚡ Gork Bot online\n\nType /help for commands' });
  
  console.log('✅ Listening...');
  
  while (true) {
    try {
      const updates = await tg('getUpdates', {
        offset: state.lastUpdateId + 1,
        timeout: 30
      });
      
      if (!updates.ok || !updates.result?.length) continue;
      
      for (const update of updates.result) {
        state.lastUpdateId = update.update_id;
        
        const msg = update.message;
        if (!msg?.text) continue;
        
        console.log(`📩 ${msg.text}`);
        
        if (msg.chat.id.toString() !== CHAT_ID.toString()) continue;
        
        let response = null;
        
        const parts = msg.text.trim().split(/\s+/);
        const cmd = parts[0].toLowerCase();
        const arg = parts[1] || 'ZECUSDT';
        
        if (cmd === '/signals' || cmd === 'signals') {
          response = await cmdSignals();
        } else if (cmd === '/zscore' || cmd === 'zscore') {
          response = await cmdZscore(arg.toUpperCase());
        } else if (cmd === '/pnl' || cmd === 'pnl') {
          response = await cmdPnL();
        } else if (cmd === '/positions' || cmd === 'positions' || cmd === '/pos') {
          response = await cmdPositions();
        } else if (cmd === '/status' || cmd === 'status') {
          response = cmdStatus();
        } else if (cmd === '/help' || cmd === 'help') {
          response = cmdHelp();
        }
        
        if (response) {
          await tg('sendMessage', { chat_id: msg.chat.id, text: response });
        }
        
        saveState();
      }
    } catch (e) {
      console.error('Poll error:', e.message);
      await new Promise(r => setTimeout(r, 5000));
    }
  }
}

main().catch(console.error);
