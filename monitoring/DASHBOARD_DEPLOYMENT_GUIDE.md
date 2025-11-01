# 📊 CryptoBoy Monitoring Dashboard - Deployment Guide

**Project**: CryptoBoy Real-Time Monitoring Dashboard  
**Organization**: VoidCat RDC  
**Developer**: Wykeve Freeman (Sorrow Eternal)  
**Last Updated**: November 1, 2025  

---

## 🎯 Overview

The CryptoBoy Monitoring Dashboard provides real-time visibility into all 8 microservices in the production trading stack. It displays service health, sentiment cache data, RabbitMQ queue depths, trading performance, and automatic alerts for system issues.

### Architecture

- **Backend**: Python aiohttp WebSocket server (`monitoring/dashboard_service.py`)
- **Frontend**: Responsive HTML/CSS/JavaScript dashboard (`monitoring/dashboard.html`)
- **Update Interval**: 5 seconds (WebSocket broadcast)
- **Port**: 8081 (HTTP + WebSocket)
- **Container**: `trading-dashboard`

### Monitored Services (8 Total)

1. `trading-rabbitmq-prod` - Message broker
2. `trading-redis-prod` - Sentiment cache
3. `trading-bot-ollama-prod` - LLM fallback
4. `trading-market-streamer` - Exchange WebSocket
5. `trading-news-poller` - RSS feed aggregation
6. `trading-sentiment-processor` - FinBERT sentiment analysis
7. `trading-signal-cacher` - Redis cache writer
8. `trading-bot-app` - Freqtrade trading bot

---

## 🔧 Prerequisites

### System Requirements

- **Docker Compose**: V2 (installed with Docker Desktop)
- **Port Availability**: 8081 must be free
- **Docker Socket Access**: `/var/run/docker.sock` (for container stats)
- **Running Services**: At minimum, `redis` and `rabbitmq` must be healthy

### Environment Variables

The dashboard reads credentials from `.env`:

```bash
# Redis (REQUIRED)
REDIS_HOST=redis
REDIS_PORT=6379

# RabbitMQ (REQUIRED for queue metrics)
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=admin
RABBITMQ_PASS=cryptoboy_secret
```

**⚠️ Critical**: If `RABBITMQ_USER` or `RABBITMQ_PASS` are not set, the container will fail to start.

---

## 🚀 Deployment Steps

### 1. Build Dashboard Image

```bash
docker compose -f docker-compose.production.yml build dashboard
```

**Expected output**: 
- Build completes successfully
- Image tagged as `cryptoboy-voidcat-dashboard:latest`

### 2. Start Dashboard Service

```bash
docker compose -f docker-compose.production.yml up -d dashboard
```

**Expected output**:
```
✔ Container trading-rabbitmq-prod  Running
✔ Container trading-redis-prod     Running
✔ Container trading-dashboard      Started
```

### 3. Verify Service Started

```bash
docker logs trading-dashboard --tail 20
```

**Success indicators**:
```
2025-11-01 18:52:16 - dashboard-service - [INFO] - === VoidCat RDC - CryptoBoy Monitoring Dashboard ===
2025-11-01 18:52:16 - [INFO] - NO SIMULATIONS LAW: All metrics from real system state
2025-11-01 18:52:16 - [INFO] - Connected to Redis for metrics collection
2025-11-01 18:52:16 - [INFO] - Dashboard Metrics Collector initialized
2025-11-01 18:52:16 - [INFO] - Dashboard server initialized on port 8081
2025-11-01 18:52:16 - [INFO] - Starting dashboard server on http://0.0.0.0:8081
======== Running on http://0.0.0.0:8081 ========
```

### 4. Test HTTP Accessibility

**PowerShell**:
```powershell
Invoke-WebRequest -Uri http://localhost:8081 -Method Head | Select-Object StatusCode
```

**Expected**: `StatusCode: 200`

**Linux/Mac**:
```bash
curl -I http://localhost:8081
```

**Expected**: `HTTP/1.1 200 OK`

### 5. Access Dashboard UI

Open browser to: **http://localhost:8081**

**Expected UI elements**:
- ✅ Header: "VoidCat RDC - CryptoBoy Monitoring Dashboard"
- ✅ Connection status indicator (top-right): "Connected" (green)
- ✅ Status bar: System health %, running services count, total trades, win rate
- ✅ 4 metric cards:
  - **Docker Services** (8 container states)
  - **Sentiment Cache** (5 trading pairs with bullish/bearish indicators)
  - **RabbitMQ Queues** (message counts)
  - **Trading Metrics** (trades, profit, win rate)

---

## 🔍 Verifying Real-Time Metrics

### WebSocket Connection Test

1. Open browser DevTools (F12)
2. Navigate to **Console** tab
3. Look for log: `WebSocket connected to ws://<host>/ws`
4. Watch for updates every 5 seconds: `Metrics updated at <timestamp>`

### Docker Container Stats

Check that all 8 services display with correct states:

**Expected states**:
- `running` (green) - Service healthy
- `restarting` (yellow) - Service recovering
- `stopped` (red) - Service offline

**Test**: Stop a non-critical service:
```bash
docker stop trading-signal-cacher
```

**Expected**: Dashboard shows service as "stopped" within 5 seconds, alert appears: "Service health at 87.5%"

**Restore**:
```bash
docker start trading-signal-cacher
```

### Redis Sentiment Cache

**Expected display**:
- 5 trading pairs: BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, MATIC/USDT
- Sentiment scores: -1.0 to +1.0
- Color coding:
  - **Green** (bullish): score > 0.3
  - **Red** (bearish): score < -0.3
  - **Gray** (neutral): -0.3 to +0.3

**Test staleness**:
If sentiment timestamp is >4 hours old, dashboard shows:
- Score text turns orange
- Alert: "Stale sentiment detected for <PAIR>"

### RabbitMQ Queue Monitoring

**Expected queues**:
- `raw_market_data` - WebSocket market data
- `raw_news_data` - RSS feed articles
- `sentiment_signals_queue` - Processed sentiment scores

**Normal state**: Message counts 0-100 (processing active)

**Alert trigger**: If any queue has >1000 messages:
- Queue row turns red
- Alert: "High queue backlog detected: <QUEUE_NAME> has <COUNT> messages"

### Trading Metrics

**Expected data from SQLite database** (`user_data/tradesv3.dryrun.sqlite`):
- **Total Trades**: Cumulative count since bot started
- **24h Trades**: Trades opened in last 24 hours
- **Open/Closed Trades**: Current positions vs. completed
- **Average Profit %**: Mean profit per trade
- **Win Rate %**: Winning trades / total trades
- **Wins/Losses**: Count breakdown

**Note**: During paper trading, profits will be simulated. Only mark Task 2.1 complete when win rate >40% over 7 days.

---

## 🚨 Alert System Reference

### Alert Severity Levels

| Severity | Color | Trigger Condition |
|----------|-------|-------------------|
| **Warning** | Yellow | Sentiment stale (4-6 hours), queue backlog (1000-5000 msgs) |
| **Critical** | Red | Service stopped, sentiment stale (>6 hours), queue backlog (>5000 msgs) |

### Alert Types

#### 1. Service Health Alerts

**Trigger**: Any Docker container not in "running" state

**Message**: `"Service health at <X>% - some services not running"`

**Resolution**:
- Check container logs: `docker logs <container_name>`
- Restart service: `docker compose -f docker-compose.production.yml restart <service_name>`
- If repeated failures, check RabbitMQ credentials and Redis connectivity

#### 2. Sentiment Staleness Alerts

**Trigger**: Sentiment data older than 4 hours (configurable)

**Message**: `"Stale sentiment detected for <PAIR> (age: <X> hours)"`

**Likely Causes**:
- News poller service stopped
- Sentiment processor crashed
- Signal cacher not writing to Redis

**Resolution**:
1. Check news poller: `docker logs trading-news-poller`
2. Check sentiment processor: `docker logs trading-sentiment-processor`
3. Check signal cacher: `docker logs trading-signal-cacher`
4. Verify RabbitMQ queues: `docker exec trading-rabbitmq-prod rabbitmqctl list_queues`

#### 3. Queue Backlog Alerts

**Trigger**: RabbitMQ queue depth >1000 messages

**Message**: `"High queue backlog detected: <QUEUE_NAME> has <COUNT> messages"`

**Likely Causes**:
- Consumer service crashed (sentiment-processor or signal-cacher)
- Processing slower than ingestion rate
- FinBERT model overloaded

**Resolution**:
1. Restart consumer service: `docker compose restart sentiment-processor`
2. Check CPU/memory: `docker stats`
3. If persistent, consider scaling sentiment processor (future enhancement)

#### 4. High Latency Alerts

**Trigger**: Metric collection time >5000ms (5 seconds)

**Message**: `"High latency detected: metrics collection took <X>ms"`

**Likely Causes**:
- Docker socket slow response
- Redis queries timing out
- SQLite database locked

**Resolution**:
- Check system load: `docker stats`
- Verify no disk I/O bottlenecks
- Restart dashboard service if persistent

---

## 🛠️ Troubleshooting

### Issue: Container Fails to Start

**Symptoms**:
```
ValueError: '/app/monitoring/static' does not exist
```

**Cause**: Old code version looking for static directory

**Fix**:
```bash
# Rebuild with latest code
docker compose -f docker-compose.production.yml build dashboard
docker compose -f docker-compose.production.yml up -d dashboard
```

---

### Issue: WebSocket Connection Refused

**Symptoms**: Browser console shows `WebSocket connection failed`

**Check 1 - Dashboard running**:
```bash
docker ps | grep trading-dashboard
```

**Expected**: Container status "Up X seconds"

**Check 2 - Port accessible**:
```powershell
Test-NetConnection -ComputerName localhost -Port 8081
```

**Expected**: `TcpTestSucceeded: True`

**Fix**:
- Restart dashboard: `docker compose restart dashboard`
- Check firewall rules (Windows Defender may block port 8081)

---

### Issue: All Services Show "Unknown" State

**Symptoms**: Dashboard shows all containers with gray status

**Cause**: Docker socket permission denied

**Check**:
```bash
docker logs trading-dashboard | grep "Permission denied"
```

**Fix**:
- Verify Docker socket mounted: 
  ```bash
  docker inspect trading-dashboard | grep "/var/run/docker.sock"
  ```
- On Linux, add dashboard to docker group (container rebuild may be needed)

---

### Issue: Redis Metrics Show "N/A"

**Symptoms**: Sentiment cache card displays no data

**Check 1 - Redis accessible**:
```bash
docker exec trading-redis-prod redis-cli PING
```

**Expected**: `PONG`

**Check 2 - Sentiment keys exist**:
```bash
docker exec trading-redis-prod redis-cli KEYS "sentiment:*"
```

**Expected**: List of 5 keys (one per trading pair)

**Fix**:
- If keys missing, signal-cacher not populating Redis
- Restart cacher: `docker compose restart signal-cacher`
- Check cacher logs: `docker logs trading-signal-cacher --tail 50`

---

### Issue: RabbitMQ Metrics Show "Error"

**Symptoms**: Queue metrics card displays error message

**Cause**: RabbitMQ credentials incorrect or management plugin disabled

**Check 1 - RabbitMQ healthy**:
```bash
docker exec trading-rabbitmq-prod rabbitmqctl status
```

**Expected**: Node running, no errors

**Check 2 - Management plugin enabled**:
```bash
docker exec trading-rabbitmq-prod rabbitmq-plugins list
```

**Expected**: `[E*] rabbitmq_management` (enabled)

**Fix**:
- Enable management: 
  ```bash
  docker exec trading-rabbitmq-prod rabbitmq-plugins enable rabbitmq_management
  ```
- Verify credentials in `.env` match RabbitMQ setup
- Restart dashboard: `docker compose restart dashboard`

---

### Issue: Trading Metrics Show 0 Trades

**Symptoms**: All trading stats display 0 or "N/A"

**Cause**: Paper trading bot not started or no trades executed yet

**Check 1 - Trading bot running**:
```bash
docker logs trading-bot-app --tail 30
```

**Expected**: Freqtrade logs showing strategy execution

**Check 2 - Database exists**:
```bash
ls -l user_data/tradesv3.dryrun.sqlite
```

**Expected**: File exists with size >0 bytes

**Check 3 - Sentiment scores high enough**:
- Dashboard sentiment cache card should show at least one pair >0.7 (bullish)
- If all scores <0.7, bot won't enter trades (by design)

**Fix**:
- This is normal during paper trading warm-up phase
- Trades will appear when sentiment scores exceed entry threshold (0.7)
- Monitor for 24-48 hours to see first trades

---

## 📝 Configuration Options

### Customizing Alert Thresholds

Edit `monitoring/dashboard_service.py`:

```python
# Line ~270 - _generate_alerts() method
sentiment_stale_hours = 4  # Change to 2 or 6 hours
queue_backlog_threshold = 1000  # Change to 500 or 2000
high_latency_ms = 5000  # Change to 3000 or 10000
```

**After editing**: Rebuild and restart dashboard service

### Changing Broadcast Interval

Default: 5 seconds

Edit `monitoring/dashboard_service.py`:

```python
# Line ~445 - metrics_broadcast_loop() method
await asyncio.sleep(5)  # Change to 10 for slower updates (less CPU)
```

### Adding Trading Pairs

Edit `monitoring/dashboard_service.py`:

```python
# Line ~133 - collect_redis_metrics() method
trading_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'MATIC/USDT']
# Add more: 'DOGE/USDT', 'XRP/USDT', etc.
```

**Also update** `config/live_config.json` `pair_whitelist` to match.

---

## 🔐 Security Considerations

### Docker Socket Access

**Risk**: Dashboard container has access to `/var/run/docker.sock`, which allows Docker API operations.

**Mitigation**:
- Volume mounted as **read-only** (`:ro` flag)
- Dashboard code only uses `docker compose ps` for stats (no create/delete/exec operations)
- Review `dashboard_service.py` code to verify no privileged operations

### RabbitMQ Credentials

**Risk**: `.env` file contains plaintext RabbitMQ password

**Mitigation**:
- `.env` excluded from version control (in `.gitignore`)
- Use strong passwords: `RABBITMQ_PASS=<complex_random_string>`
- Rotate credentials quarterly

### Public Exposure

**Risk**: Dashboard port 8081 may be accessible from network

**Default**: Bound to `0.0.0.0` (all interfaces)

**Production Fix** - Bind to localhost only:

Edit `docker-compose.production.yml`:

```yaml
ports:
  - "127.0.0.1:8081:8081"  # Localhost only
```

**Access remotely**: Use SSH tunnel:
```bash
ssh -L 8081:localhost:8081 user@cryptoboy-server
```

---

## 📊 Monitoring the Monitor

### Dashboard Health Check

**Automated check** (every 5 minutes):
```bash
# Add to crontab or Task Scheduler
*/5 * * * * curl -f http://localhost:8081/metrics || docker restart trading-dashboard
```

### Resource Usage

**CPU/Memory baseline**:
```bash
docker stats trading-dashboard --no-stream
```

**Expected**:
- CPU: 1-5% (5% spike during metric collection)
- Memory: 50-100 MB

**Alert threshold**: CPU >20% sustained, Memory >200 MB

### Log Monitoring

**Watch for errors**:
```bash
docker logs trading-dashboard -f | grep -i error
```

**Common errors**:
- `ConnectionRefusedError` - Redis/RabbitMQ down
- `sqlite3.OperationalError` - Database locked (transient, normal)
- `asyncio.TimeoutError` - Metric collection slow (check Docker stats)

---

## 🚦 Production Readiness Checklist

Before considering Task 2.2 complete:

- [x] Dashboard container builds successfully
- [x] Dashboard starts without errors
- [x] HTTP endpoint returns 200 OK
- [x] WebSocket connections working
- [x] All 8 Docker services display with correct states
- [x] Redis sentiment cache populates with data
- [x] RabbitMQ queue metrics displaying
- [ ] Trading metrics populate after first trade (depends on Task 2.1 completion)
- [x] Alerts appear when service stopped (tested)
- [ ] 24-hour uptime test completed (dashboard runs continuously)
- [ ] Deployment guide created and verified

---

## 📞 Support & Contact

**VoidCat RDC**
- **Developer**: Wykeve Freeman (Sorrow Eternal)
- **Email**: SorrowsCry86@voidcat.org
- **GitHub**: @sorrowscry86
- **Support Development**: CashApp $WykeveTF
- **Project**: CryptoBoy (Fictional-CryptoBoy repository)

**Resources**:
- GitHub Issues: Bug reports and feature requests
- Documentation: Full guides in `docs/`
- Monitoring Guide: This file (`monitoring/DASHBOARD_DEPLOYMENT_GUIDE.md`)

---

## 🔄 Next Steps

After successful dashboard deployment:

1. **Continue Task 2.1 Monitoring** (Paper Trading Baseline)
   - Check dashboard daily for first trades
   - Monitor sentiment scores trending toward >0.7
   - Document win rate progress (target >40% over 7 days)
   - **Gate Review**: Nov 7, 2025

2. **Start Task 2.3** (Stress Test All Services - 1.5 hours)
   - Use dashboard to monitor service health during tests
   - Load test RabbitMQ with 10,000 messages
   - Verify dashboard alerts trigger correctly at thresholds
   - Document capacity limits discovered

3. **Optional Enhancements** (Future backlog)
   - Historical metrics charts (trading performance over time)
   - Telegram alert forwarding
   - CSV export functionality
   - Mobile-optimized responsive view
   - Authentication layer (login required)

---

**🔒 NO SIMULATIONS LAW COMPLIANCE**

This dashboard collects **100% real metrics from actual system state**:
- Docker stats: Real container states via `docker compose ps`
- Redis metrics: Actual sentiment scores via HGETALL commands
- RabbitMQ queues: Genuine message counts via rabbitmqctl
- Trading metrics: Real database queries against SQLite

**All data is verifiable, audit-traceable, and measured from production systems.**

---

**🚀 VoidCat RDC - Excellence in Every Line of Code**

*Monitoring Dashboard Deployment Guide - v1.0*  
*Last Updated: November 1, 2025*
