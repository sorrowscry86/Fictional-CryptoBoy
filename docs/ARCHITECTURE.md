# Architecture Overview

This document explains how CryptoBoy’s components interact in both the data pipeline and the live trading loop.

---

## High-level components

- News Aggregator (`data/news_aggregator.py`): Fetches and cleans RSS articles.
- Sentiment Analyzer (primary: `llm/huggingface_sentiment.py`, fallback: `llm/lmstudio_adapter.py` + Ollama): Produces numerical sentiment scores.
- Market Data Collector (`data/market_data_collector.py`): OHLCV retrieval via CCXT.
- Signal Processor (`llm/signal_processor.py`): Aggregation/smoothing/feature generation; safe timestamp joining.
- Strategy (`strategies/llm_sentiment_strategy.py`): Combines sentiment features and technical indicators for entries/exits.
- Risk Manager (`risk/risk_manager.py`): Enforces sizing/limits; logs risk events.
- Monitoring (`monitoring/telegram_notifier.py`): Optional alerts.

---

## Data pipeline (batch)

1) RSS → News Aggregator → `data/news_data/news_articles.csv`
2) Articles → Sentiment Analyzer (FinBERT) → `data/sentiment_signals.csv`
3) CCXT → Market Data Collector → `data/ohlcv_data/*_1h.csv`
4) Optional: Signal Processor merges/aggregates and exports features

CLI: `python scripts/run_data_pipeline.py --days 365 --news-age 7`

---

## Live trading loop (textual sequence)

1) Freqtrade fetches 1h candles for each whitelisted pair
2) Strategy `bot_loop_start()` reloads sentiment periodically (from CSV)
3) `populate_indicators()` computes RSI/EMA/MACD/BB; calls `_get_sentiment_score()`
   - Sentiment is the latest score at or before candle time (no look-ahead)
4) `populate_entry_trend()` sets `enter_long` when:
   - Sentiment above threshold AND momentum confirms (EMA, MACD) AND RSI not overbought AND volume healthy AND below BB upper
5) Freqtrade submits orders (paper/live) if confirmed by `confirm_trade_entry()`
6) `populate_exit_trend()` sets `exit_long` when sentiment turns negative or momentum weakens; trailing stop/ROI rules also apply
7) Risk Manager may trigger stop-loss/daily loss governance; Notifier sends messages

---

## Look-ahead bias prevention

- Sentiment is merged by backward time alignment only (nearest prior value).
- Strategy enforces timestamp-naive comparisons using pandas Timestamps.
- Signal Processor and Data Validator provide utilities for safe merges and reporting.

---

## Files and artifacts

- News: `data/news_data/news_articles.csv`
- Sentiment: `data/sentiment_signals.csv`
- Market OHLCV: `data/ohlcv_data/*_1h.csv`
- Backtest reports: `backtest/backtest_reports/*.txt`

---

## Deployment notes

- Docker image includes TA-Lib and Freqtrade setup.
- LLM backends:
  - Primary: Hugging Face FinBERT (fast, accurate)
  - Fallbacks: LM Studio (OpenAI API) and Ollama (local LLMs)

---

## Extending

- Add sources: update `NewsAggregator.DEFAULT_FEEDS` or env overrides.
- New strategies: add a file in `strategies/` inheriting from `IStrategy`.
- New features: extend `SignalProcessor` to compute additional aggregates.
