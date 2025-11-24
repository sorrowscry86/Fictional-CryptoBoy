"""
Data Ingestion Layer for CryptoBoy
VoidCat RDC

Real-time data collection services that feed the sentiment analysis pipeline.

Services:
    - News Poller: RSS feed aggregation from trusted crypto news sources
      * Polls 5 sources every 5 minutes
      * Deduplicates articles by URL hash
      * Publishes to raw_news_data queue

    - Market Streamer: Real-time market data via WebSocket (CCXT.pro)
      * Streams OHLCV candles for configured trading pairs
      * Publishes to raw_market_data queue
      * Handles reconnection on network errors

Message Flow:
    RSS Feeds ’ News Poller ’ raw_news_data (RabbitMQ)
    Exchange WebSocket ’ Market Streamer ’ raw_market_data (RabbitMQ)

Configuration:
    Environment variables:
        NEWS_POLL_INTERVAL: Polling frequency in seconds (default: 300)
        TRADING_PAIRS: Comma-separated pairs (default: BTC/USDT,ETH/USDT,BNB/USDT)
        CANDLE_TIMEFRAME: Timeframe for OHLCV candles (default: 1m)
"""

__all__ = ["NewsPoller", "MarketDataStreamer"]
