---
description: Repository Information Overview
alwaysApply: true
---

# LLM-Powered Crypto Trading Bot Information

## Summary
An automated cryptocurrency trading system combining LLM-based sentiment analysis from Ollama with technical indicators using Freqtrade. Integrates news aggregation, risk management, and Telegram notifications for production-ready paper and live trading.

## Structure
```
crypto-trading-bot/
├── config/                    # Live and backtest configuration
│   ├── backtest_config.json
│   └── live_config.json
├── data/                      # Market data & news aggregation
│   ├── market_data_collector.py
│   ├── news_aggregator.py
│   └── data_validator.py
├── llm/                       # LLM integration & sentiment
│   ├── model_manager.py
│   ├── sentiment_analyzer.py
│   └── signal_processor.py
├── strategies/                # Trading strategies
│   └── llm_sentiment_strategy.py
├── backtest/                  # Backtesting framework
│   └── run_backtest.py
├── risk/                      # Risk management
├── monitoring/                # Telegram notifications
├── scripts/                   # Setup & utility scripts
├── Dockerfile & docker-compose.yml
├── requirements.txt
└── .env configuration
```

## Language & Runtime
**Language**: Python 3.10
**Runtime**: Python 3.10-slim (Docker)
**Build System**: Docker/Docker Compose
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- **freqtrade** (≥2023.12): Core trading framework with backtesting
- **pandas** (≥1.5.0), **numpy** (≥1.24.0): Data processing
- **ta** (≥0.10.0), **ta-lib** (≥0.4.0): Technical analysis indicators
- **ccxt** (≥4.1.0), **python-binance** (≥1.0.0): Exchange APIs
- **feedparser** (≥6.0.0), **beautifulsoup4** (≥4.11.0): News aggregation
- **python-telegram-bot** (≥20.0): Notifications
- **httpx** (≥0.24.0), **aiohttp** (≥3.9.0): LLM HTTP clients
- **python-dotenv** (≥1.0.0), **pyyaml** (≥6.0): Configuration

**Development Dependencies**:
- **pytest** (≥7.4.0), **pytest-cov** (≥4.1.0): Testing framework

## Build & Installation
```bash
# Setup environment (Unix/Linux)
./scripts/setup_environment.sh

# Windows PowerShell
.\start_cryptoboy.ps1

# Docker deployment (Recommended)
docker-compose -f docker-compose.production.yml up -d

# Install dependencies
pip install -r requirements.txt
```

## Docker Configuration
**Dockerfile**: `Dockerfile` - Python 3.10-slim with TA-Lib compilation from source
**Services**:
- **Main Trading Bot**: Python application running freqtrade strategy
- **Ollama**: LLM service on port 11434 for sentiment analysis
**Volumes**: `ollama_models:/root/.ollama` for persistent model storage
**Health Checks**: Both services configured with 30-40s startup and 30s interval checks

## Main Entry Points
- **Trading**: `scripts/launch_paper_trading.py` - Paper trading startup
- **Data Pipeline**: `scripts/run_data_pipeline.py` - Market data & news collection
- **Backtesting**: `backtest/run_backtest.py` - Strategy performance analysis
- **Monitoring**: `scripts/monitor_trading.py` - Real-time trade monitoring
- **Configuration**: `scripts/verify_api_keys.py` - API validation

## Configuration Files
**Exchange Config**: `config/live_config.json` - Freqtrade main configuration
**Environment**: `.env` - API keys, LLM host/model, risk parameters, Telegram tokens
**Strategy**: `strategies/llm_sentiment_strategy.py` - Entry/exit logic with sentiment thresholds

## Testing
**Framework**: pytest with coverage (pytest ≥7.4.0, pytest-cov ≥4.1.0)
**Configuration**: Standard pytest defaults (no pytest.ini present)
**Run Command**:
```bash
pytest tests/
pytest --cov=. --cov-report=html
```
**Status**: Test directory structure planned; implement unit tests for each module

## Key Technologies
- **Freqtrade**: Production trading framework with backtesting engine
- **Ollama**: Local LLM for offline sentiment analysis (mistral:7b default)
- **CCXT**: Unified cryptocurrency exchange interface
- **TA-Lib**: Technical analysis library (compiled during Docker build)
- **Telegram Bot API**: Real-time notifications for trades and alerts
