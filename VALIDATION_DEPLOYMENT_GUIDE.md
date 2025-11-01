# Coinbase Integration Validation - Production Deployment Guide

**VoidCat RDC - CryptoBoy Trading System**  
**Guide Version**: 1.0  
**Date**: November 1, 2025  
**Author**: Wykeve Freeman (Sorrow Eternal)

---

## Overview

This guide provides step-by-step instructions for validating the Coinbase/Binance Exchange API integration in a production environment. The validation script has been tested in CI/CD but requires a production environment with network access to cryptocurrency exchanges for full testing.

---

## Prerequisites

### System Requirements
- Docker Desktop installed and running
- Docker Compose V2 (v2.38.2 or higher)
- Python 3.10+ (for local testing)
- Network access to cryptocurrency exchange APIs
- Minimum 8GB RAM (for all 7 microservices)

### Required Files
- `.env` file configured with API credentials
- `config/live_config.json` properly configured
- All Docker images built successfully

---

## Step 1: Update Configuration (CRITICAL)

The exchange configuration has been updated from deprecated "coinbase" to "binance". Verify this change:

### Check `config/live_config.json`

```json
{
  "exchange": {
    "name": "binance",  // ✓ Updated (was "coinbase")
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_API_SECRET}",
    "pair_whitelist": [
      "BTC/USDT",
      "ETH/USDT",
      "SOL/USDT",
      "XRP/USDT",
      "ADA/USDT"
    ]
  }
}
```

### Create `.env` File

If not already present, create `.env` in the project root:

```bash
# Exchange API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# RabbitMQ Configuration
RABBITMQ_USER=admin
RABBITMQ_PASS=cryptoboy_secret

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Trading Configuration
DRY_RUN=true  # ALWAYS START WITH PAPER TRADING
STAKE_CURRENCY=USDT
STAKE_AMOUNT=50
MAX_OPEN_TRADES=3

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# API Server
API_USERNAME=admin
API_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_jwt_secret_key

# LLM Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=phi3:mini
```

**SECURITY NOTE**: Never commit the `.env` file to Git!

---

## Step 2: Verify API Keys

Run the API key verification script:

```bash
python scripts/verify_api_keys.py
```

Expected output:
```
✓ .env file found
✓ Environment variables loaded
✓ API Key: abc1...xyz9
✓ API Secret: def2...uvw8
✓ Successfully connected to Binance API
✓ Account has trading permissions
```

If this fails, verify:
1. API keys are correct
2. Binance account is active
3. API keys have appropriate permissions
4. IP whitelist includes your server IP (if configured)

---

## Step 3: Start Microservices Stack

Start all 7 services using Docker Compose:

```bash
# Navigate to project directory
cd /path/to/Fictional-CryptoBoy

# Set environment variables
export RABBITMQ_USER=admin
export RABBITMQ_PASS=cryptoboy_secret

# Start services
docker compose -f docker-compose.production.yml up -d

# Wait for services to start (60 seconds)
sleep 60
```

### Verify All Services Are Running

```bash
docker compose -f docker-compose.production.yml ps
```

Expected output:
```
NAME                          STATUS
trading-rabbitmq-prod         Up 30 seconds (healthy)
trading-redis-prod            Up 30 seconds (healthy)
trading-bot-ollama-prod       Up 30 seconds (healthy)
trading-market-streamer       Up 30 seconds
trading-news-poller           Up 30 seconds
trading-sentiment-processor   Up 30 seconds
trading-signal-cacher         Up 30 seconds
trading-bot-app               Up 30 seconds (healthy)
```

If any service is not running:
```bash
# Check logs for specific service
docker compose -f docker-compose.production.yml logs [service-name]

# Restart specific service
docker compose -f docker-compose.production.yml restart [service-name]
```

---

## Step 4: Run Coinbase Integration Validation

Execute the comprehensive validation script:

```bash
python scripts/validate_coinbase_integration.py
```

### Expected Output

The script will run 4 tests:

#### Test 1: Fetch Live Market Data
```
Testing BTC/USDT...
✓ BTC/USDT: $67,234.50 (bid: $67,234.00, ask: $67,235.00, latency: 145.23ms)

Testing ETH/USDT...
✓ ETH/USDT: $3,456.78 (bid: $3,456.50, ask: $3,457.00, latency: 132.45ms)

Testing SOL/USDT...
✓ SOL/USDT: $178.90 (bid: $178.88, ask: $178.92, latency: 128.67ms)

Testing XRP/USDT...
✓ XRP/USDT: $0.5678 (bid: $0.5677, ask: $0.5679, latency: 135.12ms)

Testing ADA/USDT...
✓ ADA/USDT: $0.4123 (bid: $0.4122, ask: $0.4124, latency: 140.34ms)

────────────────────────────────────────────────────────
ℹ Ticker Success Rate: 100.0%
ℹ OHLCV Success Rate: 100.0%
ℹ Order Book Success Rate: 100.0%
ℹ Average Latency: 136.36ms
✓ Test 1: PASSED
```

**Success Criteria**: 
- ✓ Ticker success rate ≥ 80%
- ✓ Average latency < 10,000ms (10 seconds)
- ✓ All 5 pairs return valid prices

#### Test 2: Verify WebSocket Connection
```
✓ Market streamer container is running
✓ WebSocket connection detected in logs
✓ Test 2: PASSED
```

**Success Criteria**:
- ✓ Container `trading-market-streamer` is running
- ✓ Logs show "connected" or "subscribed" messages

#### Test 3: Check Database
```
✓ Total trades in database: 0
✓ Test 3: PASSED
```

**Success Criteria**:
- ✓ Database is accessible
- ✓ Trades table exists (count may be 0 for fresh install)

#### Test 4: Verify Service Health
```
✓ trading-rabbitmq-prod: running (healthy)
✓ trading-redis-prod: running (healthy)
✓ trading-bot-ollama-prod: running (healthy)
✓ trading-market-streamer: running
✓ trading-news-poller: running
✓ trading-sentiment-processor: running
✓ trading-signal-cacher: running
✓ trading-bot-app: running (healthy)

Services running: 8/8 (100.0%)
✓ Test 4: PASSED - All services healthy
```

**Success Criteria**:
- ✓ All 7-8 services running
- ✓ Health percentage = 100%
- ✓ No containers in "Exited" or "Restarting" state

---

## Step 5: Review Generated Reports

The validation script generates two reports:

### 1. `COINBASE_VALIDATION_REPORT.md`
- Detailed test results
- Success/failure status for each pair
- Latency measurements
- Service health status
- Recommendations

### 2. `coinbase_validation_results.json`
- Machine-readable test data
- Timestamps for all tests
- Raw API responses
- Error details (if any)

Review both files:

```bash
# View markdown report
cat COINBASE_VALIDATION_REPORT.md

# View JSON results
cat coinbase_validation_results.json | python -m json.tool
```

---

## Step 6: Verify Success Criteria

All 6 success criteria from Task 1.2 must be met:

| Criterion | Check |
|-----------|-------|
| ✓ All 5 pairs fetch live ticker data (within 10 seconds) | Test 1 passed, latency < 10s |
| ✓ Market streamer connected and receiving data | Test 2 passed, WebSocket active |
| ✓ Candles stored in SQLite (< 2.5% missing data) | OHLCV success rate ≥ 97.5% |
| ✓ Order placement succeeds (dry-run mode) | Trading bot running in paper mode |
| ✓ No errors in docker logs | Check all service logs |
| ✓ All 7 services showing "healthy" status | Test 4 passed, 100% health |

### Check Docker Logs for Errors

```bash
# Check all services
docker compose -f docker-compose.production.yml logs --tail 50 | grep -i "error\|fatal\|exception"

# If errors found, check specific service
docker compose -f docker-compose.production.yml logs [service-name] --tail 100
```

**Expected**: No critical errors. Some warnings are acceptable during startup.

---

## Step 7: Monitor Paper Trading (7 Days)

After validation passes, monitor the system in paper trading mode for 7 days:

```bash
# Start monitoring dashboard
python scripts/monitor_trading.py

# Or use batch file (Windows)
start_monitor.bat
```

### What to Monitor

1. **Trade Execution**
   - Paper trades being executed
   - Entry/exit signals triggered
   - Sentiment scores influencing decisions

2. **Service Health**
   - All containers remain running
   - No memory leaks (monitor RAM usage)
   - No excessive CPU usage

3. **Data Quality**
   - News articles being collected
   - Sentiment scores being cached in Redis
   - Market data streaming continuously

4. **Performance Metrics** (from backtesting/monitoring)
   - Sharpe Ratio > 1.0
   - Max Drawdown < 20%
   - Win Rate > 50%
   - Profit Factor > 1.5

### Daily Checks

```bash
# Check service status
docker compose -f docker-compose.production.yml ps

# Check Redis sentiment cache
docker exec trading-redis-prod redis-cli KEYS "sentiment:*"
docker exec trading-redis-prod redis-cli HGETALL "sentiment:BTC/USDT"

# Check RabbitMQ queue depth
docker exec trading-rabbitmq-prod rabbitmqctl list_queues

# Check trading bot logs
docker logs trading-bot-app --tail 50 -f
```

---

## Troubleshooting

### Issue: API Rate Limits

**Symptoms**:
```
✗ BTC/USDT: Exchange error: Rate limit exceeded
```

**Solution**:
1. Reduce polling frequency in market streamer
2. Enable `enableRateLimit: true` in exchange config
3. Implement exponential backoff

### Issue: WebSocket Disconnections

**Symptoms**:
```
⚠ WebSocket disconnected, reconnecting...
```

**Solution**:
1. Check network stability
2. Verify exchange WebSocket endpoint is accessible
3. Increase reconnection timeout
4. Check firewall rules

### Issue: Sentiment Scores All Zero

**Symptoms**:
```
ℹ Sentiment score: 0.0 (stale)
```

**Solution**:
1. Verify FinBERT model loaded correctly
2. Check news-poller is collecting articles
3. Verify sentiment-processor is processing queue
4. Check RabbitMQ queues for backlog

### Issue: Docker Containers Exiting

**Symptoms**:
```
trading-market-streamer   Exited (1) 5 seconds ago
```

**Solution**:
1. Check container logs: `docker logs trading-market-streamer`
2. Verify environment variables are set correctly
3. Ensure dependencies (RabbitMQ, Redis) are running first
4. Rebuild container if code was updated

---

## Security Checklist

Before deploying to production:

- [ ] ✓ API keys not committed to repository
- [ ] ✓ `.env` file in `.gitignore`
- [ ] ✓ `DRY_RUN=true` for initial testing
- [ ] ✓ 2FA enabled on exchange account
- [ ] ✓ IP whitelisting configured on exchange (if possible)
- [ ] ✓ Read-only API keys initially (no withdrawal permissions)
- [ ] ✓ Telegram notifications configured
- [ ] ✓ Strong API server password
- [ ] ✓ JWT secret key is random and secure
- [ ] ✓ Firewall rules configured (only necessary ports open)

---

## Next Steps After Validation

1. **Week 1-2**: Paper trading monitoring
2. **Week 3**: Performance analysis and parameter tuning
3. **Week 4**: Final backtest with tuned parameters
4. **Week 5**: Decision point - proceed to live trading or continue optimization

**ONLY AFTER**:
- ✓ 7+ days successful paper trading
- ✓ Sharpe ratio > 1.0
- ✓ Max drawdown < 20%
- ✓ All services stable (no crashes)
- ✓ Team approval

**THEN**: Set `DRY_RUN=false` and restart trading bot

---

## Support

**VoidCat RDC**  
**Developer**: Wykeve Freeman (Sorrow Eternal)  
**Email**: SorrowsCry86@voidcat.org  
**GitHub**: https://github.com/sorrowscry86/Fictional-CryptoBoy  
**Support**: CashApp $WykeveTF

---

## Appendix: Command Reference

```bash
# Start services
docker compose -f docker-compose.production.yml up -d

# Stop services
docker compose -f docker-compose.production.yml down

# View logs
docker compose -f docker-compose.production.yml logs -f

# Restart service
docker compose -f docker-compose.production.yml restart [service-name]

# Rebuild service
docker compose -f docker-compose.production.yml build [service-name]
docker compose -f docker-compose.production.yml up -d [service-name]

# Check service health
docker compose -f docker-compose.production.yml ps

# Execute command in container
docker exec [container-name] [command]

# Check Redis keys
docker exec trading-redis-prod redis-cli KEYS "*"

# Check RabbitMQ queues
docker exec trading-rabbitmq-prod rabbitmqctl list_queues
```

---

**NO SIMULATIONS LAW**: This guide is based on actual system architecture and real validation procedures. Follow these steps exactly as written for reliable results.
