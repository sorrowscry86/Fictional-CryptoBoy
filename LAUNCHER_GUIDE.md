# CryptoBoy System Launcher - Quick Reference

## 🚀 One-Click System Launch

Three ways to start the complete CryptoBoy trading system:

### Option 1: Batch File (CMD/PowerShell Compatible)
```bash
start_cryptoboy.bat
```
**Or double-click:** `start_cryptoboy.bat`

### Option 2: PowerShell Script (Enhanced)
```powershell
.\start_cryptoboy.ps1
```
**Or right-click → Run with PowerShell**

### Option 3: Desktop Shortcut
1. Run: `create_desktop_shortcut.bat`
2. Double-click the desktop icon: **CryptoBoy Trading System**

---

## 📋 What the System Launcher Does

### Automatic Startup Sequence:

**Step 1: Docker Check** ✓
- Verifies Docker Desktop is running
- Displays Docker version

**Step 2: Python Verification** ✓ (PowerShell only)
- Confirms Python is installed
- Shows Python version

**Step 3: Trading Bot Launch** ✓
- Starts Docker container (creates if needed)
- Waits for initialization (5 seconds)
- Confirms bot is running

**Step 4: Health Check** ✓
- Verifies bot status
- Shows loaded sentiment signals
- Displays active trading pairs

**Step 5: System Status** ✓
- Container information
- Data file status
- Last update timestamps

**Step 6: Monitor Dashboard** ✓
- Syncs database from container
- Launches live monitoring
- Auto-refresh every 15 seconds

---

## 🎯 All Launcher Features

| Feature | Batch (.bat) | PowerShell (.ps1) |
|---------|--------------|-------------------|
| Docker check | ✓ | ✓ |
| Python check | ✗ | ✓ |
| Auto-start bot | ✓ | ✓ |
| Health verification | ✓ | ✓ |
| Data file status | ✓ | ✓ |
| Live monitor | ✓ | ✓ |
| Color output | ✓ | ✓ Enhanced |
| Detailed logging | Basic | Advanced |
| Error handling | ✓ | ✓ Enhanced |

---

## 📊 What You'll See

### During Startup:
```
================================================================================
                  CRYPTOBOY TRADING SYSTEM - VOIDCAT RDC
================================================================================

[STEP 1/6] Checking Docker...
[OK] Docker is running
  Docker version: 24.0.7

[STEP 2/6] Checking Python...
[OK] Python is available
  Python 3.11.4

[STEP 3/6] Starting Trading Bot...
[OK] Trading bot is already running
  Status: Up 2 hours

[STEP 4/6] Checking Bot Health...
[OK] Bot is healthy and running
  Sentiment signals loaded: 166
  Trading pairs: 3

[STEP 5/6] System Status Overview...
  --- Trading Bot Container ---
    Name: trading-bot-app
    Status: Up 2 hours
    Ports: 0.0.0.0:8080->8080/tcp

  --- Data Files ---
[OK] Sentiment data available
    Last modified: 2025-10-28 09:15:30
    Signals: 166

[STEP 6/6] Launching Trading Monitor...
```

### Then the monitor displays:
```
================================================================================
  [*] CRYPTOBOY TRADING MONITOR - VOIDCAT RDC
================================================================================
  [BALANCE] | Starting: 1000.00 USDT | Current: 1005.14 USDT | P/L: + +5.14 USDT

  [STATS] OVERALL STATISTICS
  Total Trades: 5
  Win Rate: * 80.00%
  Total Profit: + +5.14 USDT

  [ACTIVITY] RECENT TRADE UPDATES (Last 2 Hours)
  [09:29:32] ENTERED ETH/USDT | Rate: $2720.00 | Stake: 50.00 USDT
  [09:24:32] EXITED  SOL/USDT | P/L: + +2.55% (+1.28 USDT) | Reason: roi

  [NEWS] RECENT SENTIMENT HEADLINES
  + BULLISH | Coinbase Prime and Figment expand institutional staking...
```

---

## 🛠️ Quick Commands After Launch

The launcher shows these commands when you exit:

### View Bot Logs:
```bash
docker logs trading-bot-app --tail 50
```

### Restart Bot:
```bash
docker restart trading-bot-app
```

### Stop Bot:
```bash
docker stop trading-bot-app
```

### Monitor Only:
```bash
start_monitor.bat
```

### Full System Restart:
```bash
start_cryptoboy.bat
# or
.\start_cryptoboy.ps1
```

---

## 💡 Pro Tips

### Run from Anywhere:
Create the desktop shortcut to launch from anywhere:
```bash
create_desktop_shortcut.bat
```

### Check Status Quickly:
```bash
check_status.bat
```

### First Time Setup:
If this is your first run:
1. Make sure Docker Desktop is running
2. Run the data pipeline first:
   ```bash
   python scripts/run_data_pipeline.py
   ```
3. Then launch the system

### Troubleshooting:
- **Docker not running**: Start Docker Desktop first
- **Container won't start**: Run `docker-compose down` then restart
- **Python not found**: Make sure Python is in your PATH
- **Monitor shows no data**: Run `python scripts/insert_test_trades.py`

---

## 📁 File Locations

All launcher files are in the project root:

```
D:\Development\CryptoBoy\Fictional-CryptoBoy\
├── start_cryptoboy.bat          ← CMD/PowerShell launcher
├── start_cryptoboy.ps1          ← PowerShell launcher (enhanced)
├── create_desktop_shortcut.bat ← Desktop shortcut creator
├── start_monitor.bat            ← Monitor only (no bot start)
└── check_status.bat             ← Quick status check
```

---

## 🎨 Features Summary

✅ **Automatic System Startup**
- Checks all dependencies
- Starts bot if needed
- Launches monitor automatically

✅ **Health Monitoring**
- Verifies bot status
- Shows loaded data
- Displays container info

✅ **Live Dashboard**
- Real-time balance
- Trade notifications
- Activity feed
- Sentiment headlines

✅ **Easy Management**
- One-click launch
- Desktop shortcut option
- Clean exit messages
- Quick command reference

---

**VoidCat RDC - Excellence in Automated Trading** 🚀
