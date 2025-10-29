# 🚀 CryptoBoy Quick Start Guide
**VoidCat RDC - LLM-Powered Crypto Trading System**

---

## ✅ Current System Status

### Mistral 7B Downloaded ✓
- **Model:** `mistral:7b` (4.4 GB)
- **Status:** Ready for sentiment analysis
- **Backend:** Ollama (localhost:11434)
- **Test Result:** Working perfectly (sentiment score: +0.95 for bullish news)

### API Keys Configured ✓
- **Binance API:** Set (⚠️ geographic restrictions detected)
- **Alternative:** Use Binance Testnet or different exchange
- **Dry Run Mode:** ENABLED (safe testing)

---

## 📌 Quick Commands Reference

### LLM Operations

```bash
# List all models
ollama list

# Test Mistral model
ollama run mistral:7b "Your prompt here"

# Pull additional models
ollama pull llama2:7b
ollama pull codellama:7b

# Check Ollama service
curl http://localhost:11434/api/tags
```

### Trading Bot Operations

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run backtest
python backtest\run_backtest.py

# Verify API keys
python scripts\verify_api_keys.py

# Initialize data pipeline
.\scripts\initialize_data_pipeline.sh

# Start services (development)
docker-compose up -d

# Start production deployment
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose logs -f trading-bot

# Stop all services
docker-compose down
```

### Data Operations

```bash
# Collect market data
python -c "from data.market_data_collector import MarketDataCollector; MarketDataCollector().collect_historical_data('BTC/USDT', days=365)"

# Aggregate news
python -c "from data.news_aggregator import NewsAggregator; NewsAggregator().fetch_all_feeds()"

# Validate data
python -c "from data.data_validator import DataValidator; DataValidator().validate_all()"
```

---

## 🎯 LM Studio Setup (Optional - 3x Faster)

### Why LM Studio?
- **3x faster inference** than Ollama
- **Better GPU utilization** (85-95% vs 60-70%)
- **Lower memory usage** (4-5 GB vs 6 GB)
- **OpenAI-compatible API**

### Installation Steps

1. **Download LM Studio**
   - Visit: https://lmstudio.ai/
   - Download for Windows
   - Install and launch

2. **Download Mistral Model**
   - Click "Search" tab
   - Search: `mistral-7b-instruct`
   - Download: `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` (Q4_K_M)
   - Size: ~4 GB

3. **Load Model**
   - Click "Chat" tab
   - Select downloaded model
   - Click "Load Model"

4. **Start Server**
   - Click "Local Server" tab
   - Click "Start Server"
   - Port: 1234
   - URL: http://localhost:1234

5. **Test Integration**
   ```bash
   python -c "from llm.lmstudio_adapter import test_lmstudio; test_lmstudio()"
   ```

6. **Enable in Config**
   Edit `.env`:
   ```bash
   USE_LMSTUDIO=true
   ```

**Full Guide:** `docs/LMSTUDIO_SETUP.md`

---

## 🔧 Configuration Files

### `.env` - Main Configuration
```bash
# Key settings to verify:
DRY_RUN=true                    # Always start with dry run
OLLAMA_MODEL=mistral:7b         # Model we just installed
BINANCE_API_KEY=<your_key>      # Set ✓
SENTIMENT_BUY_THRESHOLD=0.7     # Bullish threshold
SENTIMENT_SELL_THRESHOLD=-0.5   # Bearish threshold
```

### `config/backtest_config.json`
- Backtest parameters
- Historical data settings
- Performance metrics thresholds

### `config/live_config.json`
- Live trading configuration
- Exchange settings
- Risk parameters

---

## ⚠️ Important Notes

### Geographic Restrictions
Your Binance API keys work but are blocked by geographic restrictions.

**Solutions:**
1. **Use Testnet** (recommended for testing)
   ```bash
   # In .env
   USE_TESTNET=true
   ```

2. **Alternative Exchanges:**
   - Binance.US (if in USA)
   - Kraken
   - Coinbase Pro
   - OKX

3. **VPN** (use at your own risk)

### Safety First
- ✅ DRY_RUN is enabled (paper trading)
- ✅ No real money at risk
- ✅ All tests run in simulation
- ⚠️ Only switch to live after successful backtesting

---

## 📊 Next Steps

### 1. Run Your First Backtest

```bash
# Activate environment
.\venv\Scripts\Activate.ps1

# Run backtest
python backtest\run_backtest.py

# View results
cat backtest\backtest_reports\backtest_report_*.txt
```

**Look for:**
- Sharpe Ratio > 1.0
- Max Drawdown < 20%
- Win Rate > 50%
- Profit Factor > 1.5

### 2. Initialize Data Pipeline

```bash
.\scripts\initialize_data_pipeline.sh
```

This will:
- Download 365 days of historical data
- Collect crypto news from RSS feeds
- Analyze sentiment using Mistral 7B
- Generate trading signals

### 3. Test Sentiment Analysis

```python
python -c "
from llm.sentiment_analyzer import analyze_sentiment
text = 'Bitcoin surges to new highs on ETF approval'
score = analyze_sentiment(text)
print(f'Sentiment Score: {score}')
"
```

Expected: Score between +0.7 and +1.0

### 4. Monitor in Dry Run

```bash
# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f trading-bot

# Check Telegram (if configured)
```

### 5. Optimize and Tune

Edit strategy parameters in `strategies/llm_sentiment_strategy.py`:
- Sentiment thresholds
- Risk parameters
- Technical indicator settings

---

## 🔍 Verification Checklist

- [x] Mistral 7B model downloaded (4.4 GB)
- [x] Ollama service running
- [x] API keys configured in `.env`
- [x] DRY_RUN enabled for safety
- [x] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Backtest executed successfully
- [ ] Data pipeline initialized
- [ ] Docker services tested
- [ ] LM Studio installed (optional)

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Complete system overview |
| `QUICKSTART.md` | This guide |
| `docs/LMSTUDIO_SETUP.md` | LM Studio integration |
| `config/backtest_config.json` | Backtest parameters |
| `config/live_config.json` | Live trading config |

---

## 🆘 Troubleshooting

### Ollama Not Responding
```bash
# Restart Ollama service
# Windows: Restart Ollama app
# Check service
curl http://localhost:11434/api/tags
```

### Model Not Found
```bash
ollama list                    # Verify model installed
ollama pull mistral:7b         # Reinstall if needed
```

### API Connection Issues
```bash
# Test Binance connection
python -c "import ccxt; exchange = ccxt.binance(); print(exchange.fetch_ticker('BTC/USDT'))"

# Use testnet
# Edit .env: USE_TESTNET=true
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 💡 Tips & Best Practices

### Model Selection
- **Fast**: `mistral:7b` (Q4 quantization)
- **Balanced**: `mistral:7b` (default) ✓ Current
- **Accurate**: `llama2:13b` (requires more RAM)

### Performance Optimization
1. Use LM Studio for production (3x faster)
2. Enable caching in `.env`
3. Adjust `SENTIMENT_SMOOTHING_WINDOW` to reduce noise
4. Use higher timeframes (4h, 1d) for less signal noise

### Risk Management
- Start with small `STAKE_AMOUNT` ($10-50)
- Keep `MAX_OPEN_TRADES` low (2-3)
- Set conservative `STOP_LOSS_PERCENTAGE` (2-3%)
- Enable `MAX_DAILY_LOSS_PERCENTAGE` (5%)

---

## 📞 Support & Contact

**VoidCat RDC**
- **Developer:** Wykeve Freeman (Sorrow Eternal)
- **Email:** SorrowsCry86@voidcat.org
- **GitHub:** @sorrowscry86
- **Support Development:** CashApp $WykeveTF

**Resources:**
- GitHub Issues: Report bugs or request features
- Discussions: Community Q&A
- Documentation: Full guides in `docs/`

---

## ⚡ Advanced Features

### Multi-Model Ensemble
Run multiple LLMs and aggregate sentiment:
```python
from llm.lmstudio_adapter import UnifiedLLMClient
client = UnifiedLLMClient(prefer_lmstudio=True)
```

### Custom News Sources
Add feeds to `.env`:
```bash
NEWS_FEED_CUSTOM=https://your-source.com/rss
```

### Telegram Alerts
1. Create bot with @BotFather
2. Get chat ID
3. Update `.env`
4. Receive trade notifications

### Web Dashboard (Roadmap)
- Real-time portfolio tracking
- Performance charts
- Live sentiment feed
- Trade history

---

**🚀 You're Ready to Trade!**

Start with backtesting, verify performance, then deploy in dry-run mode.  
Only switch to live trading after thorough testing and validation.

**Remember:** Crypto trading involves risk. Never invest more than you can afford to lose.

---

**Built with ❤️ by VoidCat RDC**

*Excellence in every line of code.*
