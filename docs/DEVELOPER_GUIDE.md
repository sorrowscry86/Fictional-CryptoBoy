# Developer Guide

This guide helps contributors understand, run, and extend the CryptoBoy trading system. It covers architecture, local/dev setup, configuration, core flows, and contribution tips.

---

## System overview

CryptoBoy combines financial-news sentiment from LLMs with technical indicators (via Freqtrade) and risk controls to produce automated trades.

Data flow (textual diagram):

1) News sources (RSS) → News Aggregator → cleaned articles (CSV)
2) Articles → Sentiment Analyzer (FinBERT primary; LLM fallback) → sentiment_signals.csv
3) Market OHLCV (Coinbase/Binance via CCXT) → Market Data Collector → CSV
4) Signal Processor → aggregate/smooth → features
5) Freqtrade Strategy (LLMSentimentStrategy) reads signals + indicators → entries/exits
6) Risk Manager enforces position sizing/limits; Telegram Notifier emits alerts

---

## Repository layout (key paths)

- config/: backtest and live configs (exchange, pairs, risk)
- data/: news/market data, plus helpers
- llm/: sentiment backends and adapters (Hugging Face, LM Studio, Ollama)
- strategies/: Freqtrade strategy logic
- backtest/: backtest runner and reports
- monitoring/: Telegram notifier
- scripts/: orchestration utilities (pipelines, monitoring, setup)
- docker-compose*.yml, Dockerfile: containerized deployment

---

## Environment setup (Windows/Powershell)

1) Python and venv
- Install Python 3.10+ and ensure it’s on PATH
- Create venv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Optional local LLM backends
- Ollama: run service; pull a model (e.g., mistral:7b)
- LM Studio: install, load Mistral 7B Instruct, start local server (http://localhost:1234)

3) Configure environment
- Create .env with keys and runtime flags (see README and API_SETUP_GUIDE)
- Start with DRY_RUN=true

4) Docker (production/paper)
- Install Docker Desktop; ensure it’s running
- Launch services:

```powershell
# Dev
docker-compose up -d

# Production/paper
docker-compose -f docker-compose.production.yml up -d
```

---

## Configuration essentials

- Exchange keys: .env, referenced by config/live_config.json
- Sentiment: USE_HUGGINGFACE=true with HUGGINGFACE_MODEL=finbert (primary)
- News feeds: default RSS; override via env NEWS_FEED_* variables
- Strategy thresholds: edit strategies/llm_sentiment_strategy.py (buy/sell, RSI, EMA, ROI)
- Risk: risk/risk_parameters.json (stop-loss, daily loss limit, max open positions)

---

## Core flows

### Data pipeline (scripts/run_data_pipeline.py)
- Step 1: Market data (OHLCV) collection via CCXT
- Step 2: RSS aggregation → news_data/news_articles.csv
- Step 3: Sentiment analysis (FinBERT) → data/sentiment_signals.csv

Usage:

```powershell
# All steps
python scripts\run_data_pipeline.py --days 365 --news-age 7

# Individual steps
python scripts\run_data_pipeline.py --step 1
python scripts\run_data_pipeline.py --step 2
python scripts\run_data_pipeline.py --step 3
```

Artifacts:
- data/ohlcv_data/*_1h.csv
- data/news_data/news_articles.csv
- data/sentiment_signals.csv

### Trading loop (Freqtrade)
- Strategy reads 1h candles, computes indicators (RSI, EMA, MACD, BB)
- Loads latest sentiment ≤ candle time (no look-ahead)
- Entry when sentiment strong and momentum confirms; exit on negative turn or ROI/stop

### Monitoring
- monitoring/telegram_notifier.py emits trade/portfolio/risk alerts (optional)
- scripts/monitor_trading.py shows colorized dashboard (see docs/MONITOR_COLOR_GUIDE.md)

---

## Development tips

- Keep data joins backward-only by timestamp to avoid look-ahead bias
- Prefer FinBERT for financial text; use LM Studio/Ollama as fallback
- Validate OHLCV with data/data_validator.py before backtests
- For backtesting, ensure Freqtrade and TA-Lib are properly installed (Docker image includes TA-Lib)

Testing backtest:

```powershell
python backtest\run_backtest.py
```

---

## Contribution workflow

- Branch from main; small, focused PRs
- Include docstrings for public functions/classes; type hints where possible
- Update docs when changing public behavior or configs
- If you add runtime dependencies, update requirements.txt
- Prefer adding a small script/test to verify new functionality end-to-end

---

## Troubleshooting

- Binance geo-restriction: use testnet or another exchange (see README/API_SETUP_GUIDE)
- LM Studio not responding: ensure Local Server is running and model is loaded
- No signals generated: re-run news + sentiment steps; confirm data/sentiment_signals.csv exists
- Freqtrade errors: confirm config paths and strategy name; inspect container logs

---

## Support & contact

- Issues/Discussions on GitHub
- Developer: @sorrowscry86 — SorrowsCry86@voidcat.org
- Organization: VoidCat RDC
