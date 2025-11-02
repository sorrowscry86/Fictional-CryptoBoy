"""
News Poller Service - Continuous news ingestion from RSS feeds
Publishes new articles to RabbitMQ for sentiment analysis
"""
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Set, Dict, Any, List
import feedparser
from bs4 import BeautifulSoup
import re

from services.common.rabbitmq_client import RabbitMQClient
from services.common.logging_config import setup_logging

logger = setup_logging('news-poller')


class NewsPoller:
    """
    Continuous news polling service that fetches RSS feeds and publishes to RabbitMQ
    Tracks seen articles to avoid republishing duplicates
    """

    DEFAULT_FEEDS = {
        'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'cointelegraph': 'https://cointelegraph.com/rss',
        'theblock': 'https://www.theblock.co/rss.xml',
        'decrypt': 'https://decrypt.co/feed',
        'bitcoinmagazine': 'https://bitcoinmagazine.com/.rss/full/'
    }

    def __init__(
        self,
        poll_interval: int = 300,  # 5 minutes
        queue_name: str = 'raw_news_data'
    ):
        """
        Initialize news poller

        Args:
            poll_interval: Seconds between polling cycles
            queue_name: RabbitMQ queue for publishing news
        """
        self.poll_interval = poll_interval
        self.queue_name = queue_name

        # Load feeds from environment or use defaults
        self.feeds = {}
        for name, url in self.DEFAULT_FEEDS.items():
            env_key = f"NEWS_FEED_{name.upper()}"
            self.feeds[name] = os.getenv(env_key, url)

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()
        self.rabbitmq.connect()
        self.rabbitmq.declare_queue(self.queue_name, durable=True)

        # Track published article IDs to avoid duplicates
        self.published_articles: Set[str] = set()

        # Load crypto keywords for filtering
        self.crypto_keywords = self._get_crypto_keywords()

        logger.info(f"Initialized NewsPoller with {len(self.feeds)} feeds")
        logger.info(f"Polling interval: {self.poll_interval}s")
        logger.info(f"Feeds: {', '.join(self.feeds.keys())}")

    @staticmethod
    def _get_crypto_keywords() -> List[str]:
        """Get crypto keywords for filtering"""
        return [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'defi', 'nft', 'altcoin', 'trading', 'exchange',
            'binance', 'coinbase', 'market', 'price', 'bull', 'bear',
            'bnb', 'usdt', 'tether', 'ripple', 'xrp', 'cardano', 'ada',
            'solana', 'sol', 'polkadot', 'dot', 'dogecoin', 'doge'
        ]

    @staticmethod
    def _clean_html(html_text: str) -> str:
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

    @staticmethod
    def _generate_article_id(title: str, link: str) -> str:
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

    def _is_crypto_relevant(self, title: str, content: str) -> bool:
        """
        Check if article is crypto-relevant

        Args:
            title: Article title
            content: Article content

        Returns:
            True if article contains crypto keywords
        """
        text = f"{title} {content}".lower()
        return any(keyword in text for keyword in self.crypto_keywords)

    def _fetch_feed(self, feed_url: str, source_name: str) -> List[Dict[str, Any]]:
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
            logger.debug(f"Fetching feed from {source_name}")
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
                        pub_datetime = datetime.utcnow()

                    # Extract and clean content
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')
                    content = entry.get('content', [{}])[0].get('value', summary)

                    cleaned_content = self._clean_html(content)
                    cleaned_summary = self._clean_html(summary)

                    # Generate article ID
                    article_id = self._generate_article_id(title, link)

                    # Skip if already published
                    if article_id in self.published_articles:
                        continue

                    # Filter for crypto relevance
                    if not self._is_crypto_relevant(title, cleaned_content):
                        logger.debug(f"Skipping non-crypto article: {title[:50]}")
                        continue

                    article = {
                        'type': 'news_article',
                        'article_id': article_id,
                        'source': source_name,
                        'title': title,
                        'link': link,
                        'summary': cleaned_summary[:500],  # Limit summary
                        'content': cleaned_content[:2000],  # Limit content
                        'published': pub_datetime.isoformat(),
                        'fetched_at': datetime.utcnow().isoformat()
                    }

                    articles.append(article)

                except Exception as e:
                    logger.error(f"Error parsing entry from {source_name}: {e}")
                    continue

            logger.debug(f"Fetched {len(articles)} new articles from {source_name}")

        except Exception as e:
            logger.error(f"Error fetching feed {source_name}: {e}")

        return articles

    def _poll_all_feeds(self) -> int:
        """
        Poll all configured feeds and publish new articles

        Returns:
            Number of new articles published
        """
        total_published = 0

        for source_name, feed_url in self.feeds.items():
            try:
                # Fetch articles from feed
                articles = self._fetch_feed(feed_url, source_name)

                # Publish each new article to RabbitMQ
                for article in articles:
                    try:
                        self.rabbitmq.publish(
                            self.queue_name,
                            article,
                            persistent=True,
                            declare_queue=False
                        )

                        # Track as published
                        self.published_articles.add(article['article_id'])
                        total_published += 1

                        logger.info(
                            f"Published article from {source_name}: "
                            f"{article['title'][:60]}..."
                        )

                    except Exception as e:
                        logger.error(f"Failed to publish article: {e}")

                # Polite delay between feeds
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error processing feed {source_name}: {e}", exc_info=True)

        # Limit cache size (keep last 10000 article IDs)
        if len(self.published_articles) > 10000:
            # Remove oldest 2000
            articles_list = list(self.published_articles)
            self.published_articles = set(articles_list[-8000:])
            logger.info("Pruned published articles cache")

        return total_published

    def run(self):
        """Main polling loop"""
        logger.info("News Poller starting...")
        logger.info(f"Will poll every {self.poll_interval} seconds")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                logger.info(f"Starting polling cycle #{cycle_count}")

                try:
                    # Poll all feeds
                    start_time = time.time()
                    published_count = self._poll_all_feeds()
                    elapsed = time.time() - start_time

                    logger.info(
                        f"Cycle #{cycle_count} complete: "
                        f"{published_count} new articles published in {elapsed:.1f}s"
                    )

                except Exception as e:
                    logger.error(f"Error in polling cycle: {e}", exc_info=True)

                # Sleep until next cycle
                logger.info(f"Sleeping for {self.poll_interval}s until next cycle")
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down News Poller...")

        try:
            self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")

        logger.info(f"Total unique articles tracked: {len(self.published_articles)}")


def main():
    """Main function"""
    # Get configuration from environment
    poll_interval = int(os.getenv('NEWS_POLL_INTERVAL', 300))  # 5 minutes default

    # Create and run poller
    poller = NewsPoller(
        poll_interval=poll_interval,
        queue_name='raw_news_data'
    )

    poller.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
