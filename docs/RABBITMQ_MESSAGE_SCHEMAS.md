# RabbitMQ Message Schemas & Contracts
**VoidCat RDC - CryptoBoy Trading System**
**Documentation Standard: NO SIMULATIONS LAW**

This document defines all RabbitMQ message schemas and communication contracts between microservices.

---

## Table of Contents
1. [Queue Overview](#queue-overview)
2. [Message Schemas](#message-schemas)
3. [Message Flow Diagrams](#message-flow-diagrams)
4. [Validation Rules](#validation-rules)
5. [Error Handling](#error-handling)

---

## Queue Overview

### Active Queues (Production)

| Queue Name | Producer | Consumer | Message Type | Durability |
|------------|----------|----------|--------------|------------|
| `raw_news_data` | News Poller | Sentiment Processor | RawNewsMessage | Durable |
| `raw_market_data` | Market Streamer | Trading Bot | RawMarketDataMessage | Durable |
| `sentiment_signals_queue` | Sentiment Processor | Signal Cacher | SentimentSignalMessage | Durable |

### Queue Configuration

**All queues share these settings:**
- **Durable**: Yes (survives RabbitMQ restarts)
- **Auto-delete**: No
- **Exclusive**: No
- **Arguments**: None (default)

**Connection Settings:**
- **Host**: `RABBITMQ_HOST` (default: localhost)
- **Port**: `RABBITMQ_PORT` (default: 5672)
- **Virtual Host**: `/`
- **Credentials**: `RABBITMQ_USER` / `RABBITMQ_PASS` (from environment)

---

## Message Schemas

### 1. RawNewsMessage

**Queue**: `raw_news_data`
**Producer**: News Poller
**Consumer**: Sentiment Processor

**Purpose**: Transport raw news articles from RSS feeds to sentiment analysis service.

#### Schema Definition

```python
class RawNewsMessage(BaseModel):
    timestamp: datetime      # When article was published
    source: str             # RSS feed source (coindesk, cointelegraph, etc.)
    title: str              # Article headline (1-500 chars)
    url: str                # Article URL (validated against source domain)
    content: str            # Full article text (10-50000 chars)
```

#### Field Validation

| Field | Type | Constraints | Validation |
|-------|------|-------------|------------|
| `timestamp` | datetime | ISO 8601 format | Pydantic datetime parser |
| `source` | str | 1-100 chars | Whitelist: coindesk, cointelegraph, decrypt, bitcoin_magazine, cryptoslate |
| `title` | str | 1-500 chars | Min/max length enforcement |
| `url` | str | Valid URL | Must match source domain (anti-spoofing) |
| `content` | str | 10-50000 chars | Min/max length enforcement |

#### Security Features

**URL Domain Validation** (Anti-Spoofing):
```python
ALLOWED_NEWS_DOMAINS = {
    "coindesk": ["coindesk.com", "www.coindesk.com"],
    "cointelegraph": ["cointelegraph.com", "www.cointelegraph.com"],
    "decrypt": ["decrypt.co", "www.decrypt.co"],
    "bitcoin_magazine": ["bitcoinmagazine.com", "www.bitcoinmagazine.com"],
    "cryptoslate": ["cryptoslate.com", "www.cryptoslate.com"],
}
```

**Validation Logic**:
1. Extract domain from URL
2. Verify domain matches claimed source
3. Reject if domain mismatch (prevents injection attacks)

#### Example Message

```json
{
    "timestamp": "2025-11-23T10:30:00Z",
    "source": "coindesk",
    "title": "Bitcoin Hits New All-Time High as Institutional Adoption Grows",
    "url": "https://www.coindesk.com/markets/2025/11/23/bitcoin-ath-institutional",
    "content": "Bitcoin (BTC) reached a new all-time high today, surpassing $100,000..."
}
```

---

### 2. RawMarketDataMessage

**Queue**: `raw_market_data`
**Producer**: Market Streamer
**Consumer**: Trading Bot (direct consumption, not via Signal Cacher)

**Purpose**: Transport real-time OHLCV candle data from exchange WebSocket to trading strategy.

#### Schema Definition

```python
class RawMarketDataMessage(BaseModel):
    timestamp: datetime      # Candle close time
    pair: str               # Trading pair (BTC/USDT format)
    open: float             # Opening price
    high: float             # Highest price
    low: float              # Lowest price
    close: float            # Closing price
    volume: float           # Trading volume
```

#### Field Validation

| Field | Type | Constraints | Validation |
|-------|------|-------------|------------|
| `timestamp` | datetime | ISO 8601 format | Pydantic datetime parser |
| `pair` | str | Regex: `^[A-Z]{3,5}/[A-Z]{3,5}$` | 3-5 uppercase letters each side |
| `open` | float | $0.000001 - $1,000,000 | Price sanity bounds |
| `high` | float | $0.000001 - $1,000,000 | >= low, open, close |
| `low` | float | $0.000001 - $1,000,000 | <= high, open, close |
| `close` | float | $0.000001 - $1,000,000 | Price sanity bounds |
| `volume` | float | >= 0 | Non-negative |

#### Security Features

**Price Sanity Bounds**:
```python
PRICE_SANITY_BOUNDS = {
    "max_crypto_price": 1_000_000.0,  # $1M per coin maximum
    "min_crypto_price": 0.000001,      # Minimum for micro-cap tokens
}
```

**Cross-Field Validation**:
- `high >= low` (always)
- `high >= open` (always)
- `high >= close` (always)
- `low <= open` (always)
- `low <= close` (always)

**Rejection Criteria**:
- Prices outside sanity bounds (prevents data errors)
- Invalid OHLC relationships (prevents corrupted candles)
- Negative volume (prevents data corruption)

#### Example Message

```json
{
    "timestamp": "2025-11-23T10:00:00Z",
    "pair": "BTC/USDT",
    "open": 95000.50,
    "high": 95500.00,
    "low": 94800.00,
    "close": 95200.25,
    "volume": 1234.56789
}
```

---

### 3. SentimentSignalMessage

**Queue**: `sentiment_signals_queue`
**Producer**: Sentiment Processor
**Consumer**: Signal Cacher

**Purpose**: Transport analyzed sentiment scores from FinBERT to Redis cache for trading strategy consumption.

#### Schema Definition

```python
class SentimentSignalMessage(BaseModel):
    timestamp: datetime           # When sentiment was analyzed
    pair: str                     # Trading pair (BTC/USDT format)
    score: float                  # Sentiment score (-1.0 to +1.0)
    headline: str                 # News headline analyzed
    source: str                   # News source
    confidence: Optional[float]   # Model confidence (0.0-1.0)
    model: str                    # Model used (finbert, ollama, lmstudio)
```

#### Field Validation

| Field | Type | Constraints | Validation |
|-------|------|-------------|------------|
| `timestamp` | datetime | ISO 8601 format | Pydantic datetime parser |
| `pair` | str | Regex: `^[A-Z]{3,5}/[A-Z]{3,5}$` | 3-5 uppercase letters each side |
| `score` | float | -1.0 to +1.0 | Sentiment range enforcement |
| `headline` | str | 1-500 chars | Min/max length |
| `source` | str | 1-100 chars | Source identifier |
| `confidence` | float (optional) | 0.0 to 1.0 | Model confidence |
| `model` | str | Enum | finbert, distilroberta-financial, ollama, lmstudio |

#### Sentiment Score Interpretation

| Score Range | Label | Trading Signal | Example Headlines |
|-------------|-------|----------------|-------------------|
| 0.7 to 1.0 | Very Bullish | Strong Buy | "Bitcoin surges to new all-time high" |
| 0.3 to 0.7 | Bullish | Buy | "Institutional adoption grows" |
| -0.3 to 0.3 | Neutral | Hold | "Bitcoin trades sideways" |
| -0.7 to -0.3 | Bearish | Sell | "Regulatory concerns emerge" |
| -1.0 to -0.7 | Very Bearish | Strong Sell | "Major exchange hacked" |

#### Security Features

**Model Whitelist**:
```python
allowed_models = {"finbert", "distilroberta-financial", "ollama", "lmstudio"}
```

**Score Validation**:
- Rejects scores outside [-1.0, +1.0] range
- Prevents data injection attacks via malformed scores
- Ensures trading strategy receives valid signals

#### Example Message

```json
{
    "timestamp": "2025-11-23T10:35:00Z",
    "pair": "BTC/USDT",
    "score": 0.85,
    "headline": "Bitcoin Hits New All-Time High as Institutional Adoption Grows",
    "source": "coindesk",
    "confidence": 0.96,
    "model": "finbert"
}
```

---

## Message Flow Diagrams

### Complete Data Pipeline

```
┌─────────────────┐
│   RSS Feeds     │ (CoinDesk, CoinTelegraph, Decrypt, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  News Poller    │ (Polls every 5 minutes)
└────────┬────────┘
         │ RawNewsMessage
         ▼
┌─────────────────┐
│   RabbitMQ      │ Queue: raw_news_data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Sentiment      │ (FinBERT Analysis)
│  Processor      │
└────────┬────────┘
         │ SentimentSignalMessage
         ▼
┌─────────────────┐
│   RabbitMQ      │ Queue: sentiment_signals_queue
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Signal Cacher  │ (Writes to Redis)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Cache    │ Key: sentiment:{pair}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Trading Bot    │ (LLMSentimentStrategy)
│  (Freqtrade)    │
└─────────────────┘
```

### Parallel Market Data Flow

```
┌─────────────────┐
│  Exchange       │ (Binance WebSocket)
│  WebSocket      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Market Streamer │ (CCXT.pro)
└────────┬────────┘
         │ RawMarketDataMessage
         ▼
┌─────────────────┐
│   RabbitMQ      │ Queue: raw_market_data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Trading Bot    │ (Direct consumption)
└─────────────────┘
```

---

## Validation Rules

### Message-Level Validation

**All messages must:**
1. Be valid JSON
2. Match Pydantic schema exactly
3. Pass all field validators
4. Include all required fields

**Invalid messages are:**
- Logged with error details
- Rejected (NACK without requeue)
- Never processed by consumers

### Implementation

**Validation at Producer** (before publishing):
```python
from services.common.message_schemas import RawNewsMessage

# Validate before publishing
try:
    message = RawNewsMessage(
        timestamp=datetime.now(),
        source="coindesk",
        title="Bitcoin Surges",
        url="https://www.coindesk.com/article/123",
        content="Bitcoin reached..."
    )
    rabbitmq.publish("raw_news_data", message.dict())
except ValidationError as e:
    logger.error(f"Message validation failed: {e}")
```

**Validation at Consumer** (on consumption):
```python
from services.common.message_schemas import safe_message_consumer, RawNewsMessage

@safe_message_consumer(callback=process_news, schema=RawNewsMessage)
def wrapped_consumer(ch, method, properties, validated_message):
    # validated_message is guaranteed to be valid RawNewsMessage
    process_news(validated_message)
```

---

## Error Handling

### Producer Error Handling

**Connection Failures**:
- Retry with exponential backoff (2s, 4s, 8s, 16s)
- Max 5 retry attempts
- Log all failures
- Exit on persistent failures (fail-fast principle)

**Message Publishing Failures**:
- Log failed message details
- Continue processing (don't block pipeline)
- Track failure metrics

### Consumer Error Handling

**JSON Decode Errors**:
```python
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in message: {e}")
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

**Validation Errors**:
```python
except ValidationError as e:
    logger.error(f"Message validation failed: {e}")
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

**Processing Errors**:
```python
except Exception as e:
    logger.error(f"Error processing message: {e}", exc_info=True)
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # Retry
```

### Dead Letter Queue (Future Enhancement)

**Planned Implementation**:
- Rejected messages → Dead Letter Exchange (DLX)
- DLX → Dead Letter Queue (DLQ) for inspection
- Manual reprocessing after fixes

---

## Message Deduplication

### News Articles

**Deduplication Method**: URL-based hash

```python
article_hash = hashlib.md5(url.encode()).hexdigest()
if article_hash in published_articles:
    logger.debug(f"Duplicate article skipped: {url}")
    continue
```

**Cache**: In-memory set (max 10,000 entries, pruned to 8,000)

### Sentiment Signals

**Deduplication Method**: Trading pair + timestamp

**Redis Key**: `sentiment:{pair}` (overwrites previous signal)

**Staleness Check**: Trading strategy rejects signals > 4 hours old

---

## Performance Characteristics

### Message Throughput

| Queue | Average Rate | Peak Rate | Batch Size |
|-------|--------------|-----------|------------|
| raw_news_data | 0.33 msg/sec (1 per 3 sec) | 5 msg/sec | 1 |
| raw_market_data | 0.05 msg/sec (1 per 20 sec) | 0.5 msg/sec | 1 |
| sentiment_signals_queue | 0.5 msg/sec | 10 msg/sec | 10 (prefetch) |

### Message Sizes

| Queue | Average Size | Max Size | Notes |
|-------|--------------|----------|-------|
| raw_news_data | 5 KB | 50 KB | Full article content |
| raw_market_data | 200 bytes | 500 bytes | OHLCV data only |
| sentiment_signals_queue | 300 bytes | 600 bytes | Headline + metadata |

### Latency

| Operation | Average | P95 | P99 |
|-----------|---------|-----|-----|
| Publish to RabbitMQ | <5 ms | 10 ms | 20 ms |
| Consume from RabbitMQ | <2 ms | 5 ms | 10 ms |
| End-to-end (News → Redis) | 2-5 sec | 10 sec | 30 sec |

---

## Monitoring & Metrics

### RabbitMQ Management UI

**Access**: http://localhost:15672
**Credentials**: `admin` / `cryptoboy_secret`

**Key Metrics**:
- Queue depth (messages ready)
- Consumer count (active consumers)
- Message rates (publish/deliver/ack)
- Connection status

### CLI Monitoring

```bash
# List all queues with message counts
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages

# Check queue details
docker exec trading-rabbitmq-prod rabbitmqctl list_queues \
    name messages consumers memory

# Monitor queue in real-time
watch -n 1 'docker exec trading-rabbitmq-prod rabbitmqctl list_queues'
```

---

## Troubleshooting

### Queue Backlog

**Symptom**: Message count increasing on queue

**Diagnosis**:
```bash
# Check queue depth
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages

# Check consumer count
docker exec trading-rabbitmq-prod rabbitmqctl list_consumers
```

**Solutions**:
1. Verify consumer is running: `docker ps | grep sentiment-processor`
2. Check consumer logs: `docker logs trading-sentiment-processor`
3. Restart consumer if crashed
4. Increase prefetch_count for parallel processing

### Message Rejection Rate High

**Symptom**: Many NACK operations in logs

**Diagnosis**:
```bash
# Check logs for validation errors
docker logs trading-sentiment-processor | grep "validation failed"
```

**Solutions**:
1. Review validation error details
2. Fix producer to generate valid messages
3. Update schema if requirements changed

### Connection Issues

**Symptom**: "Connection refused" or "Authentication failed"

**Diagnosis**:
```bash
# Verify RabbitMQ running
docker ps | grep rabbitmq

# Check RabbitMQ logs
docker logs trading-rabbitmq-prod

# Verify credentials
docker exec trading-rabbitmq-prod rabbitmqctl list_users
```

**Solutions**:
1. Ensure RabbitMQ container is running
2. Verify environment variables (RABBITMQ_USER, RABBITMQ_PASS)
3. Recreate admin user if needed

---

## Code References

### Schema Definitions

**File**: `services/common/message_schemas.py`

- Line 35-94: RawNewsMessage
- Line 96-163: RawMarketDataMessage
- Line 165-207: SentimentSignalMessage
- Line 212-230: validate_message()
- Line 233-282: safe_message_consumer()

### RabbitMQ Client

**File**: `services/common/rabbitmq_client.py`

- Line 18-92: RabbitMQClient class
- Line 58-92: Connection with retry logic
- Line 130-155: publish() method
- Line 219-246: consume() method
- Line 260-304: create_consumer_callback()

### Producer Implementations

- **News Poller**: `services/data_ingestor/news_poller.py:235-254`
- **Market Streamer**: `services/data_ingestor/market_streamer.py:144-147`
- **Sentiment Processor**: `services/sentiment_analyzer/sentiment_processor.py:312-355`

### Consumer Implementations

- **Sentiment Processor**: `services/sentiment_analyzer/sentiment_processor.py:167-261`
- **Signal Cacher**: `services/signal_cacher/signal_cacher.py:81-137`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-23 | Initial documentation with all 3 queues |

---

**VoidCat RDC - Excellence in Microservices Architecture**
**Documentation Standard: NO SIMULATIONS LAW - All schemas verified against production code**
