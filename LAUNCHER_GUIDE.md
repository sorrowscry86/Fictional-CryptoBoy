# CryptoBoy System Launcher - Quick Reference

**VoidCat RDC - Microservice Architecture Control System**

## 🚀 Launch Options

### Primary Launcher (Recommended)
```bash
launcher.bat
```
**Interactive menu with all system operations**

### Direct System Start
```bash
start_cryptoboy.bat
```
**Mode Selection:**
1. Microservice Architecture (Full Stack)
2. Legacy Monolithic Mode
3. Status Check Only

### PowerShell Enhanced Start
```powershell
.\start_cryptoboy.ps1
```
**Advanced features with detailed health checks**

### Desktop Shortcut
1. Run: `create_desktop_shortcut.bat`
2. Double-click: **CryptoBoy Trading System**

---

## 📋 Microservice Startup Sequence

### Automatic Launch (Mode 1):

**Step 1: Docker Check** ✓
- Verifies Docker Desktop is running
- Displays Docker version

**Step 2: Environment Variables** ✓
- Checks RABBITMQ_USER and RABBITMQ_PASS
- Uses defaults if not set (admin/cryptoboy_secret)

**Step 3: Infrastructure Services** ✓
- Starts RabbitMQ (message broker)
- Starts Redis (cache server)
- Health check verification (8 seconds)

**Step 4: Microservices Launch** ✓
- Market Data Streamer (CCXT WebSocket)
- News Poller (RSS aggregation)
- Sentiment Processor (LLM analysis)
- Signal Cacher (Redis writer)
- Initialization wait (5 seconds)

**Step 5: Trading Bot** ✓
- Freqtrade container startup
- Strategy loading from Redis cache
- Initialization (5 seconds)

**Step 6: Health Check** ✓
- All service status verification
- RabbitMQ queue inspection
- Redis cache validation

**Step 7: Monitoring Dashboard** ✓
- Auto-launches real-time monitor
- 15-second refresh interval
- Press Ctrl+C to exit (services keep running)

---

## 🎯 Complete Batch File Reference

### System Control
| File | Purpose | Use When |
|------|---------|----------|
| **launcher.bat** | Main interactive menu | General operation, new users |
| **start_cryptoboy.bat** | Start trading system | First launch or after shutdown |
| **stop_cryptoboy.bat** | Stop all services | End of day, maintenance |
| **restart_service.bat** | Restart individual service | Service errors, updates |
| **check_status.bat** | Quick health check | Verify system state |

### Monitoring & Logs
| File | Purpose | Use When |
|------|---------|----------|
| **start_monitor.bat** | Launch dashboard | Monitor active trading |
| **view_logs.bat** | Tail service logs | Debug issues, track events |

### Utilities
| File | Purpose | Use When |
|------|---------|----------|
| **add_to_startup.bat** | Auto-start on Windows login | Production deployment |
| **remove_from_startup.bat** | Remove auto-start | Development mode |
| **create_desktop_shortcut.bat** | Create desktop icon | Easy access |

---

## 📊 Monitor Dashboard Features

### Real-Time Display:
```
================================================================================
  [*] CRYPTOBOY TRADING MONITOR - VOIDCAT RDC
  Microservice Architecture - Redis Cache Mode
================================================================================
  [BALANCE] | Starting: 1000.00 USDT | Current: 1005.14 USDT | P/L: + +5.14 USDT
  Available: 950.00 USDT | Locked in Trades: 55.14 USDT

  [STATS] OVERALL STATISTICS
  Total Trades:      5
  Winning Trades:    + 4
  Losing Trades:     - 1
  Win Rate:          * 80.00%
  Total Profit:      !+ +5.14 USDT
  Avg Profit:        1.03%
  Best Trade:        + +2.55%
  Worst Trade:       - -0.80%

  [CHART] PERFORMANCE BY PAIR
  BTC/USDT     | Trades:   2 | Win Rate:  50.0% | P/L: + +2.10 USDT
  ETH/USDT     | Trades:   2 | Win Rate: 100.0% | P/L: + +4.20 USDT
  SOL/USDT     | Trades:   1 | Win Rate: 100.0% | P/L: + +1.28 USDT

  [OPEN] OPEN TRADES (1)
  ID   5 | ETH/USDT     | Entry: $2720.00 | Amount: 0.0184 | Stake: 50.00 USDT | Duration: 2.3h

  [ACTIVITY] RECENT TRADE UPDATES (Last 2 Hours)
  [09:29:32] ENTERED ETH/USDT | Rate: $2720.00 | Stake: 50.00 USDT | ID: 5
  [09:24:32] EXITED  SOL/USDT | P/L: + +2.55% (+1.28 USDT) | Reason: roi

  [NEWS] RECENT SENTIMENT HEADLINES
  + BULLISH | Bitcoin ETF sees record inflows as institutional adoption surges
  - BEARISH | SEC announces new crypto regulation framework for 2026
  = NEUTRAL | Ethereum developers target Q2 for next major upgrade
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
