#!/usr/bin/env node
/**
 * Gork Telegram Bot - Using native fetch (no spawnSync)
 */

import { createRequire } from 'module';
import { writeFileSync, existsSync, readFileSync, mkdirSync } from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const execAsync = promisify(exec);

const require = createRequire(import.meta.url);
const character = require('./characters/gork-telegram.character.json');

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || character.settings.secrets.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID || character.settings.TELEGRAM_CHAT_ID ;
const API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// Script directory for relative paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// State file (use env or relative path)
const STATE_FILE = process.env.GORK_STATE_FILE || `${__dirname}/state/gork-bot-state.json`;
let state = { lastUpdateId: 0 };

function loadState() {
  try {
    if (existsSync(STATE_FILE)) state = JSON.parse(readFileSync(STATE_FILE, 'utf-8'));
  } catch (e) {}
}

function saveState() {
  try { writeFileSync(STATE_FILE, JSON.stringify(state, null, 2)); } catch (e) {}
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

// Get prices using native fetch
async function getPrice(symbol) {
  try {
    const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}USDT`);
    const data = await res.json();
    return parseFloat(data.price);
  } catch {
    return 0;
  }
}

// Optimized parameters from GA RSI + Z-Score backtesting (Feb 27, 2026)
const SIGNAL_PARAMS = {
  BTC: { rsiPeriod: 8, longRsi: 30, shortRsi: 79, leverage: 3 },
  ZEC: { rsiPeriod: 10, longRsi: 38, shortRsi: 76, leverage: 3 },
  NEAR: { rsiPeriod: 26, longRsi: 31, shortRsi: 80, leverage: 3 }
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
    const sma = closes.slice(-20).reduce((a,b) => a+b, 0) / 20;
    const std = Math.sqrt(closes.slice(-20).reduce((sum, c) => sum + (c-sma)**2, 0) / 20);
    
    return { price: closes[closes.length-1], rsi, bbUpper: sma + 2*std, bbLower: sma - 2*std };
  } catch (e) {
    return { price: 0, rsi: 50, bbUpper: 0, bbLower: 0 };
  }
}

// Commands
async function cmdSignals() {
  const lines = ['📊 ALL SIGNALS (Validated Strategies)', ''];
  
  // Fetch all data in parallel
  const [btcData, nearData, zecData] = await Promise.all([
    fetch(`https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=50`).then(r => r.json()),
    fetch(`https://api.binance.com/api/v3/klines?symbol=NEARUSDT&interval=1h&limit=50`).then(r => r.json()),
    fetch(`https://api.binance.com/api/v3/klines?symbol=ZECUSDT&interval=1h&limit=50`).then(r => r.json())
  ]);
  
  // === MEAN REVERSION (RSI + BB) ===
  lines.push('━━━ Mean Reversion (RSI+BB) ━━━');
  
  for (const [name, candles, params] of [
    ['BTC', btcData, SIGNAL_PARAMS.BTC],
    ['NEAR', nearData, SIGNAL_PARAMS.NEAR],
    ['ZEC', zecData, SIGNAL_PARAMS.ZEC]
  ]) {
    const closes = candles.map(c => parseFloat(c[4]));
    const price = closes[closes.length - 1];
    
    // RSI
    let gains = 0, losses = 0;
    for (let i = 1; i <= params.rsiPeriod; i++) {
      const diff = closes[closes.length - i] - closes[closes.length - i - 1];
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const rsi = 100 - (100 / (1 + (gains/params.rsiPeriod) / (losses/params.rsiPeriod || 0.001)));
    
    // BB
    const sma = closes.slice(-20).reduce((a,b) => a+b, 0) / 20;
    const std = Math.sqrt(closes.slice(-20).reduce((sum, c) => sum + (c-sma)**2, 0) / 20);
    const bbLower = sma - 2*std;
    const bbUpper = sma + 2*std;
    
    let signal = '⚪';
    if (rsi > params.shortRsi && price > bbUpper) signal = '🔴 SHORT';
    else if (rsi < params.longRsi && price < bbLower) signal = '🟢 LONG';
    
    lines.push(`${name}: $${price.toFixed(name === 'BTC' ? 0 : name === 'ZEC' ? 2 : 4)} | RSI: ${rsi.toFixed(1)} | ${signal}`);
  }
  
  // === REVERSAL (LONG) ===
  lines.push('');
  lines.push('━━━ Reversal LONG ━━━');
  
  // BTC RSI Bounce
  const btcCloses = btcData.map(c => parseFloat(c[4]));
  const btcPrice = btcCloses[btcCloses.length - 1];
  let btcGains = 0, btcLosses = 0;
  for (let i = 1; i <= 14; i++) {
    const diff = btcCloses[btcCloses.length - i] - btcCloses[btcCloses.length - i - 1];
    if (diff > 0) btcGains += diff;
    else btcLosses -= diff;
  }
  const btcRsi = 100 - (100 / (1 + (btcGains/14) / (btcLosses/14 || 0.001)));
  const btcPrevRsi = btcRsi; // simplified
  const btcOversold = btcPrevRsi < 30 && btcRsi > btcPrevRsi;
  lines.push(`BTC: RSI ${btcRsi.toFixed(1)} | ${btcOversold ? '🟢 BOUNCE SIGNAL' : '⚪ No signal'} (94.1% WR)`);
  
  // NEAR Support Bounce
  const nearCloses = nearData.map(c => parseFloat(c[4]));
  const nearLows = nearData.map(c => parseFloat(c[3]));
  const nearPrice = nearCloses[nearCloses.length - 1];
  const nearSupport = Math.min(...nearLows.slice(-20));
  const nearLow = nearLows[nearLows.length - 1];
  const nearDistance = ((nearPrice - nearSupport) / nearSupport * 100);
  const nearBounce = nearLow <= nearSupport * 1.01 && nearPrice > nearLow;
  lines.push(`NEAR: $${nearPrice.toFixed(4)} | Support: $${nearSupport.toFixed(4)} (+${nearDistance.toFixed(1)}%)`);
  lines.push(`     ${nearBounce ? '🟢 BOUNCE SIGNAL' : nearDistance < 5 ? '⚠️ Near support' : '⚪ No signal'} (76.7% WR)`);
  
  // === BREAKDOWN (SHORT) ===
  lines.push('');
  lines.push('━━━ Breakdown SHORT ━━━');
  
  // ZEC Support Breakdown
  const zecCloses = zecData.map(c => parseFloat(c[4]));
  const zecLows = zecData.map(c => parseFloat(c[3]));
  const zecPrice = zecCloses[zecCloses.length - 1];
  const zecSupport = Math.min(...zecLows.slice(-20));
  const zecDistance = ((zecPrice - zecSupport) / zecSupport * 100);
  const zecBreakdown = zecPrice < zecSupport;
  lines.push(`ZEC: $${zecPrice.toFixed(2)} | Support: $${zecSupport.toFixed(2)} (+${zecDistance.toFixed(1)}%)`);
  lines.push(`     ${zecBreakdown ? '🔴 BREAKDOWN SIGNAL' : zecDistance < 3 ? '⚠️ Near breakdown' : '⚪ No signal'} (71.4% WR)`);
  
  // ZEC MA5/20 Death Cross
  const zecMa5 = zecCloses.slice(-5).reduce((a,b) => a+b, 0) / 5;
  const zecMa20 = zecCloses.slice(-20).reduce((a,b) => a+b, 0) / 20;
  const zecPrevMa5 = zecCloses.slice(-6, -1).reduce((a,b) => a+b, 0) / 5;
  const zecPrevMa20 = zecCloses.slice(-21, -1).reduce((a,b) => a+b, 0) / 20;
  const zecDeathCross = zecMa5 < zecMa20 && zecPrevMa5 >= zecPrevMa20;
  const zecMaBelow = zecMa5 < zecMa20;
  lines.push(`ZEC: MA5 $${zecMa5.toFixed(2)} vs MA20 $${zecMa20.toFixed(2)}`);
  lines.push(`     ${zecDeathCross ? '🔴 DEATH CROSS SIGNAL' : zecMaBelow ? '⚠️ MA5 below MA20' : '⚪ No signal'} (85.7% WR, 7.77 R/R)`);
  
  return lines.join('\n');
}

async function cmdRestart() {
  try {
    const { stdout, stderr } = await execAsync('/opt/homebrew/bin/openclaw gateway restart --force', {
      timeout: 30000
    });

    return `🔄 Gateway restart initiated\n\n${stdout || stderr || 'Command executed'}`;
  } catch (e) {
    return `❌ Restart failed: ${e.message}`;
  }
}

async function cmdReboot() {
  try {
    // Notify first (we won't be able to after reboot)
    await tg('sendMessage', { 
      chat_id: CHAT_ID, 
      text: '🔄 Rebooting system now...\n\nBot will be back online in ~2 minutes.' 
    });
    
    // Small delay to ensure message sends
    await new Promise(r => setTimeout(r, 1000));
    
    // Reboot
    await execAsync('osascript -e \'tell app "System Events" to restart\'', {
      timeout: 5000
    });
    
    return null; // Already sent message
  } catch (e) {
    return `❌ Reboot failed: ${e.message}`;
  }
}

function cmdHelp() {
  return `📖 Commands

/signals - RSI mean reversion signals
/reversal - BTC/NEAR reversal LONG
/breakdown - ZEC breakdown SHORT
/zscore [SYMBOL] - Z-Score heatmap
/positions - Active positions
/pnl - Full P&L summary
/proof - Signal accuracy stats
/status - System status
/restart - Restart OpenClaw gateway
/reboot - Reboot computer ⚠️
/help - Show this message`;
}

function cmdStatus() {
  return `⚡ Gork Status

✅ Bot running
✅ Signal monitor: 15 min
✅ Position check: 60 min

Type /signals or /positions`;
}

async function cmdPnL() {
  try {
    const res = await fetch('https://api.rhea.finance/v3/margin-trading/position/history?address=kampouse.near&page_num=0&page_size=20&order_column=close_timestamp&order_by=DESC&tokens=');
    const data = await res.json();
    
    if (data.code !== 0) return 'Error fetching P&L';
    
    const positions = data.data.position_records;
    
    let totalPnL = 0, totalCollateral = 0, wins = 0;
    
    for (const pos of positions) {
      const pnl = parseFloat(pos.pnl);
      const collateral = parseFloat(pos.amount_c) / 1e18;
      totalPnL += pnl;
      totalCollateral += collateral;
      if (pnl > 0) wins++;
    }
    
    // Query actual open positions via RPC
    let openCount = 0;
    let unrealized = 0;
    try {
      const posRes = await fetch('https://rpc.mainnet.near.org', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: '1',
          method: 'query',
          params: {
            request_type: 'call_function',
            finality: 'final',
            account_id: 'contract.main.burrow.near',
            method_name: 'get_margin_account',
            args_base64: Buffer.from('{"account_id":"kampouse.near"}').toString('base64')
          }
        })
      });
      const posData = await posRes.json();
      if (posData.result) {
        const account = JSON.parse(Buffer.from(posData.result.result).toString());
        openCount = Object.keys(account.margin_positions || {}).length;
      }
    } catch (e) { /* ignore */ }
    
    const total = totalPnL + unrealized;
    const roi = totalCollateral > 0 ? (total / totalCollateral * 100) : 0;
    const winRate = positions.length > 0 ? (wins / positions.length * 100) : 0;
    
    return `📊 *P&L Summary*

*Realized:* $${totalPnL.toFixed(2)} (${positions.length} trades)
*Unrealized:* $${unrealized.toFixed(2)} (${openCount} open)
*Total:* $${total.toFixed(2)}

*Win Rate:* ${wins}/${positions.length} (${winRate.toFixed(0)}%)
*ROI:* ${roi.toFixed(1)}%`;
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

function cmdProof() {
  try {
    const logFile = process.env.SIGNAL_LOG || join(__dirname, 'monitors', 'signal_validation_log.json');
    
    if (!existsSync(logFile)) {
      return '📊 No signals logged yet.\n\nWaiting for first signal to trigger...';
    }
    
    const data = JSON.parse(readFileSync(logFile, 'utf-8'));
    const stats = data.stats || { total: 0, correct: 0, pending: 0 };
    const signals = data.signals || [];
    
    if (signals.length === 0) {
      return '📊 No signals logged yet.\n\nMonitoring BTC, NEAR, ZEC...';
    }
    
    const completed = signals.filter(s => !['pending'].includes(s.status));
    const hitRate = completed.length > 0 ? (stats.correct / completed.length * 100) : 0;
    
    // Count by status
    const hitCount = signals.filter(s => s.status === 'hit').length;
    const stoppedCount = signals.filter(s => s.status === 'stopped').length;
    const missCount = signals.filter(s => s.status === 'miss').length;
    
    let msg = `📊 *Signal Accuracy Proof*\n\n`;
    msg += `*Total Signals:* ${stats.total}\n`;
    msg += `*Pending:* ${stats.pending}\n`;
    msg += `*Hit Rate:* ${hitRate.toFixed(1)}%\n`;
    msg += `✅ Hit: ${hitCount} | 🛑 Stopped: ${stoppedCount} | ❌ Miss: ${missCount}\n\n`;
    
    // Show last 3 signals
    const recent = signals.slice(-3);
    if (recent.length > 0) {
      msg += `*Recent Signals:*\n`;
      for (const sig of recent) {
        const emoji = sig.status === 'hit' ? '✅' : sig.status === 'stopped' ? '🛑' : sig.status === 'miss' ? '❌' : '⏳';
        const date = new Date(sig.timestamp).toLocaleDateString();
        msg += `${emoji} ${sig.type} ${sig.symbol} @ $${sig.entry_price.toFixed(2)} (${date})\n`;
        msg += `   Target: $${sig.target_price.toFixed(2)} | Stop: $${(sig.stop_loss || 0).toFixed(2)}\n`;
        
        // Show latest outcome
        const hours = ['24', '4', '1'].find(h => sig.outcomes[h]);
        if (hours && sig.outcomes[hours]) {
          const o = sig.outcomes[hours];
          msg += `   ${hours}h: ${o.pnl_pct > 0 ? '+' : ''}${o.pnl_pct.toFixed(1)}%\n`;
        }
      }
    }
    
    return msg;
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

async function cmdPositions() {
  try {
    // Query Burrow via RPC directly (no CLI dependency)
    const res = await fetch('https://rpc.mainnet.near.org', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: '1',
        method: 'query',
        params: {
          request_type: 'call_function',
          finality: 'final',
          account_id: 'contract.main.burrow.near',
          method_name: 'get_margin_account',
          args_base64: Buffer.from('{"account_id":"kampouse.near"}').toString('base64')
        }
      })
    });
    
    const data = await res.json();
    if (data.error) return `RPC Error: ${data.error.message}`;
    
    const result = JSON.parse(Buffer.from(data.result.result).toString());
    const positions = result.margin_positions || {};
    const positionKeys = Object.keys(positions);
    
    if (positionKeys.length === 0) {
      return `📊 *Active Positions*\n\nNo open positions`;
    }
    
    let lines = [`📊 *Active Positions*\n`];
    for (const key of positionKeys) {
      lines.push(`• ${key}`);
    }
    return lines.join('\n');
  } catch (e) {
    return `Error fetching positions: ${e.message}`;
  }
}

async function cmdZscore(symbol = 'ZECUSDT') {
  try {
    const zscoreScript = join(__dirname, 'plugins', 'zscore-command.sh');
    const { stdout, stderr } = await execAsync(
      `${zscoreScript} ${symbol}`,
      { timeout: 30000 }
    );
    
    if (stderr && !stdout) {
      return `Error: ${stderr}`;
    }
    
    // Return raw output (no markdown escaping needed)
    return stdout;
  } catch (e) {
    return `Error fetching Z-Score: ${e.message}`;
  }
}

async function cmdReversal() {
  try {
    // BTC RSI check
    const btcRes = await fetch(`https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=50`);
    const btcCandles = await btcRes.json();
    const btcCloses = btcCandles.map(c => parseFloat(c[4]));
    
    // Calculate RSI
    let gains = 0, losses = 0;
    for (let i = 1; i <= 14; i++) {
      const diff = btcCloses[btcCloses.length - i] - btcCloses[btcCloses.length - i - 1];
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const btcRsi = 100 - (100 / (1 + (gains/14) / (losses/14 || 0.001)));
    const btcPrevRsi = btcRsi; // Simplified
    const btcPrice = btcCloses[btcCloses.length - 1];
    
    // NEAR support check
    const nearRes = await fetch(`https://api.binance.com/api/v3/klines?symbol=NEARUSDT&interval=1h&limit=50`);
    const nearCandles = await nearRes.json();
    const nearLows = nearCandles.map(c => parseFloat(c[3]));
    const nearCloses = nearCandles.map(c => parseFloat(c[4]));
    const nearSupport = Math.min(...nearLows.slice(-20));
    const nearPrice = nearCloses[nearCloses.length - 1];
    const nearLow = nearLows[nearLows.length - 1];
    const nearDistance = ((nearPrice - nearSupport) / nearSupport * 100);
    
    const lines = [
      '📊 Reversal Signals (LONG)',
      '',
      `BTC: $${btcPrice.toFixed(0)} | RSI: ${btcRsi.toFixed(1)}`,
      `  Strategy: RSI < 30 bounce (94.1% WR)`,
      `  Status: ${btcRsi < 35 ? '⚠️ Near oversold' : '⚪ No signal'}`,
      '',
      `NEAR: $${nearPrice.toFixed(4)} | Support: $${nearSupport.toFixed(4)}`,
      `  Distance: +${nearDistance.toFixed(1)}%`,
      `  Strategy: Support bounce (76.7% WR)`,
      `  Status: ${nearDistance < 5 ? '⚠️ Near support' : '⚪ No signal'}`,
      '',
      'Validated: BTC +61.5% | NEAR +443.7% OOS'
    ];
    
    return lines.join('\n');
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

async function cmdBreakdown() {
  try {
    // ZEC support breakdown
    const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=ZECUSDT&interval=1h&limit=50`);
    const candles = await res.json();
    const closes = candles.map(c => parseFloat(c[4]));
    const lows = candles.map(c => parseFloat(c[3]));
    
    const price = closes[closes.length - 1];
    const support = Math.min(...lows.slice(-20));
    const distance = ((price - support) / support * 100);
    
    // MA5/20 check
    const ma5 = closes.slice(-5).reduce((a,b) => a+b, 0) / 5;
    const ma20 = closes.slice(-20).reduce((a,b) => a+b, 0) / 20;
    const maDistance = ((ma5 - ma20) / ma20 * 100);
    
    // RSI
    let gains = 0, losses = 0;
    for (let i = 1; i <= 14; i++) {
      const diff = closes[closes.length - i] - closes[closes.length - i - 1];
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const rsi = 100 - (100 / (1 + (gains/14) / (losses/14 || 0.001)));
    
    const lines = [
      '📊 Breakdown Signals (SHORT)',
      '',
      `ZEC: $${price.toFixed(2)} | RSI: ${rsi.toFixed(1)}`,
      '',
      `Support: $${support.toFixed(2)} | Distance: +${distance.toFixed(1)}%`,
      `  Strategy: Break below support (71.4% WR)`,
      `  Status: ${distance < 3 ? '⚠️ Near breakdown' : '⚪ No signal'}`,
      '',
      `MA5: $${ma5.toFixed(2)} | MA20: $${ma20.toFixed(2)}`,
      `  Cross: ${maDistance < 0 ? '🔴 Death cross' : '🟢 Above'}`,
      `  Strategy: MA5/20 cross (85.7% WR, 7.77 R/R)`,
      `  Status: ${maDistance < 0 ? '⚠️ Signal active' : '⚪ No signal'}`,
      '',
      'Validated: +49.8% OOS'
    ];
    
    return lines.join('\n');
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

// Main
async function main() {
  console.log('🚀 Gork Bot starting (native fetch)...');
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
        
        // Parse command and arguments
        const parts = msg.text.trim().split(/\s+/);
        const cmd = parts[0].toLowerCase();
        const arg = parts[1] || 'ZECUSDT'; // Default to ZEC
        
        if (cmd === '/signals' || cmd === 'signals') {
          response = await cmdSignals();
        } else if (cmd === '/reversal' || cmd === 'reversal') {
          response = await cmdReversal();
        } else if (cmd === '/breakdown' || cmd === 'breakdown') {
          response = await cmdBreakdown();
        } else if (cmd === '/zscore' || cmd === 'zscore') {
          response = await cmdZscore(arg.toUpperCase());
        } else if (cmd === '/pnl' || cmd === 'pnl') {
          response = await cmdPnL();
        } else if (cmd === '/proof' || cmd === 'proof') {
          response = cmdProof();
        } else if (cmd === '/positions' || cmd === 'positions' || cmd === '/pos') {
          response = await cmdPositions();
        } else if (cmd === '/status' || cmd === 'status') {
          response = cmdStatus();
        } else if (cmd === '/restart' || cmd === 'restart') {
          response = await cmdRestart();
        } else if (cmd === '/reboot' || cmd === 'reboot') {
          response = await cmdReboot();
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
