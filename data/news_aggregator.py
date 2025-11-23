"""
News Data Aggregator - Fetches and processes crypto news from RSS feeds
"""
import os
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAggregator:
    """Aggregates news from multiple RSS feeds"""

    DEFAULT_FEEDS = {
        'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'cointelegraph': 'https://cointelegraph.com/rss',
        'theblock': 'https://www.theblock.co/rss.xml',
        'decrypt': 'https://decrypt.co/feed',
        'bitcoinmagazine': 'https://bitcoinmagazine.com/.rss/full/'
    }

    def __init__(self, data_dir: str = "data/news_data"):
        """
        Initialize the news aggregator

        Args:
            data_dir: Directory to store news data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load custom feeds from environment or use defaults
        self.feeds = {}
        for name, url in self.DEFAULT_FEEDS.items():
            env_key = f"NEWS_FEED_{name.upper()}"
            self.feeds[name] = os.getenv(env_key, url)

        logger.info(f"Initialized NewsAggregator with {len(self.feeds)} feeds")

    def _clean_html(self, html_text: str) -> str:
        """
        Remove HTML tags and clean text

        Args:
            html_text: Raw HTML text

        Returns:
            Cleaned text
        """
        if not html_text:
            return ""

        soup = BeautifulSoup(html_text, 'html.parser')
        text = soup.get_text(separator=' ')

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _generate_article_id(self, title: str, link: str) -> str:
        """
        Generate unique ID for article

        Args:
            title: Article title
            link: Article URL

        Returns:
            MD5 hash as article ID
        """
        content = f"{title}_{link}".encode('utf-8')
        return hashlib.md5(content).hexdigest()

    def fetch_feed(self, feed_url: str, source_name: str) -> List[Dict]:
        """
        Fetch and parse a single RSS feed

        Args:
            feed_url: URL of the RSS feed
            source_name: Name of the news source

        Returns:
            List of article dictionaries
        """
        articles = []

        try:
            logger.info(f"Fetching feed from {source_name}: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning for {source_name}: {feed.bozo_exception}")

            for entry in feed.entries:
                try:
                    # Extract publish time
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        pub_datetime = datetime(*published[:6])
                    else:
                        pub_datetime = datetime.now()

                    # Extract and clean content
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    content = entry.get('content', [{}])[0].get('value', summary)

                    cleaned_content = self._clean_html(content)

                    article = {
                        'article_id': self._generate_article_id(title, entry.get('link', '')),
                        'source': source_name,
                        'title': title,
                        'link': entry.get('link', ''),
                        'summary': self._clean_html(summary)[:500],  # Limit summary length
                        'content': cleaned_content[:2000],  # Limit content length
                        'published': pub_datetime,
                        'fetched_at': datetime.now()
                    }

                    articles.append(article)

                except Exception as e:
                    logger.error(f"Error parsing entry from {source_name}: {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from {source_name}")

        except Exception as e:
            logger.error(f"Error fetching feed {source_name}: {e}")

        return articles

    def fetch_all_feeds(self) -> pd.DataFrame:
        """
        Fetch articles from all configured feeds

        Returns:
            DataFrame with all articles
        """
        all_articles = []

        for source_name, feed_url in self.feeds.items():
            articles = self.fetch_feed(feed_url, source_name)
            all_articles.extend(articles)

            # Polite delay between feeds
            time.sleep(1)

        if not all_articles:
            logger.warning("No articles fetched from any feed")
            return pd.DataFrame()

        df = pd.DataFrame(all_articles)

        # Remove duplicates based on article_id
        original_count = len(df)
        df = df.drop_duplicates(subset=['article_id']).reset_index(drop=True)
        logger.info(f"Removed {original_count - len(df)} duplicate articles")

        # Sort by publish time
        df = df.sort_values('published', ascending=False).reset_index(drop=True)

        logger.info(f"Total unique articles fetched: {len(df)}")
        return df

    def filter_crypto_keywords(
        self,
        df: pd.DataFrame,
        keywords: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter articles by crypto-related keywords

        Args:
            df: DataFrame with articles
            keywords: List of keywords to filter by

        Returns:
            Filtered DataFrame
        """
        if keywords is None:
            keywords = [
                'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
                'blockchain', 'defi', 'nft', 'altcoin', 'trading', 'exchange',
                'binance', 'coinbase', 'market', 'price', 'bull', 'bear'
            ]

        # Create regex pattern (case insensitive)
        pattern = '|'.join(keywords)

        # Filter based on title or content
        mask = (
            df['title'].str.contains(pattern, case=False, na=False) |
            df['content'].str.contains(pattern, case=False, na=False)
        )

        filtered_df = df[mask].reset_index(drop=True)
        logger.info(f"Filtered to {len(filtered_df)} crypto-related articles")

        return filtered_df

    def save_to_csv(self, df: pd.DataFrame, filename: str = 'news_articles.csv') -> None:
        """
        Save articles to CSV file

        Args:
            df: DataFrame with articles
            filename: Output filename
        """
        if df.empty:
            logger.warning("Cannot save empty DataFrame")
            return

        filepath = self.data_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} articles to {filepath}")

    def load_from_csv(self, filename: str = 'news_articles.csv') -> pd.DataFrame:
        """
        Load articles from CSV file

        Args:
            filename: Input filename

        Returns:
            DataFrame with articles
        """
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return pd.DataFrame()

        df = pd.read_csv(filepath)
        df['published'] = pd.to_datetime(df['published'])
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])

        logger.info(f"Loaded {len(df)} articles from {filepath}")
        return df

    def update_news(
        self,
        filename: str = 'news_articles.csv',
        max_age_days: int = 30
    ) -> pd.DataFrame:
        """
        Update news by fetching new articles and merging with existing

        Args:
            filename: CSV filename
            max_age_days: Maximum age of articles to keep

        Returns:
            Updated DataFrame
        """
        # Fetch new articles
        new_df = self.fetch_all_feeds()

        # Load existing articles
        existing_df = self.load_from_csv(filename)

        # Combine and deduplicate
        if not existing_df.empty and not new_df.empty:
            df = pd.concat([existing_df, new_df], ignore_index=True)
            df = df.drop_duplicates(subset=['article_id']).reset_index(drop=True)
        elif not new_df.empty:
            df = new_df
        else:
            df = existing_df

        # Remove old articles
        if not df.empty and 'published' in df.columns:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            df = df[df['published'] >= cutoff_date].reset_index(drop=True)
            logger.info(f"Removed articles older than {max_age_days} days")

        # Sort by publish time
        if not df.empty:
            df = df.sort_values('published', ascending=False).reset_index(drop=True)
            self.save_to_csv(df, filename)

        return df

    def get_recent_headlines(
        self,
        hours: int = 24,
        filename: str = 'news_articles.csv'
    ) -> List[Dict]:
        """
        Get recent headlines for sentiment analysis

        Args:
            hours: Number of hours to look back
            filename: CSV filename

        Returns:
            List of headline dictionaries
        """
        df = self.load_from_csv(filename)

        if df.empty:
            logger.warning("No news data available")
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_df = df[df['published'] >= cutoff_time]

        headlines = []
        for _, row in recent_df.iterrows():
            headlines.append({
                'article_id': row['article_id'],
                'timestamp': row['published'],
                'headline': row['title'],
                'source': row['source']
            })

        logger.info(f"Retrieved {len(headlines)} headlines from last {hours} hours")
        return headlines


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    aggregator = NewsAggregator()

    # Fetch and update news
    df = aggregator.update_news(max_age_days=7)

    if not df.empty:
        logger.info(f"Total articles: {len(df)}")
        logger.info(f"Date range: {df['published'].min()} to {df['published'].max()}")
        logger.info(f"Sources: {df['source'].unique()}")

        # Get recent headlines
        headlines = aggregator.get_recent_headlines(hours=24)
        logger.info(f"Recent headlines (24h): {len(headlines)}")

        for h in headlines[:5]:
            logger.info(f"  - {h['headline']}")
