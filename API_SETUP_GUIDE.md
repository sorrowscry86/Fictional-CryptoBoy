# VoidCat RDC - CryptoBoy API Setup Guide

**Generated:** October 26, 2025  
**Project:** CryptoBoy Trading System  
**Organization:** VoidCat RDC  
**Developer:** Wykeve Freeman (Sorrow Eternal)

---

## ✅ Configuration Status

### Current Setup Status

| Component | Status | Notes |
|-----------|--------|-------|
| ✅ Environment File | **CONFIGURED** | `.env` file created with production keys |
| ✅ Binance API Keys | **CONFIGURED** | Keys stored securely |
| ⚠️ Binance Access | **RESTRICTED** | Geographic restriction detected |
| ✅ Ollama LLM | **RUNNING** | Using `qwen3:8b` model |
| ⚠️ Telegram Bot | **NOT CONFIGURED** | Optional - notifications disabled |
| ✅ Trading Mode | **DRY RUN** | Paper trading enabled (safe mode) |
| ✅ Directory Structure | **CREATED** | All required directories initialized |

---

## 🔑 API Keys Configured

### Binance API
```
API Key: IevI0LWd...J0M2DVCej9
Secret:  Ik1aIR7c...H5JcMqGyi
Status:  ✅ Valid (Geographic restriction active)
```

**⚠️ GEOGRAPHIC RESTRICTION DETECTED**

Binance is currently blocking API access from your location with error:
```
Service unavailable from a restricted location according to 'b. Eligibility'
```

### Solutions to Geographic Restriction

#### Option 1: Use Binance Testnet (Recommended for Development)
1. Create testnet API keys at: https://testnet.binance.vision/
2. Update `.env`:
   ```bash
   USE_TESTNET=true
   BINANCE_TESTNET_API_KEY=your_testnet_key
   BINANCE_TESTNET_API_SECRET=your_testnet_secret
   ```

#### Option 2: Use VPN/Proxy
1. Connect to VPN in an allowed region
2. Verify access: `python scripts/verify_api_keys.py`

#### Option 3: Alternative Exchanges
Configure one of these CCXT-supported exchanges:
- **Binance.US** (US residents)
- **Kraken** (Global, crypto-friendly)
- **Coinbase Pro** (US, regulated)
- **Bybit** (Global)
- **OKX** (Global)

To switch exchanges, update `config/live_config.json`

---

## 🤖 Ollama LLM Configuration

### Current Setup
```
Host:  http://localhost:11434
Model: qwen3:8b (active)
Status: ✅ Running
```

### Available Models
- `qwen3:8b` ⬅️ Currently configured
- `qwen3:4b`
- `llama2-uncensored:latest`
- `wizard-vicuna-uncensored:latest`

### To Add More Models
```bash
# Pull additional models
docker exec -it trading-bot-ollama ollama pull mistral:7b
docker exec -it trading-bot-ollama ollama pull llama2:13b

# Update .env to use different model
OLLAMA_MODEL=mistral:7b
```

---

## 📱 Telegram Bot Setup (Optional)

Currently **NOT CONFIGURED** - trade notifications are disabled.

### To Enable Telegram Notifications

#### Step 1: Create Telegram Bot
1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

#### Step 2: Get Your Chat ID
1. Start a chat with your new bot
2. Send any message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` in the response

#### Step 3: Update .env
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

#### Step 4: Test
```bash
python monitoring/telegram_notifier.py
```

---

## 🛡️ Security Checklist

- [x] `.env` file created and excluded from git
- [x] API keys masked in logs and verification output
- [x] DRY_RUN mode enabled by default
- [ ] Exchange 2FA enabled (recommended)
- [ ] Read-only API keys (if possible)
- [ ] IP whitelisting on exchange (recommended)
- [ ] Regular API key rotation

### Important Security Notes

1. **Never commit `.env` to version control** - Already protected by `.gitignore`
2. **Use read-only API keys** when possible - No withdrawal permissions needed
3. **Enable IP whitelisting** on your exchange account settings
4. **Start with DRY_RUN=true** - Always test with paper trading first
5. **Monitor for unusual activity** - Set up Telegram alerts
6. **Keep software updated** - Regularly pull latest changes

---

## 🚀 Next Steps

### 1. Resolve Binance Access Issue

Choose one solution from the options above and verify:
```bash
python scripts/verify_api_keys.py
```

### 2. Initialize Data Pipeline

Once API access is working:
```bash
# Run complete data initialization
./scripts/initialize_data_pipeline.sh

# Or manually:
python data/market_data_collector.py
python data/news_aggregator.py
```

### 3. Run Backtest

Test the strategy with historical data:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Run backtest
python backtest/run_backtest.py

# Review results
cat backtest/backtest_reports/backtest_report_*.txt
```

### 4. Paper Trading

Start with simulated trading:
```bash
# Ensure DRY_RUN=true in .env
export DRY_RUN=true

# Start services
docker-compose -f docker-compose.production.yml up -d

# Monitor logs
docker-compose -f docker-compose.production.yml logs -f
```

### 5. Live Trading (Only After Successful Testing)

**⚠️ ONLY proceed after thorough paper trading and backtesting**

```bash
# Set live trading mode
# Edit .env and change: DRY_RUN=false

# Deploy
docker-compose -f docker-compose.production.yml up -d
```

---

## 📊 Verification Commands

### Check API Keys
```bash
python scripts/verify_api_keys.py
```

### Test Binance Connection
```python
import ccxt
exchange = ccxt.binance({
    'apiKey': 'YOUR_KEY',
    'secret': 'YOUR_SECRET'
})
print(exchange.fetch_balance())
```

### Check Ollama Status
```bash
curl http://localhost:11434/api/tags
```

### View Environment Variables
```bash
# View loaded config (keys masked)
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DRY_RUN:', os.getenv('DRY_RUN'))"
```

---

## 🔧 Troubleshooting

### Binance Geographic Restriction
**Error:** "Service unavailable from a restricted location"

**Solutions:**
1. Use Binance Testnet for development
2. Connect via VPN to allowed region
3. Switch to alternative exchange

### Ollama Model Not Found
**Error:** "Model 'mistral:7b' not found"

**Solution:**
```bash
docker exec -it trading-bot-ollama ollama pull mistral:7b
```

### Environment Variables Not Loading
**Solution:**
```bash
# Verify .env exists
ls -la .env

# Check file is being read
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(sorted([k for k in os.environ.keys() if 'BINANCE' in k or 'OLLAMA' in k]))"
```

---

## 📞 Support & Contact

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Community discussions and Q&A  
- **Developer**: @sorrowscry86
- **Project**: CryptoBoy (VoidCat RDC)
- **Contact**: Wykeve Freeman (Sorrow Eternal) - SorrowsCry86@voidcat.org
- **Organization**: VoidCat RDC
- **Support Development**: CashApp $WykeveTF

---

## 📋 Configuration Files Reference

### `.env` - Main configuration (created ✅)
Contains all API keys and runtime parameters

### `config/live_config.json` - Freqtrade live trading config
Exchange-specific settings for production trading

### `config/backtest_config.json` - Backtesting config
Parameters for historical strategy testing

### `risk/risk_parameters.json` - Risk management rules
Stop-loss, position sizing, and risk limits

---

## 🎯 Configuration Summary

```yaml
Project: CryptoBoy Trading System
Version: 1.0.0
Organization: VoidCat RDC

API Keys:
  Binance: ✅ Configured (access restricted)
  Telegram: ⚠️ Not configured (optional)
  
Services:
  Ollama LLM: ✅ Running (qwen3:8b)
  
Trading Mode:
  DRY_RUN: ✅ Enabled (paper trading)
  
Risk Management:
  Stop Loss: 3.0%
  Take Profit: 5.0%
  Risk Per Trade: 1.0%
  Max Open Trades: 3
  
Status: ⚠️ Ready for testing (resolve Binance access first)
```

---

## ⚠️ CRITICAL REMINDERS

1. **ALWAYS START WITH DRY_RUN=true**
2. **Test thoroughly with backtesting before live trading**
3. **Only risk capital you can afford to lose**
4. **Monitor your bot actively - automation ≠ unattended**
5. **Review and understand the strategy before deploying**
6. **Keep API keys secure and never share them**

---

**Built with precision by VoidCat RDC**  
**Wykeve Freeman (Sorrow Eternal) - SorrowsCry86@voidcat.org**

*This configuration was generated on October 26, 2025*
