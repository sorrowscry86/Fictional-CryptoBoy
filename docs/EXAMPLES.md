# Examples and Recipes

Practical snippets to use modules directly and to run end-to-end flows.

---

## 1) Collect OHLCV and validate

```python
from data.market_data_collector import MarketDataCollector

collector = MarketDataCollector(exchange_name='coinbase')
df = collector.update_data('BTC/USDT', timeframe='1h', days=60)

if not df.empty and collector.validate_data_consistency(df):
    print('OK:', len(df), 'candles', df['timestamp'].min(), '→', df['timestamp'].max())
```

---

## 2) Aggregate news and preview headlines

```python
from data.news_aggregator import NewsAggregator

news = NewsAggregator()
df = news.update_news(max_age_days=7)
print('Articles:', len(df))
recent = news.get_recent_headlines(hours=24)
for h in recent[:5]:
    print(h['timestamp'], h['source'], '-', h['headline'])
```

---

## 3) Analyze sentiment with FinBERT (primary)

```python
from llm.huggingface_sentiment import HuggingFaceFinancialSentiment

analyzer = HuggingFaceFinancialSentiment('finbert')
text = 'Bitcoin surges after ETF approval as institutions pile in'
score = analyzer.analyze_sentiment(text)
print('Score:', f"{score:+.2f}")
```

Batch:

```python
articles = [
  'Major exchange hacked; millions stolen',
  'ETH upgrade cuts fees by 80% for users',
]
scores = analyzer.analyze_batch(articles)
print(scores)
```

---

## 4) Build trading features from sentiment

```python
import pandas as pd
from llm.signal_processor import SignalProcessor

# Suppose you created data/sentiment_signals.csv from the pipeline
df = pd.read_csv('data/sentiment_signals.csv', parse_dates=['timestamp'])

proc = SignalProcessor()
df_roll = proc.calculate_rolling_sentiment(df, window_hours=24)
df_smooth = proc.smooth_signal_noise(df_roll, method='ema', window=3)
signals = proc.create_trading_signals(df_smooth, bullish_threshold=0.3, bearish_threshold=-0.3)
proc.export_signals_csv(signals, 'data/sentiment_signals_features.csv')
print('Buy signals:', (signals['signal'] == 1).sum())
```

---

## 5) Merge sentiment with OHLCV (no look-ahead)

```python
import pandas as pd
from data.market_data_collector import MarketDataCollector
from llm.signal_processor import SignalProcessor

collector = MarketDataCollector(exchange_name='coinbase')
ohlcv = collector.load_from_csv('BTC/USDT', timeframe='1h')
sent = pd.read_csv('data/sentiment_signals.csv', parse_dates=['timestamp'])

merged = SignalProcessor().merge_with_market_data(sent, ohlcv)
print('Merged rows:', len(merged))
```

---

## 6) Telegram notifications (optional)

```python
from monitoring.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()
if notifier.enabled:
    notifier.send_trade_notification('BUY', 'BTC/USDT', price=67000.0, amount=0.0015, sentiment_score=0.72)
```

---

## 7) Risk manager usage

```python
from risk.risk_manager import RiskManager

risk = RiskManager()
size = risk.calculate_position_size(10_000, entry_price=67000, stop_loss_price=65000)
print('Size BTC:', size)
summary = risk.get_risk_summary()
print(summary)
```

---

## 8) End-to-end pipeline (script)

```powershell
python scripts\run_data_pipeline.py --days 365 --news-age 7
```

Artifacts:
- data/ohlcv_data/*
- data/news_data/news_articles.csv
- data/sentiment_signals.csv

---

## 9) Backtest the strategy

```powershell
python backtest\run_backtest.py
```

After completion, check backtest/backtest_reports/*.txt and user_data/backtest_results/*.json.

---

## 10) LM Studio fallback example

```python
from llm.lmstudio_adapter import UnifiedLLMClient

client = UnifiedLLMClient(prefer_lmstudio=True)
score = client.analyze_sentiment('Circle and Visa announce new crypto settlement pilot')
print('Score:', score)
```
