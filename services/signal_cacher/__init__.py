"""
Signal Caching Service
VoidCat RDC

Consumes sentiment signals from RabbitMQ and caches them in Redis for
real-time access by the trading bot strategy.

Features:
    - Consumes sentiment_signals_queue from RabbitMQ
    - Writes to Redis hash structures (sentiment:{pair})
    - Tracks statistics (signals processed, cache updates, errors)
    - Configurable TTL for cache expiry (default: no expiry)

Redis Data Structure:
    Key: sentiment:{pair}  (e.g., sentiment:BTC/USDT)
    Fields:
        - score: Sentiment score (-1.0 to +1.0)
        - timestamp: ISO 8601 timestamp of analysis
        - headline: News headline that generated the signal
        - source: News source (coindesk, cointelegraph, etc.)
        - model: Model used for analysis (finbert, ollama, lmstudio)
        - article_id: Unique article identifier for deduplication

Processing Flow:
    RabbitMQ (sentiment_signals_queue) ’ Signal Cacher ’ Redis (sentiment:{pair})
                                                            “
                                                    Trading Bot reads

Performance:
    - Uses Redis connection pooling (max_connections=50)
    - Prefetch count: 10 (parallel processing)
    - Average latency: <5ms per signal

Configuration:
    Environment variables:
        REDIS_HOST: Redis host (default: redis)
        REDIS_PORT: Redis port (default: 6379)
        CACHE_TTL: Time-to-live in seconds (default: 0 = no expiry)
"""

__all__ = ["SignalCacher"]
