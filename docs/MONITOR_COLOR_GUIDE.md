# 🎨 Trading Monitor - Color Guide

**NEW FEATURES:**
- ✅ **Balance Tracking** - Real-time account balance with P/L tracking
- ✅ **Headline Ticker** - Latest sentiment headlines with color-coded sentiment
- ✅ **Available/Locked Capital** - See how much capital is free vs in trades

## Color Coding System

The CryptoBoy Trading Monitor uses a comprehensive color system to help you quickly identify important information at a glance.

---

## 🎨 **Color Meanings**

### **Headers & Borders**
- **CYAN (Bright Blue)** - Section borders and dividers
- **WHITE (Bold)** - Section titles and headers

### **Profit & Loss**
- **🟢 GREEN** - Profitable trades, positive values, wins
  - Bright green = Excellent performance (>50% win rate, >$50 profit)
  - Regular green = Good performance
- **🔴 RED** - Losing trades, negative values, losses
  - Bright red = Poor performance (<40% win rate, significant losses)
- **🟡 YELLOW** - Neutral, breakeven, or waiting states
  - Warning indicator for trades running too long (>24h)

### **Information Types**
- **🔵 BLUE** - General information, timestamps, durations
- **🟣 MAGENTA** - Trade IDs, important highlights
- **⚪ WHITE** - Counts, quantities, entry prices

---

## 📊 **Indicator Symbols**

### **Direction Indicators**
- **↑** (Green) - Bullish/Up/Winning
- **↓** (Red) - Bearish/Down/Losing
- **→** (Yellow) - Neutral/Sideways

### **Performance Indicators**
- **★★** (Green) - Exceptional (>60% win rate)
- **★** (Green) - Excellent (>50% win rate)
- **✓** (Green) - Success
- **✗** (Red) - Failure

### **Special Indicators**
- **🔥↑** - Hot performance (>$50 profit or >10 USDT on a pair)
- **⏰** - Time-related information
- **🔒** - Security/Safety mode (DRY_RUN)
- **📊** - Statistics section
- **📈** - Performance charts
- **🔓** - Open trades
- **📝** - Closed trades

---

## 📋 **Section-by-Section Color Guide**

### **1. Header**
```
🔥 CRYPTOBOY TRADING MONITOR - VOIDCAT RDC  (White/Bold)
================================================================================  (Cyan)
🔒 Paper Trading Mode (DRY_RUN)  (Yellow/Bold)
⏰ Last Updated: 2025-10-28 08:20:37  (Blue)
```

### **2. Overall Statistics**
```
Total Trades:      10                 (White)
Winning Trades:    ↑ 7                (Green + up arrow)
Losing Trades:     ↓ 3                (Red + down arrow)
Breakeven:         → 0                (Yellow + neutral arrow)
Win Rate:          ★ 70.00%           (Green + star if >50%)
Total Profit:      🔥↑ +125.50 USDT   (Green + fire if >$50)
Avg Profit:        2.45%              (Blue)
Best Trade:        ↑ +8.50%           (Green + up arrow)
Worst Trade:       ↓ -2.80%           (Red + down arrow)
```

### **3. Performance by Pair**
```
BTC/USDT     | Trades:  15 | Win Rate: 66.7% | P/L: 🔥↑ +85.50 USDT
             (Bold)      (White)   (Green)        (Green+fire)

ETH/USDT     | Trades:   8 | Win Rate: 37.5% | P/L: ↓ -15.25 USDT
             (Bold)      (White)   (Red)          (Red+down)
```

### **4. Open Trades**
```
ID  12 | BTC/USDT     | Entry: $67,500.00 | Amount: 0.0007 | Stake: 50.00 USDT | Duration: 2.5h
(Magenta) (Bold)        (White)           (Blue)         (Yellow)           (Blue if <24h)
```

### **5. Recent Closed Trades**
```
10-28 14:30 | BTC/USDT     | ★↑ +5.25% (+2.63 USDT) | Duration: 3.2h | Exit: roi
(Blue)        (Bold)         (Green+star)              (Blue)           (Green)

10-28 12:15 | ETH/USDT     | ✗↓ -2.80% (-1.40 USDT) | Duration: 1.5h | Exit: stop_loss
(Blue)        (Bold)         (Red+cross)               (Blue)           (Red)
```

---

## 🎯 **Quick Reference**

### **Win Rate Colors**
- **🟢 Green** = ≥50% (good)
- **🟡 Yellow** = 40-49% (marginal)
- **🔴 Red** = <40% (needs improvement)

### **Profit Colors**
- **🟢 Green + 🔥** = >$50 or >10 USDT (excellent)
- **🟢 Green + ↑** = >$0 (profitable)
- **🟡 Yellow + →** = $0 (breakeven)
- **🔴 Red + ↓** = <$0 (losing)

### **Exit Reason Colors**
- **🟢 Green** = ROI target hit (good exit)
- **🔴 Red** = Stop loss hit (bad exit)
- **🔵 Blue** = Other reasons (neutral)

### **Duration Warnings**
- **🔵 Blue** = <24 hours (normal)
- **🟡 Yellow** = 24-48 hours (getting long)
- **🔴 Red** = >48 hours (too long!)

---

## 💡 **Tips for Reading the Monitor**

1. **Scan for colors first** - Green = good, Red = bad, Yellow = caution
2. **Look for special indicators** - 🔥 = hot performance, ★ = excellence
3. **Check arrows** - ↑ = winning/bullish, ↓ = losing/bearish
4. **Monitor duration colors** - Yellow/Red trades may need attention
5. **Exit reasons** - Green "roi" is ideal, Red "stop_loss" needs strategy review

---

## 🖥️ **Windows PowerShell Note**

If colors aren't showing:
1. Make sure you're using Windows 10 or later
2. Update PowerShell: `winget install Microsoft.PowerShell`
3. Run: `Set-ItemProperty HKCU:\Console VirtualTerminalLevel -Type DWORD 1`
4. Restart terminal

Alternatively, use Windows Terminal for better color support:
```bash
winget install Microsoft.WindowsTerminal
```

---

## 🔄 **Live Monitoring Commands**

### Start with color output
```bash
# Live monitoring (refreshes every 15 seconds)
python scripts/monitor_trading.py

# Custom refresh interval
python scripts/monitor_trading.py --interval 5

# One-time snapshot
python scripts/monitor_trading.py --once

# Easy launch with batch file (Windows)
start_monitor.bat
```

---

## 💰 **Balance Tracking Details**

### Balance Display Format
```
[BALANCE] | Starting: 1000.00 USDT | Current: 1015.50 USDT | P/L: ↑ +15.50 USDT (+1.55%)
Available: 915.50 USDT | Locked in Trades: 100.00 USDT
```

### What Each Value Means
- **Starting**: Initial paper trading capital (configured in live_config.json)
- **Current**: Starting balance + all realized profits/losses
- **P/L**: Total profit/loss with percentage gain
  - 🟢 Green with ↑ = Profit
  - 🔴 Red with ↓ = Loss
  - 🟡 Yellow with → = Breakeven
- **Available**: Free capital for opening new trades
- **Locked**: Capital currently allocated to open positions

### Balance Calculation
```
Current Balance = Starting Balance + Realized P/L from Closed Trades
Available = Current Balance - Capital Locked in Open Trades
```

---

## 📰 **Headline Ticker Details**

### Ticker Display Format
```
[NEWS] RECENT SENTIMENT HEADLINES
--------------------------------------------------------------------------------
↑ BULLISH  | Circle debuts Arc testnet with participation by BlackRock...
→ NEUTRAL  | Bitcoin Little Changed, Faces 'Double-Edged Sword' in Lever...
↓ BEARISH  | F2Pool co-founder refuses BIP-444 Bitcoin soft fork, says...
```

### Headline Features
- **Source**: Headlines from sentiment_signals.csv (FinBERT analysis)
- **Limit**: Shows 5 most recent unique headlines
- **Truncation**: Headlines limited to 65 characters for clean display
- **Sentiment Indicators**:
  - ↑ BULLISH (Green) - Positive sentiment score
  - ↓ BEARISH (Red) - Negative sentiment score
  - → NEUTRAL (Yellow) - Neutral sentiment score
- **Deduplication**: Same headline shown only once (by article_id)
- **Sorted**: Most recent headlines first (by timestamp)

### How Headlines Affect Trading
The bot uses these sentiment signals as part of its entry strategy:
- Bullish headlines (score > +0.3) can trigger entry signals
- Combined with technical indicators (RSI, volume, SMA)
- Multiple positive headlines increase confidence score
- Headlines refresh when you run `python scripts/run_data_pipeline.py --step 2 && --step 3`

---

**All colors and features are designed to help you make quick decisions without reading every detail!**

*VoidCat RDC - Excellence in Visual Design*
