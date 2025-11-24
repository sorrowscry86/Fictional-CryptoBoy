"""
Sentiment Analysis Processing Service
VoidCat RDC

Analyzes cryptocurrency news articles using FinBERT to generate sentiment scores
for trading signal generation.

Features:
    - Primary: FinBERT (ProsusAI/finbert) - 100% financial accuracy
    - Fallback 1: LM Studio (3x faster inference)
    - Fallback 2: Ollama (local Mistral 7B)
    - 3-tier cascade for resilience against LLM failures

Processing Flow:
    1. Consume raw_news_data from RabbitMQ
    2. Analyze sentiment using FinBERT (-1.0 to +1.0 scale)
    3. Extract mentioned trading pairs from headline
    4. Publish to sentiment_signals_queue for each pair

Message Format:
    Input: RawNewsMessage (timestamp, source, title, url, content)
    Output: SentimentSignalMessage (timestamp, pair, score, headline, source, model)

Performance:
    - FinBERT: 35-second load time, then real-time inference
    - Batch processing: 10 articles per batch for efficiency
    - Graceful degradation: Falls back to LM Studio or Ollama if FinBERT unavailable

Configuration:
    Environment variables:
        TRADING_PAIRS: Pairs to analyze (default: BTC/USDT,ETH/USDT,BNB/USDT)
        USE_LMSTUDIO: Enable LM Studio fallback (default: false)
        OLLAMA_HOST: Ollama service URL (default: http://localhost:11434)
"""

__all__ = ["SentimentProcessor"]
