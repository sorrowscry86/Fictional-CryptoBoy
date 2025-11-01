# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**CryptoBoy** is an LLM-powered cryptocurrency trading bot that combines sentiment analysis from news sources with technical indicators to execute automated trades via Freqtrade. The system supports two deployment modes:

- **Microservices Architecture** (Production): 7-service distributed system with RabbitMQ message broker and Redis caching
- **Legacy Monolithic** (Development): Single-container Freqtrade with CSV-based sentiment loading

**Critical Context**: The codebase underwent major microservice refactoring on Oct 28-29, 2025. All new development should target the microservices architecture unless explicitly working on legacy compatibility.

## Essential Commands

### Quick Start (Windows - RECOMMENDED)

```bash
# Interactive launcher with 12 operations
launcher.bat

# Direct commands
start_cryptoboy.bat     # Start system (select Mode 1 for microservices)
check_status.bat        # Health check all services
view_logs.bat           # Monitor service logs
start_monitor.bat       # Real-time trading dashboard
stop_cryptoboy.bat      # Graceful shutdown
```

### Docker Operations

```bash
# Development (infrastructure only: RabbitMQ, Redis, Ollama)
docker-compose up -d
docker-compose logs -f [rabbitmq|redis|ollama]
docker-compose down

# Production (full 7-service stack)
docker-compose -f docker-compose.production.yml up -d
docker-compose -f docker-compose.production.yml logs -f
docker-compose -f docker-compose.production.yml down

# Individual service rebuild
docker-compose -f docker-compose.production.yml build [service-name]
```

**Production Container Names**:
- Infrastructure: `trading-rabbitmq-prod`, `trading-redis-prod`, `trading-bot-ollama-prod`
- Microservices: `trading-news-poller`, `trading-sentiment-processor`, `trading-signal-cacher`, `trading-market-streamer`, `trading-bot-app`

**IMPORTANT**: Use full production names (see [Claude Desktop Operational Instructions](#claude-desktop-operational-instructions) for details)

### Data Pipeline (Legacy/Development)

```bash
# Full pipeline: market data → news aggregation → sentiment analysis
python scripts/run_data_pipeline.py --days 90 --news-age 7

# Individual steps
python scripts/run_data_pipeline.py --step 1  # Market data collection
python scripts/run_data_pipeline.py --step 2  # News aggregation
python scripts/run_data_pipeline.py --step 3  # Sentiment analysis

# Validation
python -c "from data.data_validator import DataValidator; DataValidator().validate_all()"
```

### Backtesting

```bash
# Run backtest with historical data
python backtest/run_backtest.py

# Target metrics: Sharpe > 1.0, Drawdown < 20%, Win Rate > 50%, Profit Factor > 1.5
```

### Monitoring & Debugging

```bash
# RabbitMQ Management UI
# http://localhost:15672 (admin/cryptoboy_secret)

# Redis CLI
docker exec -it trading-redis-prod redis-cli
> KEYS sentiment:*
> HGETALL sentiment:BTC/USDT

# Check message queues
docker exec trading-rabbitmq-prod rabbitmqctl list_queues

# Trading bot logs
docker logs trading-bot-app --tail 50 -f

# Test API keys
python scripts/verify_api_keys.py

# Test LM Studio integration
python scripts/test_lmstudio.py
```

## Architecture & Data Flow

### 7-Service Microservice Stack

```
Infrastructure Layer:
├── RabbitMQ (port 5672, UI on 15672) - Message broker
├── Redis (port 6379) - Sentiment cache with 4h staleness threshold
└── Ollama (port 11434) - LLM service (Mistral 7B)

Data Ingestion Layer:
├── Market Streamer (services/data_ingestor/market_streamer.py)
│   └── CCXT.pro WebSocket → raw_market_data queue
└── News Poller (services/data_ingestor/news_poller.py)
    └── RSS feeds (5 min poll) → raw_news_data queue

Processing Layer:
├── Sentiment Processor (services/sentiment_analyzer/sentiment_processor.py)
│   └── LLM cascade (FinBERT→LM Studio→Ollama) → sentiment_signals_queue
└── Signal Cacher (services/signal_cacher/signal_cacher.py)
    └── Queue consumer → Redis hash storage

Trading Layer:
└── Freqtrade Bot (strategies/llm_sentiment_strategy.py)
    └── Redis sentiment + Technical indicators → Trade execution
```

### Message Flow Pattern

```
News Sources → News Poller → raw_news_data (RabbitMQ)
                                    ↓
                         Sentiment Processor → sentiment_signals_queue
                                                        ↓
Exchange WebSocket → Market Streamer → raw_market_data    Signal Cacher → Redis
                                                                            ↓
                                                                    Trading Bot
                                                                    (reads Redis)
```

### Key Technologies

- **Trading Framework**: Freqtrade 2023.12+
- **Exchange**: CCXT 4.1+ (REST), CCXT.pro (WebSocket streaming)
- **Message Broker**: RabbitMQ 3.x (Pika client library)
- **Cache**: Redis 7.x with persistence
- **LLM Backends** (cascade):
  1. **Primary**: Hugging Face FinBERT (ProsusAI/finbert) - 100% accuracy on financial sentiment
  2. **Fallback**: LM Studio (OpenAI-compatible API, 3x faster inference)
  3. **Fallback**: Ollama (local Mistral 7B)
- **Technical Analysis**: TA-Lib 0.4.0+
- **Python**: 3.10+

### Directory Structure (High-Level)

```
├── config/                      # JSON configs (backtest, live trading)
├── data/                        # Data collectors, validators, storage
│   ├── *_collector.py          # OHLCV and news aggregation
│   ├── data_validator.py       # Quality checks
│   └── [ohlcv_data|news_data]/ # CSV storage
├── llm/                        # LLM integration layer
│   ├── huggingface_sentiment.py    # FinBERT (primary)
│   ├── lmstudio_adapter.py         # LM Studio (fast fallback)
│   ├── sentiment_analyzer.py       # Ollama (local fallback)
│   ├── signal_processor.py         # Aggregation + look-ahead prevention
│   └── model_manager.py            # Model lifecycle
├── strategies/                 # Freqtrade strategies
│   └── llm_sentiment_strategy.py   # Main Redis-based strategy
├── services/                   # Microservices (NEW - Oct 2025)
│   ├── common/                 # Shared utilities
│   │   ├── rabbitmq_client.py  # RabbitMQ connection manager
│   │   ├── redis_client.py     # Redis connection manager
│   │   └── logging_config.py   # Logging setup
│   ├── data_ingestor/          # Real-time data ingestion
│   ├── sentiment_analyzer/     # Sentiment processing
│   └── signal_cacher/          # Redis caching service
├── backtest/                   # Backtesting framework
├── risk/                       # Risk management
├── monitoring/                 # Telegram notifications
├── scripts/                    # Operational scripts
├── docs/                       # Comprehensive documentation
├── *.bat                       # Windows batch control (7 files)
├── docker-compose.yml          # Dev infrastructure
├── docker-compose.production.yml   # Full production stack
└── requirements*.txt           # Dependencies (split by service)
```

## Critical Patterns & Conventions

### Trading Strategy Logic

**File**: [strategies/llm_sentiment_strategy.py](strategies/llm_sentiment_strategy.py)

**Entry Conditions** (ALL must be true):
1. Sentiment score > 0.7 (strongly bullish from Redis cache)
2. EMA(12) > EMA(26) - uptrend confirmation
3. 30 < RSI < 70 - not overbought/oversold
4. MACD > MACD Signal - bullish crossover
5. Volume > Average Volume - liquidity confirmation
6. Price < Upper Bollinger Band - not overextended

**Exit Conditions** (ANY triggers exit):
1. Sentiment < -0.5 (bearish reversal)
2. EMA(12) < EMA(26) AND RSI > 70 - weakening + overbought
3. MACD < MACD Signal - bearish crossover
4. ROI targets: 5% (0 min), 3% (30 min), 2% (60 min), 1% (120 min)
5. Stop loss: -3% (trailing enabled at +1% profit)

**Position Sizing by Sentiment**:
```python
if sentiment > 0.8:
    stake = max_stake * 1.0  # 100% confidence
elif sentiment > 0.7:
    stake = max_stake * 0.75  # 75% confidence
else:
    stake = default_stake
```

### Look-Ahead Bias Prevention

**Critical**: All sentiment merging uses backward time alignment only to prevent future data leakage.

**Pattern** (from [llm/signal_processor.py](llm/signal_processor.py)):
```python
def _merge_sentiment_to_candles(candles_df, sentiment_df):
    """Merge sentiment using backward fill - NEVER forward"""
    merged = pd.merge_asof(
        candles_df.sort_values('timestamp'),
        sentiment_df.sort_values('timestamp'),
        on='timestamp',
        direction='backward',  # Only use PAST sentiment
        tolerance=pd.Timedelta(hours=4)  # Max staleness
    )
    return merged
```

### RabbitMQ Message Pattern

**All microservices use shared client** ([services/common/rabbitmq_client.py](services/common/rabbitmq_client.py)):

```python
from services.common.rabbitmq_client import RabbitMQClient

# Publisher
client = RabbitMQClient()
client.connect()
client.declare_queue('queue_name', durable=True)
client.publish('queue_name', {'data': 'value'})

# Consumer
def process_message(msg: dict):
    # Handle message
    pass

callback = create_consumer_callback(process_message)
client.consume('queue_name', callback, prefetch_count=10)
```

**Queue Names**:
- `raw_market_data` - WebSocket market data from exchanges
- `raw_news_data` - RSS feed articles
- `sentiment_signals_queue` - Processed sentiment scores

### Redis Sentiment Cache Pattern

**Strategy reads from Redis instead of CSV** (microservices mode):

```python
import redis
from datetime import datetime, timedelta

self.redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Retrieve sentiment for trading pair
sentiment_data = self.redis_client.hgetall(f'sentiment:{pair}')
score = float(sentiment_data.get('score', 0.0))
timestamp = datetime.fromisoformat(sentiment_data.get('timestamp'))

# Staleness check (4 hours default)
if (datetime.now() - timestamp) > timedelta(hours=4):
    logger.warning(f"Stale sentiment for {pair}")
    # Skip entry or use fallback logic
```

**Redis Hash Structure**:
```
Key: sentiment:BTC/USDT
Fields:
  score: 0.75
  timestamp: 2025-10-29T10:30:00
  headline: "Bitcoin surges as institutional adoption grows"
  source: coindesk
```

### LLM Sentiment Cascade

**Three-tier fallback system for resilience**:

```python
# Primary: FinBERT (Hugging Face - best accuracy)
from llm.huggingface_sentiment import HuggingFaceFinancialSentiment
analyzer = HuggingFaceFinancialSentiment(model_name="ProsusAI/finbert")
score = analyzer.analyze_sentiment(text)  # -1.0 to +1.0

# Fallback: LM Studio (3x faster, OpenAI API compatible)
from llm.lmstudio_adapter import UnifiedLLMClient
client = UnifiedLLMClient(prefer_lmstudio=True)
score = client.analyze_sentiment(text)

# Final Fallback: Ollama (local LLM, always available)
from llm.sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer(
    base_url=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
    model=os.getenv('OLLAMA_MODEL', 'mistral:7b')
)
score = analyzer.analyze_sentiment(text)
```

## Configuration Requirements

### Environment Variables (Required)

Create `.env` file in repository root:

```bash
# Exchange API (REQUIRED for live trading)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret_key

# RabbitMQ (REQUIRED for microservices)
RABBITMQ_USER=admin
RABBITMQ_PASS=cryptoboy_secret

# Redis (defaults work for local Docker)
REDIS_HOST=redis
REDIS_PORT=6379

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b
USE_LMSTUDIO=false  # Set true for 3x faster inference (requires LM Studio installed)

# Trading Mode (ALWAYS START WITH DRY RUN)
DRY_RUN=true

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Freqtrade Configuration

**File**: [config/live_config.json](config/live_config.json)

References environment variables via `${VARIABLE_NAME}` syntax. Key parameters:
- `max_open_trades`: 3 (default)
- `stake_currency`: "USDT"
- `stake_amount`: 100 (USDT per trade)
- `dry_run`: true (paper trading mode)
- `timeframe`: "1h"
- `pair_whitelist`: ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

### Risk Parameters

Embedded in [strategies/llm_sentiment_strategy.py](strategies/llm_sentiment_strategy.py):
```python
minimal_roi = {
    "0": 0.05,    # 5% immediate target
    "30": 0.03,   # 3% after 30 min
    "60": 0.02,   # 2% after 1 hour
    "120": 0.01   # 1% after 2 hours
}

stoploss = -0.03  # -3% stop loss
trailing_stop = True
trailing_stop_positive = 0.01  # Enable at +1% profit

# Strategy-specific
sentiment_buy_threshold = 0.7    # Bullish entry
sentiment_sell_threshold = -0.5  # Bearish exit
sentiment_stale_hours = 4        # Max cache age
```

## Development Workflow

### Initial Setup

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# 2. Install dependencies
pip install -r requirements.txt
pip install -r services/requirements-common.txt  # For microservices

# 3. Install TA-Lib (Windows requires build tools)
pip install TA-Lib

# 4. Configure environment
# Create .env file with API keys
# Set DRY_RUN=true for initial testing

# 5. Start infrastructure
docker-compose up -d  # RabbitMQ, Redis, Ollama

# 6. Run data pipeline (legacy mode)
python scripts/run_data_pipeline.py --days 90 --news-age 7

# 7. Validate data
python -c "from data.data_validator import DataValidator; DataValidator().validate_all()"

# 8. Run backtest
python backtest/run_backtest.py

# 9. Deploy paper trading
launcher.bat  # Select Mode 1 (microservices)

# 10. Monitor performance
start_monitor.bat
```

### Testing Approach

**Current State**: Manual testing workflow (no pytest configuration yet)

**Manual Test Commands**:
```bash
# API validation
python scripts/verify_api_keys.py

# LM Studio integration
python scripts/test_lmstudio.py

# Sentiment analysis
python -c "from llm.huggingface_sentiment import HuggingFaceFinancialSentiment; \
    analyzer = HuggingFaceFinancialSentiment(); \
    print(analyzer.analyze_sentiment('Bitcoin surges to new highs'))"

# Insert test trades
python scripts/insert_test_trades.py
```

**Future**: Add pytest configuration and unit test suite for all services.

### Deployment Checklist

**Before Production**:
1. ✓ Backtest shows Sharpe > 1.0, Drawdown < 20%
2. ✓ Paper trading (DRY_RUN=true) runs successfully for 7+ days
3. ✓ All 7 services healthy (check_status.bat)
4. ✓ Sentiment cache populating (Redis KEYS sentinel:*)
5. ✓ RabbitMQ queues processing (rabbitmqctl list_queues)
6. ✓ No API rate limit errors in logs
7. ✓ Risk parameters validated (stake amount, stop loss)
8. ✓ Telegram notifications working (optional)
9. ✓ 2FA enabled on exchange account
10. ✓ IP whitelist configured on exchange (if possible)

**Only then**: Set `DRY_RUN=false` in .env and restart trading bot.

## Critical Reminders

### Recent Major Changes

#### Oct 31, 2025 - FinBERT Integration & Monitoring Fixes

1. **Sentiment Analysis Engine Upgrade**
   - ✅ Switched from Ollama to **FinBERT** (ProsusAI/finbert) for sentiment analysis
   - ✅ Added PyTorch and Transformers dependencies (899.8 MB + libraries)
   - ✅ Model loads in-process (35 seconds) - no external LLM service needed
   - ✅ **TinyLLaMA** downloaded as backup (637 MB via Ollama)
   - ✅ Real sentiment scores now generating: -0.52 (bearish), +0.35 (bullish), -0.03 (neutral)
   - ✅ Previous issue: All scores were 0.0 due to Ollama memory constraints

2. **Batch File Container Name Fixes**
   - ✅ Fixed [check_status.bat](check_status.bat): Updated RabbitMQ and Redis container names
   - ✅ Fixed [view_logs.bat](view_logs.bat): Corrected all 6 microservice container names
   - ✅ See [BATCH_FILES_UPDATE_SUMMARY.md](BATCH_FILES_UPDATE_SUMMARY.md) for details

3. **Bug Fixes**
   - ✅ Added missing `RedisClient.ltrim()` method in [services/common/redis_client.py](services/common/redis_client.py:247)
   - ✅ Fixed RabbitMQ authentication: Created admin user with correct credentials
   - ✅ Updated Ollama health check in docker-compose.production.yml
   - ✅ Changed Freqtrade API listen address from 127.0.0.1 to 0.0.0.0

#### Oct 28-29, 2025 - Microservice Architecture

1. **Microservice Architecture Refactoring** (PR #2)
   - Monolithic app split into 4 microservices + 3 infrastructure services
   - Added RabbitMQ message broker for inter-service communication
   - Added Redis cache for real-time sentiment delivery
   - WebSocket market data streaming via ccxt.pro

2. **Windows Batch Control System**
   - 7 new/updated batch files for complete operational control
   - Interactive launcher (launcher.bat) with 12 operations
   - Granular service management and monitoring

3. **Requirements Split**
   - `requirements.txt` - Core dependencies
   - `services/requirements-common.txt` - Shared microservice deps (includes transformers, torch)
   - `services/requirements-ingestor.txt` - CCXT.pro for market streamer only
   - Prevents WebSocket library conflicts

### Test Documentation Standard

**"NO SIMULATIONS LAW"**: All test output must be real. No placeholder text, no "simulated" data. See [docs/TEST_RUN_TEMPLATE.md](docs/TEST_RUN_TEMPLATE.md) for comprehensive test logging framework.

### Known Issues

1. **Geographic Restrictions**: Binance API may be geo-restricted
   - Solution: Use Binance Testnet, switch to Kraken/Coinbase Pro, or use VPN

2. **Market Data**: Currently using synthetic data for backtesting
   - Cause: Coinbase API auth issues (private key format)
   - Solution: Resolve Coinbase auth or use Binance testnet

3. **Code Quality**: No linting/formatting configs yet
   - Missing: pytest.ini, .flake8, pylint, black configs
   - Missing: pre-commit hooks
   - Add to development roadmap

### Resolved Issues (Oct 31, 2025)

1. ✅ **Sentiment Scores All Zero** - Fixed by switching to FinBERT
   - Previous: Ollama memory constraints (3.8 GB required, 1.4 GB available)
   - Solution: FinBERT runs in-process, no memory issues
   - Status: Generating real scores (-0.52 bearish, +0.35 bullish, etc.)

2. ✅ **RabbitMQ Authentication Failures** - Fixed by creating admin user
   - Previous: Services using admin/cryptoboy_secret, but only cryptoboy/cryptoboy123 existed
   - Solution: Created admin user with correct credentials
   - Status: All services connecting successfully

3. ✅ **Batch File Container Names** - Fixed in check_status.bat and view_logs.bat
   - Previous: Used generic names (rabbitmq, redis, sentiment-processor)
   - Solution: Updated to production names (trading-rabbitmq-prod, etc.)
   - Status: All batch files now reference correct containers

### Security Best Practices

1. **Never commit API keys** to version control (use .env, add to .gitignore)
2. **Start with DRY_RUN=true** for all initial testing
3. **Use read-only API keys** when possible for monitoring
4. **Enable IP whitelisting** on exchange API settings
5. **Use 2FA** on exchange account
6. **Monitor for unusual activity** (Telegram notifications recommended)
7. **Keep dependencies updated** (especially ccxt and freqtrade)

## Claude Desktop Operational Instructions

This section provides commands and procedures specifically for Claude Desktop/Claude Code AI assistants working with the CryptoBoy system.

### Container Naming Conventions

**CRITICAL**: Production containers have specific names. Always use these exact names:

```bash
Infrastructure:
  trading-rabbitmq-prod    # RabbitMQ message broker
  trading-redis-prod       # Redis sentiment cache
  trading-bot-ollama-prod  # Ollama LLM service (backup)

Microservices:
  trading-news-poller           # News RSS aggregation
  trading-sentiment-processor   # FinBERT sentiment analysis
  trading-signal-cacher         # Redis cache writer
  trading-market-streamer       # Exchange WebSocket (future)
  trading-bot-app               # Freqtrade trading bot
```

**DO NOT** use generic names like `rabbitmq`, `redis`, `sentiment-processor` - these will fail!

### System Health Check Commands

```bash
# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}" | grep trading

# Verify RabbitMQ queues
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages

# Check Redis sentiment keys
docker exec trading-redis-prod redis-cli KEYS "sentiment:*"

# View current sentiment scores
docker exec trading-redis-prod redis-cli HGETALL "sentiment:BTC/USDT"
docker exec trading-redis-prod redis-cli HGET "sentiment:BTC/USDT" score
```

### Monitoring Service Logs

```bash
# Sentiment processor (FinBERT)
docker logs trading-sentiment-processor --tail 50 -f

# News poller
docker logs trading-news-poller --tail 50 -f

# Signal cacher
docker logs trading-signal-cacher --tail 50 -f

# Trading bot
docker logs trading-bot-app --tail 50 -f

# RabbitMQ
docker logs trading-rabbitmq-prod --tail 50 -f
```

### Environment Variables for Docker Compose

When running docker-compose commands, always export these first:

```bash
export RABBITMQ_USER=admin
export RABBITMQ_PASS=cryptoboy_secret
docker-compose -f docker-compose.production.yml [command]
```

Or use inline:

```bash
RABBITMQ_USER=admin RABBITMQ_PASS=cryptoboy_secret \
  docker-compose -f docker-compose.production.yml up -d
```

### Rebuilding Services

When code changes are made to a service:

```bash
# Rebuild sentiment-processor (FinBERT)
export RABBITMQ_USER=admin && export RABBITMQ_PASS=cryptoboy_secret
docker-compose -f docker-compose.production.yml build sentiment-processor
docker-compose -f docker-compose.production.yml up -d sentiment-processor

# Rebuild all services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

### Verifying FinBERT Sentiment Analysis

FinBERT should generate **non-zero sentiment scores**. To verify:

```bash
# 1. Check logs for "Sentiment analysis complete" messages
docker logs trading-sentiment-processor --tail 20 | grep "Sentiment analysis complete"

# 2. Check Redis for non-zero scores
docker exec trading-redis-prod redis-cli HGET "sentiment:BTC/USDT" score

# 3. Expected output: -1.0 to +1.0 (NOT 0.0)
# Examples:
#   -0.52 = bearish (negative news)
#    0.06 = slightly bullish (positive news)
#   -0.03 = neutral (mixed/unclear news)
```

**If all scores are 0.0**, check:
1. Sentiment processor logs for errors
2. FinBERT model loaded successfully (should see "FinBERT test successful" in logs)
3. News articles being processed (check RabbitMQ queue depth)

### RabbitMQ Operations

```bash
# Check queue status
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages

# Check user permissions
docker exec trading-rabbitmq-prod rabbitmqctl list_users

# Create admin user (if needed)
docker exec trading-rabbitmq-prod rabbitmqctl add_user admin cryptoboy_secret
docker exec trading-rabbitmq-prod rabbitmqctl set_user_tags admin administrator
docker exec trading-rabbitmq-prod rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
```

### Redis Operations

```bash
# Check all sentiment keys
docker exec trading-redis-prod redis-cli KEYS "sentiment:*"

# View specific sentiment
docker exec trading-redis-prod redis-cli HGETALL "sentiment:BTC/USDT"

# Check database size
docker exec trading-redis-prod redis-cli DBSIZE

# Clear all sentiment keys (use with caution)
docker exec trading-redis-prod redis-cli DEL sentiment:BTC/USDT sentiment:ETH/USDT sentiment:BNB/USDT
```

### Common Issues & Solutions

#### Issue: "Container not found" errors

**Solution**: Use full production container names (see naming conventions above)

```bash
# ❌ WRONG
docker logs sentiment-processor

# ✅ CORRECT
docker logs trading-sentiment-processor
```

#### Issue: Sentiment scores all 0.0

**Solution**: Verify FinBERT loaded correctly

```bash
# Check model initialization
docker logs trading-sentiment-processor | grep "FinBERT"

# Expected: "FinBERT test successful (test score: -0.16)"
# If missing: Model failed to load or wrong configuration
```

#### Issue: RabbitMQ authentication failures

**Solution**: Verify admin user exists with correct password

```bash
docker exec trading-rabbitmq-prod rabbitmqctl list_users
# Should show: admin [administrator]

# If missing, create user (see RabbitMQ Operations above)
```

#### Issue: Services not seeing environment variables

**Solution**: Export variables before running docker-compose

```bash
# Must export BEFORE docker-compose command
export RABBITMQ_USER=admin
export RABBITMQ_PASS=cryptoboy_secret
docker-compose -f docker-compose.production.yml up -d
```

### File Locations for Common Tasks

| Task | File Location |
|------|---------------|
| Sentiment processor code | [services/sentiment_analyzer/sentiment_processor.py](services/sentiment_analyzer/sentiment_processor.py) |
| FinBERT integration | [llm/huggingface_sentiment.py](llm/huggingface_sentiment.py) |
| Redis client | [services/common/redis_client.py](services/common/redis_client.py) |
| RabbitMQ client | [services/common/rabbitmq_client.py](services/common/rabbitmq_client.py) |
| Trading strategy | [strategies/llm_sentiment_strategy.py](strategies/llm_sentiment_strategy.py) |
| Docker production config | [docker-compose.production.yml](docker-compose.production.yml) |
| Batch files | [*.bat](*.bat) files in root directory |

### Verification Workflow After Changes

When making code changes, follow this workflow:

1. **Code Changes** → Edit files
2. **Rebuild Service** → `docker-compose build [service-name]`
3. **Restart Service** → `docker-compose up -d [service-name]`
4. **Check Logs** → `docker logs [container-name] --tail 50`
5. **Verify Output** → Check Redis/RabbitMQ for expected data
6. **Test End-to-End** → Verify trading bot receives sentiment

### Troubleshooting Quick Reference

```bash
# Docker not running
# → Start Docker Desktop

# Services won't start
check_status.bat
view_logs.bat
docker-compose down && docker-compose up -d

# No sentiment in Redis
docker exec -it trading-redis-prod redis-cli KEYS "sentiment:*"
docker logs trading-signal-cacher --tail 50

# RabbitMQ connection errors
docker logs trading-rabbitmq-prod
docker exec trading-rabbitmq-prod rabbitmqctl status
# Check RABBITMQ_USER and RABBITMQ_PASS in .env

# Bot not entering trades
docker logs trading-bot-app --tail 50
# 1. Verify DRY_RUN setting
# 2. Check sentiment cache populated
# 3. Verify all 6 entry conditions met
# 4. Check exchange API connectivity
```

## Additional Resources

### Documentation Files

- [README.md](README.md) - Project overview and quick start
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture overview with sequence diagrams
- [docs/MICROSERVICES_ARCHITECTURE.md](docs/MICROSERVICES_ARCHITECTURE.md) - Microservices detailed guide
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) - Comprehensive developer reference
- [docs/TEST_RUN_TEMPLATE.md](docs/TEST_RUN_TEMPLATE.md) - Test documentation template (421 lines)
- [LAUNCHER_GUIDE.md](LAUNCHER_GUIDE.md) - Batch file reference
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [API_SETUP_GUIDE.md](API_SETUP_GUIDE.md) - Exchange API configuration
- [LAUNCH_PATTERN_SUMMARY.md](LAUNCH_PATTERN_SUMMARY.md) - Microservice launch patterns

### Project Metadata

- **Author**: Wykeve Freeman (Sorrow Eternal) / VoidCat RDC
- **License**: MIT
- **Python**: 3.9+ (3.10+ recommended)
- **Exchange**: Binance (primary), Coinbase (partial support)
- **Trading Pairs**: BTC/USDT, ETH/USDT, SOL/USDT
- **Default Timeframe**: 1h candles

---

**For additional context**, refer to [.specstory/history/](*.specstory/history/) for detailed conversation logs documenting architectural decisions and development evolution.
