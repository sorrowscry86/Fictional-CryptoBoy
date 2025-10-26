#!/bin/bash
# Initialize Data Pipeline - Phase 2: Collect market and news data

set -e

echo "================================================"
echo "LLM Crypto Trading Bot - Data Pipeline Setup"
echo "================================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Activate virtual environment if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

echo -e "${YELLOW}Step 1: Collecting market data (this may take a while)...${NC}"
python -c "
from data.market_data_collector import MarketDataCollector
from dotenv import load_dotenv
load_dotenv()

collector = MarketDataCollector()
symbols = ['BTC/USDT', 'ETH/USDT']

for symbol in symbols:
    print(f'Fetching data for {symbol}...')
    df = collector.update_data(symbol, timeframe='1h', days=365)
    if not df.empty:
        print(f'✓ {symbol}: {len(df)} candles collected')
    else:
        print(f'✗ {symbol}: Failed to collect data')
"
echo -e "${GREEN}✓ Market data collection complete${NC}"
echo ""

echo -e "${YELLOW}Step 2: Aggregating news data...${NC}"
python -c "
from data.news_aggregator import NewsAggregator
from dotenv import load_dotenv
load_dotenv()

aggregator = NewsAggregator()
df = aggregator.update_news(max_age_days=30)

if not df.empty:
    print(f'✓ Collected {len(df)} news articles')
    print(f'Date range: {df[\"published\"].min()} to {df[\"published\"].max()}')
else:
    print('✗ Failed to collect news data')
"
echo -e "${GREEN}✓ News data collection complete${NC}"
echo ""

echo -e "${YELLOW}Step 3: Analyzing sentiment with LLM...${NC}"
python -c "
import pandas as pd
from llm.sentiment_analyzer import SentimentAnalyzer
from data.news_aggregator import NewsAggregator
from dotenv import load_dotenv
import os
load_dotenv()

# Load news data
aggregator = NewsAggregator()
df = aggregator.load_from_csv('news_articles.csv')

if not df.empty:
    # Analyze sentiment
    model_name = os.getenv('OLLAMA_MODEL', 'mistral:7b')
    analyzer = SentimentAnalyzer(model_name=model_name)

    print(f'Analyzing sentiment for {len(df)} articles...')
    df_with_sentiment = analyzer.analyze_dataframe(df, max_workers=4)

    # Save results
    analyzer.save_sentiment_scores(df_with_sentiment, 'data/news_with_sentiment.csv')
    print(f'✓ Sentiment analysis complete')
else:
    print('No news data found')
"
echo -e "${GREEN}✓ Sentiment analysis complete${NC}"
echo ""

echo -e "${YELLOW}Step 4: Processing signals...${NC}"
python -c "
import pandas as pd
from llm.signal_processor import SignalProcessor
from dotenv import load_dotenv
load_dotenv()

processor = SignalProcessor()

# Load sentiment data
try:
    df = pd.read_csv('data/news_with_sentiment.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Aggregate to 1-hour timeframe
    df_aggregated = processor.aggregate_signals(df, timeframe='1H')

    # Calculate rolling sentiment
    df_rolling = processor.calculate_rolling_sentiment(df_aggregated, window_hours=24)

    # Create trading signals
    df_signals = processor.create_trading_signals(df_rolling)

    # Export
    processor.export_signals_csv(df_signals, 'sentiment_signals.csv')

    print(f'✓ Processed {len(df_signals)} signal periods')

    # Summary
    summary = processor.generate_signal_summary(df_signals)
    print(f'Signal summary: {summary}')
except Exception as e:
    print(f'Error processing signals: {e}')
"
echo -e "${GREEN}✓ Signal processing complete${NC}"
echo ""

echo -e "${YELLOW}Step 5: Validating data quality...${NC}"
python -c "
from data.data_validator import DataValidator
from data.market_data_collector import MarketDataCollector
import pandas as pd

validator = DataValidator()
collector = MarketDataCollector()

# Validate market data
df_market = collector.load_from_csv('BTC/USDT', '1h')
if not df_market.empty:
    results = validator.validate_ohlcv_integrity(df_market)
    print(f'Market data validation: {\"PASS\" if results[\"valid\"] else \"FAIL\"}')

# Load sentiment data
try:
    df_sentiment = pd.read_csv('data/sentiment_signals.csv')
    df_sentiment['timestamp'] = pd.to_datetime(df_sentiment['timestamp'])

    # Generate report
    report = validator.generate_quality_report(df_market, df_sentiment)
    print('✓ Quality report generated: data/data_quality_report.txt')
except:
    print('⚠ Could not validate sentiment data')
"
echo -e "${GREEN}✓ Data validation complete${NC}"
echo ""

echo "================================================"
echo -e "${GREEN}Data pipeline initialization complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review data quality report: cat data/data_quality_report.txt"
echo "2. Run backtesting: ./scripts/run_backtest.sh"
echo ""
