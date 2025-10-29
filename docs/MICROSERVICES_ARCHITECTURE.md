# CryptoBoy Microservices Architecture

## Overview

CryptoBoy has been refactored from a monolithic architecture to a decoupled, message-driven microservice architecture. This transformation enhances real-time responsiveness, scalability, and resilience.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐        ┌──────────────────────┐       │
│  │  Market Streamer    │        │   News Poller        │       │
│  │  (WebSocket)        │        │   (RSS Feeds)        │       │
│  │                     │        │                      │       │
│  │  - BTC/USDT         │        │  - CoinDesk          │       │
│  │  - ETH/USDT         │        │  - CoinTelegraph     │       │
│  │  - BNB/USDT         │        │  - TheBlock          │       │
│  │                     │        │  - Decrypt           │       │
│  │  Real-time OHLCV    │        │  - Bitcoin Magazine  │       │
│  └──────────┬──────────┘        └──────────┬───────────┘       │
│             │                               │                   │
│             └───────────┬───────────────────┘                   │
│                         ▼                                       │
│                   ┌──────────┐                                 │
│                   │ RabbitMQ │                                 │
│                   └──────────┘                                 │
│                         │                                       │
│         ┌───────────────┼───────────────┐                      │
│         │               │               │                       │
│         ▼               ▼               ▼                       │
│  raw_market_data   raw_news_data   (other queues)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SENTIMENT ANALYSIS LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│              ┌────────────────────────────┐                      │
│              │  Sentiment Processor       │                      │
│              │                            │                      │
│              │  Consumes: raw_news_data   │                      │
│              │  ┌──────────────────────┐  │                      │
│              │  │  Ollama LLM          │  │                      │
│              │  │  (mistral:7b)        │  │                      │
│              │  │                      │  │                      │
│              │  │  Sentiment Analysis  │  │                      │
│              │  └──────────────────────┘  │                      │
│              │                            │                      │
│              │  Publishes: sentiment_     │                      │
│              │             signals_queue  │                      │
│              └──────────────┬─────────────┘                      │
│                             │                                    │
│                             ▼                                    │
│                   ┌──────────────────┐                           │
│                   │ sentiment_signals│                           │
│                   │      _queue      │                           │
│                   └──────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       CACHING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│              ┌────────────────────────────┐                      │
│              │  Signal Cacher             │                      │
│              │                            │                      │
│              │  Consumes: sentiment_      │                      │
│              │            signals_queue   │                      │
│              │                            │                      │
│              │  Updates Redis Cache:      │                      │
│              │  ┌──────────────────────┐  │                      │
│              │  │ sentiment:BTC/USDT   │  │                      │
│              │  │ sentiment:ETH/USDT   │  │                      │
│              │  │ sentiment:BNB/USDT   │  │                      │
│              │  └──────────────────────┘  │                      │
│              └──────────────┬─────────────┘                      │
│                             │                                    │
│                             ▼                                    │
│                      ┌──────────┐                                │
│                      │  Redis   │                                │
│                      └──────────┘                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      TRADING EXECUTION LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│              ┌────────────────────────────┐                      │
│              │  Freqtrade Trading Bot     │                      │
│              │                            │                      │
│              │  LLMSentimentStrategy      │                      │
│              │  ┌──────────────────────┐  │                      │
│              │  │ Reads Redis Cache:   │  │                      │
│              │  │                      │  │                      │
│              │  │ - Latest sentiment   │  │                      │
│              │  │ - Technical indicators│  │                     │
│              │  │                      │  │                      │
│              │  │ Trading Decisions:   │  │                      │
│              │  │ - Entry signals      │  │                      │
│              │  │ - Exit signals       │  │                      │
│              │  │ - Position sizing    │  │                      │
│              │  └──────────────────────┘  │                      │
│              │                            │                      │
│              │  Executes on Binance       │                      │
│              └────────────────────────────┘                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Technologies

- **Message Broker**: RabbitMQ 3.x (with management UI)
- **Cache**: Redis 7.x (with persistence)
- **LLM**: Ollama (local LLM server) with Mistral 7B
- **Trading Framework**: Freqtrade 2023.12+
- **Python**: 3.10+

## Microservices

### 1. Market Data Streamer (`services/data_ingestor/market_streamer.py`)

**Purpose**: Real-time market data ingestion via WebSocket connections.

**Key Features**:
- Connects to Binance WebSocket API using `ccxt.pro`
- Streams live OHLCV candle data for configured trading pairs
- Publishes formatted market data to `raw_market_data` queue
- Automatic reconnection on network failures
- Duplicate detection to avoid republishing same candles

**Configuration**:
```bash
TRADING_PAIRS=BTC/USDT,ETH/USDT,BNB/USDT
CANDLE_TIMEFRAME=1m
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

**Message Format**:
```json
{
  "type": "market_data",
  "source": "binance_websocket",
  "symbol": "BTC/USDT",
  "timeframe": "1m",
  "timestamp": "2025-10-29T12:34:56",
  "timestamp_ms": 1730203496000,
  "data": {
    "open": 68500.0,
    "high": 68550.0,
    "low": 68480.0,
    "close": 68530.0,
    "volume": 125.5
  },
  "collected_at": "2025-10-29T12:34:57"
}
```

### 2. News Poller (`services/data_ingestor/news_poller.py`)

**Purpose**: Continuous news aggregation from RSS feeds.

**Key Features**:
- Polls 5 major crypto news sources every 5 minutes (configurable)
- HTML cleaning and content extraction
- Crypto-relevance filtering using keyword matching
- Deduplication using article ID hashing
- Publishes new articles to `raw_news_data` queue

**Configuration**:
```bash
NEWS_POLL_INTERVAL=300  # seconds
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

**Supported Sources**:
- CoinDesk
- CoinTelegraph
- TheBlock
- Decrypt
- Bitcoin Magazine

**Message Format**:
```json
{
  "type": "news_article",
  "article_id": "a1b2c3d4e5f6...",
  "source": "coindesk",
  "title": "Bitcoin Breaks New All-Time High",
  "link": "https://...",
  "summary": "Bitcoin reached a new...",
  "content": "Full article content...",
  "published": "2025-10-29T10:00:00",
  "fetched_at": "2025-10-29T10:05:00"
}
```

### 3. Sentiment Processor (`services/sentiment_analyzer/sentiment_processor.py`)

**Purpose**: LLM-based sentiment analysis of news articles.

**Key Features**:
- Consumes news articles from `raw_news_data` queue
- Uses Ollama LLM (Mistral 7B) for sentiment scoring
- Sentiment range: -1.0 (very bearish) to +1.0 (very bullish)
- Matches articles to relevant trading pairs using keyword detection
- Publishes enriched sentiment signals to `sentiment_signals_queue`

**Configuration**:
```bash
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b
TRADING_PAIRS=BTC/USDT,ETH/USDT,BNB/USDT
RABBITMQ_HOST=rabbitmq
```

**Sentiment Classification**:
- **Very Bullish**: score ≥ 0.7
- **Bullish**: 0.3 ≤ score < 0.7
- **Neutral**: -0.3 < score < 0.3
- **Bearish**: -0.7 < score ≤ -0.3
- **Very Bearish**: score ≤ -0.7

**Message Format**:
```json
{
  "type": "sentiment_signal",
  "article_id": "a1b2c3d4e5f6...",
  "pair": "BTC/USDT",
  "source": "coindesk",
  "headline": "Bitcoin Breaks New All-Time High",
  "sentiment_score": 0.85,
  "sentiment_label": "very_bullish",
  "published": "2025-10-29T10:00:00",
  "analyzed_at": "2025-10-29T10:05:30",
  "model": "mistral:7b"
}
```

### 4. Signal Cacher (`services/signal_cacher/signal_cacher.py`)

**Purpose**: Fast caching of sentiment signals in Redis.

**Key Features**:
- Consumes sentiment signals from `sentiment_signals_queue`
- Updates Redis hash with latest sentiment per trading pair
- Maintains optional historical signal list (last 100)
- Configurable TTL for cache entries
- High-throughput processing (prefetch=10)

**Configuration**:
```bash
REDIS_HOST=redis
REDIS_PORT=6379
RABBITMQ_HOST=rabbitmq
SIGNAL_CACHE_TTL=0  # 0 = no expiry
```

**Redis Data Structure**:
```
Key: sentiment:BTC/USDT
Type: Hash
Fields:
  score: 0.85
  label: very_bullish
  timestamp: 2025-10-29T10:05:30
  headline: Bitcoin Breaks New...
  source: coindesk
  article_id: a1b2c3d4e5f6...
```

### 5. Trading Bot (Modified Freqtrade Strategy)

**Purpose**: Execute trades based on sentiment + technical indicators.

**Key Modifications**:
- Replaced CSV-based sentiment loading with Redis cache reads
- Real-time sentiment fetching per trading pair
- Staleness check (default: 4 hours)
- Integrated with existing technical analysis

**Entry Conditions**:
- Sentiment > 0.7 (strongly positive)
- EMA short > EMA long (uptrend)
- 30 < RSI < 70 (not overbought/oversold)
- MACD bullish crossover
- Volume > average
- Price < upper Bollinger Band

**Exit Conditions**:
- Sentiment < -0.5 (negative)
- EMA short < EMA long + RSI > 70
- MACD bearish crossover

**Position Sizing**:
- Sentiment > 0.8: 100% of max stake
- Sentiment > 0.7: 75% of max stake
- Default: standard stake amount

## Message Queues

### Queue Configuration

All queues are configured with:
- **Durable**: Yes (survive broker restart)
- **Auto-delete**: No
- **Message Persistence**: Enabled
- **Prefetch Count**: Varies by service (1-10)

### Queue Workflow

```
┌─────────────────┐
│ raw_market_data │  ← Market Streamer
└────────┬────────┘
         │ (Future: consumed by market analysis service)
         ▼

┌─────────────────┐
│ raw_news_data   │  ← News Poller
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Sentiment Processor  │  (Consumes raw_news_data)
└──────────┬───────────┘
           │
           ▼
┌────────────────────────┐
│ sentiment_signals_queue│  ← Sentiment Processor
└────────┬───────────────┘
         │
         ▼
┌──────────────────┐
│ Signal Cacher    │  (Consumes sentiment_signals_queue)
└────────┬─────────┘
         │
         ▼
    ┌────────┐
    │ Redis  │  → Read by Freqtrade Strategy
    └────────┘
```

## Deployment

### Development

```bash
# Start infrastructure only
docker-compose up -d

# The main trading bot and microservices run separately in development
```

### Production

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f sentiment-processor

# Stop all services
docker-compose -f docker-compose.production.yml down
```

### Service Health Checks

**RabbitMQ Management UI**:
- URL: http://localhost:15672
- Default credentials: cryptoboy / cryptoboy123
- Monitor queues, message rates, and connections

**Redis CLI**:
```bash
# Connect to Redis
docker exec -it trading-redis-prod redis-cli

# Check cached sentiment
HGETALL sentiment:BTC/USDT

# View all sentiment keys
KEYS sentiment:*

# Check key expiration
TTL sentiment:BTC/USDT
```

## Environment Variables

Create a `.env` file in the project root:

```bash
# Exchange API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# RabbitMQ
RABBITMQ_USER=cryptoboy
RABBITMQ_PASS=cryptoboy123

# Redis (optional, defaults work for local development)
REDIS_HOST=redis
REDIS_PORT=6379

# Ollama LLM
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b

# Trading Configuration
TRADING_PAIRS=BTC/USDT,ETH/USDT,BNB/USDT
CANDLE_TIMEFRAME=1m
NEWS_POLL_INTERVAL=300

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Mode
DRY_RUN=true  # Set to false for live trading

# Logging
LOG_LEVEL=INFO
```

## Monitoring & Debugging

### View Service Logs

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker logs -f trading-sentiment-processor
docker logs -f trading-news-poller
docker logs -f trading-market-streamer
docker logs -f trading-signal-cacher
```

### Check RabbitMQ Queues

1. Open http://localhost:15672
2. Navigate to **Queues** tab
3. Verify message rates and queue sizes
4. Check for errors in **Connections** tab

### Verify Redis Cache

```bash
# Enter Redis CLI
docker exec -it trading-redis-prod redis-cli

# Check sentiment for a pair
HGETALL sentiment:BTC/USDT

# View all sentiment keys
KEYS sentiment:*

# Check sentiment history
LRANGE sentiment_history:BTC/USDT 0 9
```

### Test Individual Services

```bash
# Test news poller
docker exec -it trading-news-poller python -m services.data_ingestor.news_poller

# Test sentiment processor
docker exec -it trading-sentiment-processor python -m services.sentiment_analyzer.sentiment_processor
```

## Performance Considerations

### Scalability

**Horizontal Scaling**:
- Multiple news pollers can run concurrently (use different feed subsets)
- Multiple sentiment processors can process in parallel
- Signal cacher can be scaled for high-throughput scenarios

**Vertical Scaling**:
- Increase RabbitMQ memory and disk limits
- Adjust Redis `maxmemory` policy
- Allocate more CPU/RAM to Ollama for faster LLM inference

### Optimization Tips

1. **News Polling**: Adjust `NEWS_POLL_INTERVAL` based on news velocity
2. **Sentiment Processing**: Use faster LLM models (e.g., `orca-mini`) for lower latency
3. **Redis TTL**: Set appropriate cache expiration to balance freshness vs. memory
4. **Prefetch Count**: Tune RabbitMQ prefetch for optimal throughput
5. **Market Streaming**: Adjust `CANDLE_TIMEFRAME` based on strategy needs

## Troubleshooting

### Common Issues

**1. RabbitMQ Connection Refused**
```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# Restart RabbitMQ
docker-compose restart rabbitmq

# Check logs
docker logs trading-rabbitmq
```

**2. Redis Connection Timeout**
```bash
# Check Redis status
docker exec -it trading-redis-prod redis-cli ping

# Should return: PONG
```

**3. Ollama Model Not Found**
```bash
# Pull the model
docker exec -it trading-bot-ollama-prod ollama pull mistral:7b

# List available models
docker exec -it trading-bot-ollama-prod ollama list
```

**4. No Sentiment Data in Strategy**
```bash
# Check Redis cache
docker exec -it trading-redis-prod redis-cli HGETALL sentiment:BTC/USDT

# If empty, check signal cacher logs
docker logs trading-signal-cacher

# Check if sentiment processor is running
docker ps | grep sentiment-processor
```

## Migration from Legacy System

### What Changed

**Before** (Monolithic):
- CSV-based data persistence
- Batch processing with cron jobs
- Sentiment loaded hourly from disk
- Tight coupling between components

**After** (Microservices):
- Real-time message streaming via RabbitMQ
- Continuous processing (no batch jobs)
- Sentiment cached in Redis for instant access
- Loose coupling, independent scaling

### Backward Compatibility

The old CSV-based data pipeline scripts are preserved in `scripts/` for:
- Historical data backfilling
- Offline analysis
- Backtesting with historical sentiment

## Future Enhancements

1. **Market Data Processing Service**: Consume `raw_market_data` for custom indicators
2. **Signal Aggregation Service**: Combine multiple sentiment sources
3. **Dead Letter Queues**: Handle failed messages gracefully
4. **Metrics & Monitoring**: Prometheus + Grafana dashboards
5. **WebSocket API**: Real-time sentiment feed for external consumers
6. **Multi-LLM Support**: Ensemble sentiment from multiple models

## Contributing

When adding new microservices:
1. Create service directory under `services/`
2. Implement using shared utilities from `services/common/`
3. Add Dockerfile and requirements
4. Update `docker-compose.production.yml`
5. Document in this file

## License

See main project LICENSE file.
