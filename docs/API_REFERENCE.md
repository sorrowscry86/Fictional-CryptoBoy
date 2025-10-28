# API Reference

Concise reference for key modules, classes, and functions. Types use Python hints; all timestamps are naive pandas Timestamps unless stated.

---

## data.market_data_collector

Class: MarketDataCollector
- Purpose: Fetch, persist, and validate OHLCV data via CCXT
- Init(api_key: str|None = None, api_secret: str|None = None, data_dir: str = "data/ohlcv_data", exchange_name: str = "coinbase")
  - Reads keys from env if not provided
  - exchange_name: any ccxt exchange id (e.g., "binance", "coinbase")

Methods
- get_historical_ohlcv(symbol: str, timeframe: str = '1h', start_date: dt|None = None, end_date: dt|None = None, limit: int = 1000) -> pd.DataFrame
  - Returns columns: [timestamp, open, high, low, close, volume, symbol]
  - Notes: Paginates via since + limit; sleeps by exchange.rateLimit
- fetch_latest_candle(symbol: str, timeframe: str = '1h') -> dict|None
- save_to_csv(df: pd.DataFrame, symbol: str, timeframe: str = '1h') -> None
- load_from_csv(symbol: str, timeframe: str = '1h') -> pd.DataFrame
- update_data(symbol: str, timeframe: str = '1h', days: int = 365) -> pd.DataFrame
  - Appends new data to existing CSV or fetches fresh if none
- validate_data_consistency(df: pd.DataFrame) -> bool

Exceptions: network/CCXT errors are logged and return empty dataframes where applicable.

---

## data.news_aggregator

Class: NewsAggregator
- Purpose: Fetch and clean crypto news articles via RSS
- Init(data_dir: str = "data/news_data")
  - Feeds read from env override: NEWS_FEED_COINDESK, etc.

Methods
- fetch_feed(feed_url: str, source_name: str) -> list[dict]
- fetch_all_feeds() -> pd.DataFrame
- filter_crypto_keywords(df: pd.DataFrame, keywords: list[str]|None = None) -> pd.DataFrame
- save_to_csv(df: pd.DataFrame, filename: str = 'news_articles.csv') -> None
- load_from_csv(filename: str = 'news_articles.csv') -> pd.DataFrame
- update_news(filename: str = 'news_articles.csv', max_age_days: int = 30) -> pd.DataFrame
- get_recent_headlines(hours: int = 24, filename: str = 'news_articles.csv') -> list[dict]

Data columns: [article_id, source, title, link, summary, content, published, fetched_at]

---

## data.data_validator

Class: DataValidator
- Purpose: Validate OHLCV and combined datasets; detect look-ahead bias
- Init(output_dir: str = "data")

Methods
- validate_ohlcv_integrity(df: pd.DataFrame) -> dict
- check_timestamp_alignment(df1, df2, timestamp_col1='timestamp', timestamp_col2='timestamp', tolerance_minutes=60) -> dict
- detect_look_ahead_bias(market_df, sentiment_df, market_timestamp_col='timestamp', sentiment_timestamp_col='timestamp') -> dict
- generate_quality_report(market_df: pd.DataFrame, sentiment_df: pd.DataFrame|None = None, output_file: str = 'data_quality_report.txt') -> str

---

## llm.huggingface_sentiment

Class: HuggingFaceFinancialSentiment
- Purpose: High-accuracy financial sentiment using FinBERT or variants
- Init(model_name: str = 'finbert' | full HF path)

Methods
- analyze_sentiment(text: str, return_probabilities: bool = False) -> float|dict
- analyze_batch(texts: list[str]) -> list[float]

Class: UnifiedSentimentAnalyzer
- Purpose: Prefer HF; fallback to LLM (LM Studio/Ollama via UnifiedLLMClient)
- Init(prefer_huggingface: bool = True, hf_model: str = 'finbert')
- analyze_sentiment(text: str) -> float

---

## llm.lmstudio_adapter

Class: LMStudioAdapter
- Purpose: Simple OpenAI-compatible client for LM Studio local server
- Init(host: str|None = None, model: str|None = None, timeout: int = 30)

Methods
- check_connection() -> bool
- list_models() -> list[str]
- generate(prompt: str, system_prompt: str|None = None, temperature: float = 0.7, max_tokens: int = 500) -> str|None
- analyze_sentiment(text: str, context: str|None = None) -> float|None

Class: UnifiedLLMClient
- Purpose: Pick LM Studio or Ollama (via model_manager + sentiment_analyzer)
- Init(prefer_lmstudio: bool = True)
- analyze_sentiment(text: str, context: str|None = None) -> float|None

---

## llm.sentiment_analyzer

Class: SentimentAnalyzer
- Purpose: Sentiment via Ollama text-generation; numeric extraction
- Init(model_name: str = 'mistral:7b', ollama_host: str = 'http://localhost:11434', timeout: int = 30, max_retries: int = 3)

Methods
- get_sentiment_score(headline: str, context: str = "") -> float
- batch_sentiment_analysis(headlines: list[str|dict], max_workers: int = 4, show_progress: bool = True) -> list[dict]
- analyze_dataframe(df: pd.DataFrame, headline_col='headline', timestamp_col='timestamp', max_workers: int = 4) -> pd.DataFrame
- save_sentiment_scores(df: pd.DataFrame, output_file: str, timestamp_col='timestamp', score_col='sentiment_score') -> None
- test_connection() -> bool

---

## llm.signal_processor

Class: SignalProcessor
- Purpose: Turn raw sentiment into trading features/signals; merge with OHLCV
- Init(output_dir: str = 'data')

Methods
- calculate_rolling_sentiment(df, window_hours=24, timestamp_col='timestamp', score_col='sentiment_score') -> pd.DataFrame
- aggregate_signals(df, timeframe='1H', timestamp_col='timestamp', score_col='sentiment_score', aggregation_method='mean') -> pd.DataFrame
- smooth_signal_noise(df, method='ema', window=3, score_col='sentiment_score') -> pd.DataFrame
- create_trading_signals(df, score_col='sentiment_score', bullish_threshold=0.3, bearish_threshold=-0.3) -> pd.DataFrame
- merge_with_market_data(sentiment_df, market_df, sentiment_timestamp_col='timestamp', market_timestamp_col='timestamp', tolerance_hours=1) -> pd.DataFrame
- export_signals_csv(df: pd.DataFrame, filename='sentiment_signals.csv', columns: list[str]|None = None) -> None
- generate_signal_summary(df: pd.DataFrame) -> dict

---

## monitoring.telegram_notifier

Class: TelegramNotifier
- Purpose: Post trade/system messages to Telegram
- Init(bot_token: str|None = None, chat_id: str|None = None)

Methods
- send_message(message: str, parse_mode: str = 'Markdown', disable_notification: bool = False) -> bool
- send_trade_notification(action: str, pair: str, price: float, amount: float, stop_loss: float|None = None, take_profit: float|None = None, sentiment_score: float|None = None) -> bool
- send_position_close(pair: str, entry_price: float, exit_price: float, amount: float, profit_pct: float, profit_amount: float, duration: str) -> bool
- send_portfolio_update(total_value: float, daily_pnl: float, daily_pnl_pct: float, open_positions: int, today_trades: int) -> bool
- send_risk_alert(alert_type: str, message_text: str, severity: str = 'warning') -> bool
- send_error_alert(error_type: str, error_message: str) -> bool
- send_system_status(status: str, details: dict|None = None) -> bool
- test_connection() -> bool

---

## risk.risk_manager

Class: RiskManager
- Purpose: Position sizing, daily limits, correlation checks, stop-loss enforcement
- Init(config_path: str = 'risk/risk_parameters.json', log_dir: str = 'logs')

Methods
- calculate_position_size(portfolio_value: float, entry_price: float, stop_loss_price: float, risk_per_trade: float|None = None) -> float
- validate_risk_parameters(pair: str, entry_price: float, position_size: float, portfolio_value: float) -> dict
- enforce_stop_loss(pair: str, entry_price: float, current_price: float, position_size: float) -> dict
- check_daily_loss_limit(daily_pnl: float, portfolio_value: float) -> dict
- track_trade(pair: str, entry_price: float, position_size: float, timestamp: datetime|None = None) -> None
- close_position(pair: str, exit_price: float) -> None
- get_risk_summary() -> dict

---

## backtest.run_backtest

Class: BacktestRunner
- Purpose: Manage Freqtrade downloads, backtests, and metrics/reporting
- Init(config_path='config/backtest_config.json', strategy_name='LLMSentimentStrategy', data_dir='user_data/data/binance')

Methods
- download_data(pairs: list[str]|None = None, timeframe: str = '1h', days: int = 365) -> bool
- run_backtest(timerange: str|None = None, timeframe: str = '1h') -> dict|None
- calculate_metrics(results: dict) -> dict
- validate_metrics_threshold(metrics: dict) -> dict
- generate_report(metrics: dict, validation: dict) -> str

---

## strategies.llm_sentiment_strategy

Class: LLMSentimentStrategy(IStrategy)
- Purpose: Combine sentiment with technicals for entries/exits (Freqtrade)
- Key config:
  - timeframe = '1h'
  - minimal_roi, stoploss, trailing
  - thresholds: sentiment_buy_threshold=0.3, sentiment_sell_threshold=-0.3
- Important hooks:
  - bot_start/bot_loop_start: load/refresh sentiment CSV
  - populate_indicators(df, metadata) -> df: computes RSI/EMA/MACD/BB + sentiment
  - populate_entry_trend(df, metadata) / populate_exit_trend(df, metadata)
  - custom_stake_amount(...): boost size when sentiment very strong
  - confirm_trade_entry(...): final sentiment gate
  - custom_exit(...): early exits on reversals / strong profit

Notes
- Sentiment is joined by nearest prior timestamp (no look-ahead). Ensure data/sentiment_signals.csv is up-to-date.

---

## Exceptions & error modes (common)

- Network/API timeouts: methods log and return empty df/None/neutral, continuing execution
- File not found: loaders return empty df with warnings
- Parsing errors: sentiment parsing/HTML cleaning guarded with try/except and warnings

---

## Versioning

APIs are stable per main branch; breaking changes will be documented in release notes and reflected here.
