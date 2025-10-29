"""
Integrated Data Pipeline - Market Data, News, Sentiment, and Backtesting
VoidCat RDC - CryptoBoy Trading Bot

This script orchestrates the complete data pipeline:
1. Market Data Collection (Coinbase)
2. News Aggregation (RSS feeds)
3. Sentiment Analysis (FinBERT)
4. Backtest Execution (optional)
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data_collector import MarketDataCollector
from data.news_aggregator import NewsAggregator
from llm.huggingface_sentiment import HuggingFaceFinancialSentiment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrates the complete data pipeline"""

    def __init__(self):
        """Initialize pipeline components"""
        load_dotenv()
        
        # Initialize components
        self.market_collector = MarketDataCollector(
            api_key=os.getenv('COINBASE_API_KEY'),
            api_secret=os.getenv('COINBASE_API_SECRET'),
            data_dir="data/ohlcv_data"
        )
        
        self.news_aggregator = NewsAggregator(data_dir="data/news_data")
        
        self.sentiment_analyzer = HuggingFaceFinancialSentiment(
            model_name="ProsusAI/finbert"
        )
        
        # Configure pairs
        self.trading_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        logger.info("Data pipeline initialized")

    def step1_collect_market_data(self, days: int = 365, timeframe: str = '1h'):
        """
        Step 1: Collect historical market data from Coinbase
        
        Args:
            days: Number of days of history to collect
            timeframe: Candle timeframe
            
        Returns:
            Dictionary of DataFrames by pair
        """
        logger.info("=" * 80)
        logger.info("STEP 1: MARKET DATA COLLECTION")
        logger.info("=" * 80)
        
        market_data = {}
        
        for pair in self.trading_pairs:
            logger.info(f"\nCollecting data for {pair}...")
            
            try:
                # Update (fetch or append new data)
                df = self.market_collector.update_data(
                    symbol=pair,
                    timeframe=timeframe,
                    days=days
                )
                
                if not df.empty:
                    # Validate data
                    is_valid = self.market_collector.validate_data_consistency(df)
                    
                    market_data[pair] = df
                    
                    logger.info(f"✓ {pair}: {len(df)} candles collected")
                    logger.info(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                    logger.info(f"  Validation: {'PASSED' if is_valid else 'FAILED'}")
                else:
                    logger.warning(f"✗ {pair}: No data collected")
                    
            except Exception as e:
                logger.error(f"✗ {pair}: Error - {e}")
                continue
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Market data collection complete: {len(market_data)}/{len(self.trading_pairs)} pairs")
        logger.info(f"{'='*80}\n")
        
        return market_data

    def step2_aggregate_news(self, max_age_days: int = 7):
        """
        Step 2: Aggregate news from RSS feeds
        
        Args:
            max_age_days: Maximum age of articles to keep
            
        Returns:
            DataFrame with news articles
        """
        logger.info("=" * 80)
        logger.info("STEP 2: NEWS AGGREGATION")
        logger.info("=" * 80)
        
        try:
            # Fetch and update news
            df = self.news_aggregator.update_news(
                filename='news_articles.csv',
                max_age_days=max_age_days
            )
            
            if not df.empty:
                logger.info(f"✓ Total articles: {len(df)}")
                logger.info(f"  Date range: {df['published'].min()} to {df['published'].max()}")
                logger.info(f"  Sources: {', '.join(df['source'].unique())}")
                
                # Get recent headlines
                recent = self.news_aggregator.get_recent_headlines(hours=24)
                logger.info(f"  Recent (24h): {len(recent)} headlines")
                
                if recent:
                    logger.info("\n  Sample headlines:")
                    for headline in recent[:5]:
                        logger.info(f"    • {headline['headline'][:80]}...")
            else:
                logger.warning("✗ No news articles collected")
                
        except Exception as e:
            logger.error(f"✗ News aggregation error: {e}")
            df = pd.DataFrame()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"News aggregation complete: {len(df) if not df.empty else 0} articles")
        logger.info(f"{'='*80}\n")
        
        return df

    def step3_analyze_sentiment(self, news_df: pd.DataFrame):
        """
        Step 3: Analyze sentiment of news articles
        
        Args:
            news_df: DataFrame with news articles
            
        Returns:
            DataFrame with sentiment signals
        """
        logger.info("=" * 80)
        logger.info("STEP 3: SENTIMENT ANALYSIS")
        logger.info("=" * 80)
        
        if news_df.empty:
            logger.warning("No news data available for sentiment analysis")
            return pd.DataFrame()
        
        sentiment_signals = []
        
        # Process recent articles (last 48 hours)
        recent_cutoff = datetime.now() - timedelta(hours=48)
        recent_news = news_df[news_df['published'] >= recent_cutoff]
        
        logger.info(f"Analyzing sentiment for {len(recent_news)} recent articles...\n")
        
        for idx, article in recent_news.iterrows():
            try:
                # Analyze headline + summary
                text = f"{article['title']}. {article['summary']}"
                
                sentiment_score = self.sentiment_analyzer.analyze_sentiment(text)
                
                # Determine label
                if sentiment_score > 0.3:
                    label = "BULLISH"
                elif sentiment_score < -0.3:
                    label = "BEARISH"
                else:
                    label = "NEUTRAL"
                
                # Try to match to trading pairs (simple keyword matching)
                matched_pairs = self._match_article_to_pairs(article)
                
                for pair in matched_pairs:
                    sentiment_signals.append({
                        'pair': pair,
                        'timestamp': article['published'],
                        'sentiment_score': sentiment_score,
                        'sentiment_label': label,
                        'source': 'finbert',
                        'article_id': article['article_id'],
                        'headline': article['title'][:100]
                    })
                
                if idx % 10 == 0:
                    logger.info(f"  Processed {idx}/{len(recent_news)} articles...")
                    
            except Exception as e:
                logger.error(f"  Error analyzing article {article.get('article_id', 'unknown')}: {e}")
                continue
        
        # Create DataFrame
        signals_df = pd.DataFrame(sentiment_signals)
        
        if not signals_df.empty:
            # Remove duplicates and sort
            signals_df = signals_df.drop_duplicates(
                subset=['pair', 'article_id']
            ).sort_values('timestamp', ascending=False).reset_index(drop=True)
            
            # Save to CSV
            output_path = Path("data/sentiment_signals.csv")
            signals_df.to_csv(output_path, index=False)
            
            logger.info(f"\n✓ Sentiment analysis complete: {len(signals_df)} signals generated")
            logger.info(f"  Saved to: {output_path}")
            
            # Summary by pair
            logger.info("\n  Signals by pair:")
            for pair in self.trading_pairs:
                pair_signals = signals_df[signals_df['pair'] == pair]
                if not pair_signals.empty:
                    bullish = len(pair_signals[pair_signals['sentiment_label'] == 'BULLISH'])
                    bearish = len(pair_signals[pair_signals['sentiment_label'] == 'BEARISH'])
                    neutral = len(pair_signals[pair_signals['sentiment_label'] == 'NEUTRAL'])
                    avg_score = pair_signals['sentiment_score'].mean()
                    logger.info(f"    {pair}: {len(pair_signals)} signals (↑{bullish} ↓{bearish} →{neutral}) avg={avg_score:.2f}")
        else:
            logger.warning("✗ No sentiment signals generated")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Sentiment analysis complete: {len(signals_df) if not signals_df.empty else 0} signals")
        logger.info(f"{'='*80}\n")
        
        return signals_df

    def _match_article_to_pairs(self, article) -> list:
        """
        Match article to trading pairs based on keywords
        
        Args:
            article: Article row from DataFrame
            
        Returns:
            List of matched pairs
        """
        text = f"{article['title']} {article.get('content', '')}".lower()
        
        matched = []
        
        # Keyword mapping
        keywords = {
            'BTC/USDT': ['bitcoin', 'btc'],
            'ETH/USDT': ['ethereum', 'eth', 'ether'],
            'SOL/USDT': ['solana', 'sol']
        }
        
        for pair, kw_list in keywords.items():
            if any(kw in text for kw in kw_list):
                matched.append(pair)
        
        # If no specific match, apply to all pairs (general crypto news)
        if not matched:
            general_keywords = ['crypto', 'cryptocurrency', 'market', 'trading', 'blockchain']
            if any(kw in text for kw in general_keywords):
                matched = self.trading_pairs.copy()
        
        return matched

    def run_full_pipeline(self, days: int = 365, max_news_age: int = 7):
        """
        Run the complete data pipeline
        
        Args:
            days: Days of market data to collect
            max_news_age: Maximum age of news articles to keep
            
        Returns:
            Dictionary with all results
        """
        logger.info("\n" + "=" * 80)
        logger.info("CRYPTOBOY DATA PIPELINE - VOIDCAT RDC")
        logger.info("=" * 80)
        logger.info(f"Started: {datetime.now()}")
        logger.info(f"Trading Pairs: {', '.join(self.trading_pairs)}")
        logger.info("=" * 80 + "\n")
        
        results = {
            'market_data': None,
            'news_data': None,
            'sentiment_signals': None,
            'success': False
        }
        
        try:
            # Step 1: Market Data
            market_data = self.step1_collect_market_data(days=days)
            results['market_data'] = market_data
            
            # Step 2: News Aggregation
            news_data = self.step2_aggregate_news(max_age_days=max_news_age)
            results['news_data'] = news_data
            
            # Step 3: Sentiment Analysis
            if not news_data.empty:
                sentiment_signals = self.step3_analyze_sentiment(news_data)
                results['sentiment_signals'] = sentiment_signals
            else:
                logger.warning("Skipping sentiment analysis - no news data available")
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results['success'] = False
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Status: {'SUCCESS' if results['success'] else 'FAILED'}")
        logger.info(f"Market Data: {len(results.get('market_data', {}))}/{len(self.trading_pairs)} pairs")
        logger.info(f"News Articles: {len(results.get('news_data', pd.DataFrame()))}")
        logger.info(f"Sentiment Signals: {len(results.get('sentiment_signals', pd.DataFrame()))}")
        logger.info(f"Completed: {datetime.now()}")
        logger.info("=" * 80 + "\n")
        
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CryptoBoy Data Pipeline")
    parser.add_argument('--days', type=int, default=365, help='Days of market data to collect')
    parser.add_argument('--news-age', type=int, default=7, help='Maximum age of news articles (days)')
    parser.add_argument('--step', type=str, choices=['1', '2', '3', 'all'], default='all',
                       help='Run specific step or all steps')
    
    args = parser.parse_args()
    
    pipeline = DataPipeline()
    
    if args.step == '1':
        pipeline.step1_collect_market_data(days=args.days)
    elif args.step == '2':
        pipeline.step2_aggregate_news(max_age_days=args.news_age)
    elif args.step == '3':
        news_df = pipeline.news_aggregator.load_from_csv('news_articles.csv')
        pipeline.step3_analyze_sentiment(news_df)
    else:
        pipeline.run_full_pipeline(days=args.days, max_news_age=args.news_age)
