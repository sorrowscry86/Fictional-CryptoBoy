# LLM-Powered Crypto Trading Bot

An automated cryptocurrency trading system that combines **LLM-based sentiment analysis** with technical indicators using Freqtrade.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ⚠️ DISCLAIMER

**IMPORTANT:** Cryptocurrency trading involves substantial risk of loss. This software is provided for educational and research purposes only. Never risk more capital than you can afford to lose. The authors are not responsible for any financial losses incurred.

**Always start with:**
1. Paper trading (dry run mode)
2. Small amounts you can afford to lose
3. Thorough backtesting on historical data

---

## 🎯 Features

### Core Capabilities
- **LLM Sentiment Analysis**: Uses Ollama (local LLM) to analyze crypto news sentiment
- **Technical Indicators**: RSI, MACD, EMA, Bollinger Bands integration
- **Risk Management**: Position sizing, stop-loss, take-profit, correlation checks
- **Backtesting**: Comprehensive backtesting with performance metrics
- **Telegram Alerts**: Real-time notifications for trades, P&L, and alerts
- **Docker Deployment**: Production-ready containerized deployment

### Architecture
```
┌─────────────────┐
│  News Sources   │  (CoinDesk, CoinTelegraph, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ News Aggregator │  Collects & deduplicates articles
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM (Ollama)    │  Sentiment analysis (-1.0 to +1.0)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Signal Processor│  Aggregates & smooths signals
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ Freqtrade       │◄─────┤ Market Data  │
│ Strategy        │      │ (Binance)    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│ Risk Manager    │  Position sizing, limits
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Exchange        │  Execute trades
└─────────────────┘
```

---

## 📋 Prerequisites

- **Python 3.9+**
- **Docker & Docker Compose**
- **Binance Account** (or other CCXT-supported exchange)
- **Telegram Bot** (optional, for notifications)
- **~4GB RAM** for LLM model
- **~10GB disk space** for data and models

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/crypto-trading-bot.git
cd crypto-trading-bot

# Run complete setup (recommended)
./scripts/setup_environment.sh
```

### 2. Configure API Keys

Edit `.env` file with your credentials:

```bash
# Exchange API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b

# Trading
DRY_RUN=true  # ALWAYS START WITH DRY RUN
```

### 3. Initialize Data Pipeline

```bash
# Collect market data and news
./scripts/initialize_data_pipeline.sh
```

This will:
- Download 365 days of BTC/USDT and ETH/USDT data
- Aggregate news from RSS feeds
- Analyze sentiment using LLM
- Generate trading signals
- Validate data quality

### 4. Run Backtest

```bash
source venv/bin/activate
python backtest/run_backtest.py
```

Review the backtest report:
```bash
cat backtest/backtest_reports/backtest_report_*.txt
```

**Target Metrics:**
- Sharpe Ratio > 1.0
- Max Drawdown < 20%
- Win Rate > 50%
- Profit Factor > 1.5

### 5. Deploy (Paper Trading)

```bash
# Start with paper trading (simulated)
export DRY_RUN=true
docker-compose -f docker-compose.production.yml up -d

# Monitor logs
docker-compose -f docker-compose.production.yml logs -f
```

### 6. Live Trading (Optional)

**⚠️ ONLY after successful paper trading**

```bash
# Edit .env and set DRY_RUN=false
export DRY_RUN=false

# Deploy
docker-compose -f docker-compose.production.yml up -d
```

---

## 📊 Strategy Details

### Entry Conditions (BUY)

The strategy enters a long position when:

1. **Sentiment Score > 0.7** (strong bullish sentiment)
2. **EMA Short > EMA Long** (upward momentum)
3. **RSI** between 30 and 70 (not overbought)
4. **MACD > MACD Signal** (bullish crossover)
5. **Volume > Average Volume**
6. **Price < Upper Bollinger Band** (not overextended)

### Exit Conditions (SELL)

Exit when:

1. **Sentiment Score < -0.5** (bearish sentiment)
2. **EMA Short < EMA Long AND RSI > 70** (weakening)
3. **MACD < MACD Signal** (bearish crossover)
4. **Take Profit: 5%** (default)
5. **Stop Loss: 3%** (default)

### Risk Management

- **Position Size**: 1-2% risk per trade
- **Max Open Positions**: 3
- **Max Daily Trades**: 10
- **Stop Loss**: Trailing 3%
- **Daily Loss Limit**: 5%

---

## 📁 Project Structure

```
crypto-trading-bot/
├── config/                    # Configuration files
│   ├── backtest_config.json
│   └── live_config.json
├── data/                      # Data storage
│   ├── market_data_collector.py
│   ├── news_aggregator.py
│   └── data_validator.py
├── llm/                       # LLM integration
│   ├── model_manager.py
│   ├── sentiment_analyzer.py
│   └── signal_processor.py
├── strategies/                # Trading strategies
│   └── llm_sentiment_strategy.py
├── backtest/                  # Backtesting
│   └── run_backtest.py
├── risk/                      # Risk management
│   └── risk_manager.py
├── monitoring/                # Alerts & monitoring
│   └── telegram_notifier.py
├── scripts/                   # Automation scripts
│   ├── setup_environment.sh
│   ├── initialize_data_pipeline.sh
│   └── run_complete_pipeline.sh
├── docker-compose.yml         # Ollama service
├── docker-compose.production.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration

### Exchange Configuration

Edit `config/live_config.json`:

```json
{
  "exchange": {
    "name": "binance",
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_API_SECRET}",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"]
  }
}
```

### Strategy Parameters

Edit `strategies/llm_sentiment_strategy.py`:

```python
# Sentiment thresholds
sentiment_buy_threshold = 0.7
sentiment_sell_threshold = -0.5

# Risk parameters
stoploss = -0.03  # 3% stop loss
minimal_roi = {
    "0": 0.05,    # 5% profit target
    "30": 0.03,
    "60": 0.02
}
```

### Risk Parameters

Edit `risk/risk_parameters.json`:

```json
{
  "stop_loss_percentage": 3.0,
  "risk_per_trade_percentage": 1.0,
  "max_daily_trades": 10,
  "max_open_positions": 3
}
```

---

## 📈 Monitoring

### Telegram Notifications

The bot sends notifications for:
- 📈 New trade entries
- 📉 Trade exits
- 💰 Portfolio updates (hourly)
- ⚠️ Risk alerts
- 🚨 System errors

### API Monitoring

Access the Freqtrade API:
```
http://localhost:8080
```

### Logs

```bash
# Real-time logs
docker-compose -f docker-compose.production.yml logs -f trading-bot

# Specific service
docker-compose logs -f ollama
```

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/
```

### Backtest Different Periods

```bash
python backtest/run_backtest.py --timerange 20230101-20231231
```

### Test Telegram

```bash
python monitoring/telegram_notifier.py
```

---

## 🛠️ Development

### Adding New Strategies

1. Create new strategy file in `strategies/`
2. Inherit from `IStrategy`
3. Implement `populate_indicators`, `populate_entry_trend`, `populate_exit_trend`
4. Update config to use new strategy

### Adding News Sources

Edit `data/news_aggregator.py`:

```python
DEFAULT_FEEDS = {
    'your_source': 'https://example.com/rss',
}
```

### Custom LLM Models

Download different models:

```bash
docker exec -it trading-bot-ollama ollama pull llama2:13b
```

Update `.env`:
```
OLLAMA_MODEL=llama2:13b
```

---

## 📊 Performance Metrics

The backtest calculates:

- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Gross profit / Gross loss
- **Win Rate**: Percentage of winning trades
- **Average Trade Duration**

---

## 🔒 Security Best Practices

1. **Never commit API keys** to version control
2. **Use read-only API keys** when possible
3. **Enable IP whitelisting** on exchange
4. **Start with paper trading**
5. **Use 2FA on exchange account**
6. **Monitor for unusual activity**
7. **Keep software updated**

---

## 🐛 Troubleshooting

### Ollama Not Responding

```bash
docker-compose restart ollama
docker-compose logs ollama
```

### Model Not Downloaded

```bash
docker exec -it trading-bot-ollama ollama pull mistral:7b
```

### Data Collection Errors

Check API rate limits:
```bash
python -c "from data.market_data_collector import MarketDataCollector; MarketDataCollector().exchange.load_markets()"
```

### Freqtrade Issues

```bash
# Check config
freqtrade show-config --config config/live_config.json

# Test strategy
freqtrade test-strategy --config config/backtest_config.json --strategy LLMSentimentStrategy
```

---

## 📚 Resources

- [Freqtrade Documentation](https://www.freqtrade.io/)
- [Ollama Models](https://ollama.ai/library)
- [Binance API Docs](https://binance-docs.github.io/apidocs/)
- [TA-Lib Indicators](https://ta-lib.org/)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## ⚡ Roadmap

- [ ] Multi-asset portfolio optimization
- [ ] Advanced sentiment: whitepaper analysis
- [ ] Multi-agent LLM framework
- [ ] Machine learning price predictions
- [ ] Automated parameter optimization
- [ ] Web dashboard for monitoring
- [ ] Support for more exchanges

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/crypto-trading-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/crypto-trading-bot/discussions)

---

## ⚠️ Final Warning

**This bot trades with real money.** The developers assume no liability for financial losses. Cryptocurrency markets are highly volatile and risky. Only invest what you can afford to lose completely.

**Always:**
- Start with paper trading
- Test thoroughly with backtesting
- Use proper risk management
- Monitor your bot actively
- Keep learning and improving

---

**Built with ❤️ for the crypto community**

**Disclaimer**: Not financial advice. Do your own research.
