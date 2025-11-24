"""
CryptoBoy Microservices Package
VoidCat RDC

This package contains the microservices architecture for the CryptoBoy trading system.
The system is composed of 7 services organized into layers:

Infrastructure Layer:
    - RabbitMQ (message broker)
    - Redis (sentiment cache)
    - Ollama (local LLM service)

Data Ingestion Layer:
    - Market Streamer (real-time OHLCV data via WebSocket)
    - News Poller (RSS feed aggregation)

Processing Layer:
    - Sentiment Processor (FinBERT sentiment analysis)
    - Signal Cacher (Redis cache writer)

Trading Layer:
    - Freqtrade Bot (trading strategy execution)

For detailed architecture documentation, see:
    - docs/MICROSERVICES_ARCHITECTURE.md
    - docs/ARCHITECTURE.md
"""

__version__ = "1.0.0"
__author__ = "Wykeve Freeman (Sorrow Eternal) - VoidCat RDC"
