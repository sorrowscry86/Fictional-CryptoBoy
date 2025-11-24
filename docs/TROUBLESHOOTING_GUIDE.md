# CryptoBoy Troubleshooting Guide
**VoidCat RDC - Problem Diagnosis & Resolution**

This guide provides systematic troubleshooting for common failure modes in the CryptoBoy trading system.

---

## Table of Contents
1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Service Health Issues](#service-health-issues)
3. [Message Queue Problems](#message-queue-problems)
4. [Sentiment Analysis Failures](#sentiment-analysis-failures)
5. [Trading Bot Issues](#trading-bot-issues)
6. [Performance Problems](#performance-problems)
7. [Data Pipeline Failures](#data-pipeline-failures)

---

## Quick Diagnostic Commands

### Windows (Batch Files)

```bash
# Check all service status
check_status.bat

# View logs for all services
view_logs.bat

# Start monitoring dashboard
start_monitor.bat

# Full system restart
stop_cryptoboy.bat
start_cryptoboy.bat
```

### Docker Commands

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View logs for specific service
docker logs trading-sentiment-processor --tail 50 -f

# Check resource usage
docker stats --no-stream

# Restart all services
docker-compose -f docker-compose.production.yml restart
```

### Service Health Checks

```bash
# RabbitMQ
docker exec trading-rabbitmq-prod rabbitmqctl status
docker exec trading-rabbitmq-prod rabbitmqctl list_queues

# Redis
docker exec trading-redis-prod redis-cli PING
docker exec trading-redis-prod redis-cli KEYS "sentiment:*"

# Ollama (LLM backup)
curl http://localhost:11434/api/tags
```

---

## Service Health Issues

### Problem: Container Won't Start

**Symptoms**:
- Container exits immediately after start
- `docker ps` doesn't show container
- Exit code 1 or 137 in logs

**Diagnosis**:
```bash
# Check container logs
docker logs trading-sentiment-processor --tail 100

# Check exit code
docker inspect trading-sentiment-processor | grep "ExitCode"

# Check Docker resources
docker system df
```

**Common Causes & Solutions**:

**1. Environment Variables Missing**
```
Error: RABBITMQ_USER not set
```
**Solution**:
```bash
# Verify .env file exists
cat .env

# Ensure variables exported
export RABBITMQ_USER=admin
export RABBITMQ_PASS=cryptoboy_secret

# Restart with environment
docker-compose -f docker-compose.production.yml up -d
```

**2. Port Already in Use**
```
Error: bind: address already in use
```
**Solution**:
```bash
# Find process using port
netstat -ano | findstr :8080  # Windows
lsof -i :8080  # Linux/Mac

# Kill process or change port in docker-compose.production.yml
```

**3. Insufficient Memory**
```
Exit code 137 (OOM killed)
```
**Solution**:
```bash
# Increase Docker memory limit (Docker Desktop Settings)
# Or add memory limits to docker-compose.production.yml

services:
  sentiment-processor:
    deploy:
      resources:
        limits:
          memory: 4G
```

---

### Problem: Service Running but Unhealthy

**Symptoms**:
- Container status shows "unhealthy"
- Health check failures in logs

**Diagnosis**:
```bash
# Check health check definition
docker inspect trading-redis-prod | grep -A 10 "Healthcheck"

# View health check logs
docker inspect trading-redis-prod | grep -A 20 "Health"
```

**Common Causes & Solutions**:

**1. Redis Connection Failures**
```
Health check failed: connection refused
```
**Solution**:
```bash
# Verify Redis running
docker exec trading-redis-prod redis-cli PING

# Check port binding
docker port trading-redis-prod

# Restart Redis
docker-compose -f docker-compose.production.yml restart redis
```

**2. RabbitMQ Authentication**
```
Health check failed: ACCESS_REFUSED
```
**Solution**:
```bash
# Verify credentials
docker exec trading-rabbitmq-prod rabbitmqctl list_users

# Create admin user if missing
docker exec trading-rabbitmq-prod rabbitmqctl add_user admin cryptoboy_secret
docker exec trading-rabbitmq-prod rabbitmqctl set_user_tags admin administrator
docker exec trading-rabbitmq-prod rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
```

---

## Message Queue Problems

### Problem: Queue Backlog Growing

**Symptoms**:
- Message count increasing on RabbitMQ queue
- Consumer not processing messages
- Delayed sentiment updates

**Diagnosis**:
```bash
# Check queue depth
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages

# Check consumer status
docker exec trading-rabbitmq-prod rabbitmqctl list_consumers

# Monitor queue in real-time
watch -n 1 'docker exec trading-rabbitmq-prod rabbitmqctl list_queues'
```

**Example Output**:
```
Listing queues for vhost / ...
name                      messages
raw_news_data            0
sentiment_signals_queue  0
raw_market_data          1250  # PROBLEM: Growing backlog
```

**Solutions**:

**1. Consumer Not Running**
```bash
# Check if consumer container is running
docker ps | grep trading-sentiment-processor

# If not running, start it
docker-compose -f docker-compose.production.yml up -d sentiment-processor

# Check logs for startup errors
docker logs trading-sentiment-processor --tail 50
```

**2. Consumer Processing Too Slow**
```bash
# Increase prefetch count for parallel processing
# Edit services/sentiment_analyzer/sentiment_processor.py
# Change: prefetch_count=1  →  prefetch_count=10

# Rebuild and restart
docker-compose -f docker-compose.production.yml build sentiment-processor
docker-compose -f docker-compose.production.yml up -d sentiment-processor
```

**3. Poison Pill Message**
```
Error: Message validation failed repeatedly
```
**Solution**:
```bash
# Purge problematic queue (CAUTION: deletes all messages)
docker exec trading-rabbitmq-prod rabbitmqctl purge_queue raw_news_data

# Or manually inspect messages via Management UI
# http://localhost:15672 → Queues → raw_news_data → Get Messages
```

---

### Problem: Messages Not Being Published

**Symptoms**:
- Queue remains empty despite producer running
- No new sentiment data
- Producer logs show no errors

**Diagnosis**:
```bash
# Check producer logs
docker logs trading-news-poller --tail 50

# Verify queue exists
docker exec trading-rabbitmq-prod rabbitmqctl list_queues

# Check RabbitMQ connections
docker exec trading-rabbitmq-prod rabbitmqctl list_connections
```

**Common Causes & Solutions**:

**1. RabbitMQ Connection Lost**
```
ConnectionError: connection closed
```
**Solution**:
```bash
# Restart producer to reconnect
docker-compose -f docker-compose.production.yml restart news-poller

# Verify connection established
docker logs trading-news-poller | grep "Successfully connected"
```

**2. Message Validation Failing**
```
ValidationError: URL domain mismatch
```
**Solution**:
```bash
# Check producer logs for validation errors
docker logs trading-news-poller | grep "validation failed"

# Fix producer code or update schema in message_schemas.py
```

---

## Sentiment Analysis Failures

### Problem: All Sentiment Scores Are 0.0

**Symptoms**:
- Redis cache shows score: 0.0 for all pairs
- No variation in sentiment
- Trading bot won't enter trades

**Diagnosis**:
```bash
# Check Redis sentiment data
docker exec trading-redis-prod redis-cli HGETALL "sentiment:BTC/USDT"

# Check sentiment processor logs
docker logs trading-sentiment-processor | grep "Sentiment analysis"

# Verify FinBERT loaded
docker logs trading-sentiment-processor | grep "FinBERT"
```

**Common Causes & Solutions**:

**1. FinBERT Model Not Loaded**
```
Error: Failed to load FinBERT model
```
**Solution**:
```bash
# Check if transformers/torch installed
docker exec trading-sentiment-processor pip list | grep transformers

# If missing, rebuild container
docker-compose -f docker-compose.production.yml build sentiment-processor --no-cache
docker-compose -f docker-compose.production.yml up -d sentiment-processor
```

**2. Fallback to Ollama (Memory Issues)**
```
Warning: FinBERT initialization failed, using Ollama
```
**Solution**:
```bash
# Increase container memory
# Add to docker-compose.production.yml:
services:
  sentiment-processor:
    deploy:
      resources:
        limits:
          memory: 4G  # FinBERT needs ~2GB

# Restart
docker-compose -f docker-compose.production.yml up -d sentiment-processor
```

**3. All News is Neutral**
```
All sentiment scores between -0.1 and +0.1
```
**Solution**:
- This may be legitimate (slow news day)
- Verify with manual test:
```python
from llm.huggingface_sentiment import HuggingFaceFinancialSentiment
analyzer = HuggingFaceFinancialSentiment()
print(analyzer.analyze_sentiment("Bitcoin crashes 50%"))  # Should be very negative
print(analyzer.analyze_sentiment("Bitcoin surges to ATH"))  # Should be very positive
```

---

### Problem: Sentiment Updates Too Slow

**Symptoms**:
- Sentiment timestamp in Redis is hours old
- Strategy sees stale data
- Bot skips trades due to staleness

**Diagnosis**:
```bash
# Check last update time
docker exec trading-redis-prod redis-cli HGET "sentiment:BTC/USDT" timestamp

# Calculate age
echo "Last update: $(docker exec trading-redis-prod redis-cli HGET 'sentiment:BTC/USDT' timestamp)"
echo "Current time: $(date -u +%Y-%m-%dT%H:%M:%S)"

# Check news poller frequency
docker logs trading-news-poller | grep "polling cycle"
```

**Solutions**:

**1. Reduce Polling Interval**
```bash
# Edit .env
NEWS_POLL_INTERVAL=180  # 3 minutes instead of 5

# Restart news poller
docker-compose -f docker-compose.production.yml restart news-poller
```

**2. Sentiment Processor Bottleneck**
```bash
# Check processing speed
docker logs trading-sentiment-processor | grep "Sentiment analysis complete"

# If slow, increase batch size
# Edit services/sentiment_analyzer/sentiment_processor.py
# Increase prefetch_count for parallel processing
```

---

## Trading Bot Issues

### Problem: Bot Not Entering Trades

**Symptoms**:
- Bot running for hours/days with no trades
- Paper trading shows 0 trades
- All conditions seem met

**Diagnosis**:
```bash
# Check bot status
docker logs trading-bot-app --tail 50

# Check open trades
docker exec trading-bot-app freqtrade trades --config config/live_config.json

# Verify sentiment data
docker exec trading-redis-prod redis-cli HGETALL "sentiment:BTC/USDT"

# Check strategy conditions
docker exec trading-redis-prod redis-cli HGETALL "strategy_state:BTC/USDT"
```

**Common Causes & Solutions**:

**1. Sentiment Threshold Not Met**
```
Current sentiment: 0.35, Required: > 0.7
```
**Solution**:
- Wait for more bullish news (market is neutral)
- OR lower threshold in strategy (testing only):
```python
# strategies/llm_sentiment_strategy.py
sentiment_buy_threshold = 0.3  # Lowered from 0.7
```

**2. Technical Indicators Not Aligned**
```
Sentiment: 0.85 ✓
EMA(12) < EMA(26) ✗  # Downtrend
```
**Solution**:
- Use strategy state monitor to see blocking reasons:
```bash
python monitoring/strategy_monitor.py
```

**3. Max Open Trades Reached**
```
Max open trades: 3/3 reached
```
**Solution**:
```bash
# Check current trades
docker exec trading-bot-app freqtrade trades --config config/live_config.json

# Close trades manually (DRY_RUN only)
python monitoring/manual_trade_controller.py --force-sell <trade_id>
```

**4. Insufficient Balance**
```
Error: Insufficient balance for stake amount
```
**Solution**:
```bash
# Check balance
docker exec trading-bot-app freqtrade balance --config config/live_config.json

# Reduce stake amount in config/live_config.json
# Or increase starting capital in DRY_RUN mode
```

---

### Problem: Bot Enters Too Many Trades

**Symptoms**:
- Excessive trade frequency
- Max open trades always reached
- Poor risk management

**Diagnosis**:
```bash
# Check trade frequency
docker exec trading-bot-app freqtrade trades --config config/live_config.json | wc -l

# Check open trades
docker exec trading-bot-app freqtrade status --config config/live_config.json
```

**Solutions**:

**1. Sentiment Threshold Too Low**
```python
# Increase threshold in strategies/llm_sentiment_strategy.py
sentiment_buy_threshold = 0.8  # Raised from 0.7 (more conservative)
```

**2. Reduce Max Open Trades**
```json
// config/live_config.json
"max_open_trades": 2  // Reduced from 3
```

**3. Add Cooldown Period**
```python
# Add to strategy (custom implementation)
self.last_trade_time = {}
cooldown_minutes = 30

# In populate_entry_trend()
if pair in self.last_trade_time:
    if (current_time - self.last_trade_time[pair]).total_seconds() < cooldown_minutes * 60:
        return dataframe  # Skip entry
```

---

### Problem: Bot Stuck in Loss Position

**Symptoms**:
- Trade open for days with negative P&L
- Stop loss not triggering
- Trailing stop not working

**Diagnosis**:
```bash
# Check open trade details
docker logs trading-bot-app | grep "open trades"

# Manually close (DRY_RUN only)
python monitoring/manual_trade_controller.py --force-sell <trade_id>
```

**Solutions**:

**1. Verify Stop Loss Configuration**
```python
# strategies/llm_sentiment_strategy.py
stoploss = -0.03  # -3% stop loss

# Ensure not overridden
```

**2. Check Trailing Stop**
```python
trailing_stop = True
trailing_stop_positive = 0.01  # Activate at +1% profit
trailing_stop_positive_offset = 0.0
```

**3. Force Sell if Stuck** (DRY_RUN only)
```bash
# Get trade ID
docker exec trading-bot-app freqtrade status

# Force sell
curl -X POST http://localhost:8080/api/v1/forcesell \
  -u freqtrader: \
  -H "Content-Type: application/json" \
  -d '{"tradeid": 123}'
```

---

## Performance Problems

### Problem: High Memory Usage

**Symptoms**:
- Container OOM killed (exit code 137)
- System slowdown
- Swap usage high

**Diagnosis**:
```bash
# Check container memory
docker stats --no-stream

# Check system memory
free -h  # Linux
wmic OS get FreePhysicalMemory  # Windows

# Check specific service
docker stats trading-sentiment-processor --no-stream
```

**Solutions**:

**1. FinBERT Memory Usage**
```
sentiment-processor: 3.8 GB / 4 GB (95%)
```
**Solution**:
```bash
# Increase memory limit
# docker-compose.production.yml
services:
  sentiment-processor:
    deploy:
      resources:
        limits:
          memory: 6G  # Increased from 4G
```

**2. Redis Memory Bloat**
```
redis: 2 GB / 2 GB (100%)
```
**Solution**:
```bash
# Check Redis memory usage
docker exec trading-redis-prod redis-cli INFO memory

# Enable cache TTL
# Edit services/signal_cacher/signal_cacher.py
cache_ttl = 86400  # 24 hours instead of 0 (infinite)

# Manually clear old data
docker exec trading-redis-prod redis-cli FLUSHDB
```

---

### Problem: High CPU Usage

**Symptoms**:
- CPU at 100% constantly
- System unresponsive
- Slow processing

**Diagnosis**:
```bash
# Check container CPU
docker stats --no-stream

# Check process inside container
docker exec trading-sentiment-processor top
```

**Solutions**:

**1. FinBERT Inference Bottleneck**
```
sentiment-processor: 95% CPU
```
**Solution**:
```bash
# Use GPU acceleration (if available)
# Install CUDA version of PyTorch

# OR switch to LM Studio (3x faster)
# Edit .env
USE_LMSTUDIO=true

# Restart
docker-compose -f docker-compose.production.yml restart sentiment-processor
```

**2. Excessive Logging**
```
All services logging at DEBUG level
```
**Solution**:
```bash
# Change log level to INFO
# Edit services/common/logging_config.py
level=logging.INFO  # Changed from DEBUG

# Rebuild all services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

## Data Pipeline Failures

### Problem: No News Articles Being Collected

**Symptoms**:
- raw_news_data queue empty
- News poller logs show "0 new articles"
- Sentiment not updating

**Diagnosis**:
```bash
# Check news poller logs
docker logs trading-news-poller --tail 100

# Verify RSS feeds accessible
curl https://www.coindesk.com/arc/outboundfeeds/rss/

# Check published articles cache
docker exec trading-news-poller python -c "import sys; sys.path.append('/app'); from services.data_ingestor.news_poller import NewsPoller; p = NewsPoller(); print(len(p.published_articles))"
```

**Solutions**:

**1. RSS Feeds Down**
```
Error: Failed to fetch feed: timeout
```
**Solution**:
```bash
# Test feeds manually
curl -I https://www.coindesk.com/arc/outboundfeeds/rss/

# If down, wait or disable temporarily
# Edit services/data_ingestor/news_poller.py
# Comment out problematic feed
```

**2. All Articles Already Seen**
```
0 new articles published (all duplicates)
```
**Solution**:
```bash
# Clear cache to reprocess articles (testing only)
docker-compose -f docker-compose.production.yml restart news-poller

# OR reduce deduplication window
# Edit services/data_ingestor/news_poller.py
self.published_articles = set(articles_list[-1000:])  # Reduced from 8000
```

**3. Crypto Relevance Filter Too Strict**
```
100 articles fetched, 0 crypto-relevant
```
**Solution**:
```bash
# Check filter logs
docker logs trading-news-poller | grep "crypto-related"

# Broaden keywords
# Edit services/data_ingestor/news_poller.py
# Add more keywords to _get_crypto_keywords()
```

---

## Emergency Procedures

### Complete System Reset

```bash
# Stop all services
docker-compose -f docker-compose.production.yml down

# Clear all data (CAUTION: destructive)
docker volume rm cryptoboy-voidcat_ollama_models
docker volume rm cryptoboy-voidcat_redis_data

# Rebuild from scratch
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Verify all services healthy
check_status.bat
```

### Backup Critical Data

```bash
# Backup Redis data
docker exec trading-redis-prod redis-cli SAVE
docker cp trading-redis-prod:/data/dump.rdb ./backups/redis_$(date +%Y%m%d).rdb

# Backup Freqtrade database
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite ./backups/trades_$(date +%Y%m%d).sqlite

# Backup configuration
cp config/live_config.json ./backups/live_config_$(date +%Y%m%d).json
```

### Restore from Backup

```bash
# Restore Redis
docker cp ./backups/redis_20251123.rdb trading-redis-prod:/data/dump.rdb
docker-compose -f docker-compose.production.yml restart redis

# Restore Freqtrade database
docker cp ./backups/trades_20251123.sqlite trading-bot-app:/app/tradesv3.dryrun.sqlite
docker-compose -f docker-compose.production.yml restart trading-bot
```

---

## Getting Help

### Log Collection for Bug Reports

```bash
# Collect all logs
for service in trading-news-poller trading-sentiment-processor trading-signal-cacher trading-market-streamer trading-bot-app trading-rabbitmq-prod trading-redis-prod; do
  docker logs $service --tail 200 > logs/${service}_$(date +%Y%m%d_%H%M%S).log
done

# Create archive
tar -czf cryptoboy_logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/
```

### Support Channels

- **GitHub Issues**: https://github.com/sorrowscry86/Fictional-CryptoBoy/issues
- **Email**: SorrowsCry86@voidcat.org
- **Discord**: VoidCat RDC Server

### Information to Include

1. Error messages (exact text)
2. Docker logs (last 50-100 lines)
3. System information (OS, Docker version)
4. Configuration files (with sensitive data redacted)
5. Steps to reproduce
6. Expected vs actual behavior

---

**VoidCat RDC - Excellence in Problem Resolution**
**Version**: 1.0.0 (2025-11-23)
