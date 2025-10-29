"""
Sentiment Processor Service - Consumes news and publishes sentiment signals
Integrates with Ollama LLM for sentiment analysis
"""
import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, List

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.common.rabbitmq_client import RabbitMQClient, create_consumer_callback
from services.common.logging_config import setup_logging
from llm.sentiment_analyzer import SentimentAnalyzer

logger = setup_logging('sentiment-processor')


class SentimentProcessor:
    """
    Sentiment analysis service that processes news articles from RabbitMQ
    Publishes enriched sentiment signals for trading strategies
    """

    # Trading pairs to match articles against
    TRADING_PAIRS = {
        'BTC/USDT': ['bitcoin', 'btc'],
        'ETH/USDT': ['ethereum', 'eth', 'ether'],
        'BNB/USDT': ['binance', 'bnb', 'binance coin'],
    }

    # Sentiment classification thresholds
    SENTIMENT_THRESHOLDS = {
        'very_bullish': 0.7,
        'bullish': 0.3,
        'neutral': (-0.3, 0.3),
        'bearish': -0.3,
        'very_bearish': -0.7
    }

    def __init__(
        self,
        input_queue: str = 'raw_news_data',
        output_queue: str = 'sentiment_signals_queue',
        model_name: str = None,
        ollama_host: str = None
    ):
        """
        Initialize sentiment processor

        Args:
            input_queue: RabbitMQ queue to consume news from
            output_queue: RabbitMQ queue to publish sentiment signals
            model_name: Ollama model name (defaults to env or 'mistral:7b')
            ollama_host: Ollama host URL (defaults to env or 'http://ollama:11434')
        """
        self.input_queue = input_queue
        self.output_queue = output_queue

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()
        self.rabbitmq.connect()
        self.rabbitmq.declare_queue(self.input_queue, durable=True)
        self.rabbitmq.declare_queue(self.output_queue, durable=True)

        # Initialize Sentiment Analyzer
        model = model_name or os.getenv('OLLAMA_MODEL', 'mistral:7b')
        host = ollama_host or os.getenv('OLLAMA_HOST', 'http://ollama:11434')

        self.analyzer = SentimentAnalyzer(
            model_name=model,
            ollama_host=host,
            timeout=30,
            max_retries=3
        )

        # Get custom trading pairs from environment if available
        pairs_env = os.getenv('TRADING_PAIRS', '')
        if pairs_env:
            self.trading_pairs = self._parse_trading_pairs(pairs_env)
        else:
            self.trading_pairs = self.TRADING_PAIRS

        logger.info(f"Initialized SentimentProcessor")
        logger.info(f"Model: {model}")
        logger.info(f"Ollama host: {host}")
        logger.info(f"Tracking pairs: {', '.join(self.trading_pairs.keys())}")

        # Test connection
        self._test_connection()

    @staticmethod
    def _parse_trading_pairs(pairs_str: str) -> Dict[str, List[str]]:
        """Parse trading pairs from environment variable"""
        pairs = {}
        for pair in pairs_str.split(','):
            pair = pair.strip()
            if '/' in pair:
                # Extract base currency keywords
                base = pair.split('/')[0].lower()
                pairs[pair] = [base]
        return pairs

    def _test_connection(self):
        """Test connection to Ollama service"""
        logger.info("Testing connection to Ollama...")
        try:
            test_score = self.analyzer.get_sentiment_score("Bitcoin price rises")
            if test_score is not None:
                logger.info(f"Connection test successful (test score: {test_score})")
            else:
                logger.warning("Connection test returned None score")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            logger.warning("Will retry on first real message")

    def _match_article_to_pairs(self, title: str, content: str) -> List[str]:
        """
        Match article to relevant trading pairs

        Args:
            title: Article title
            content: Article content

        Returns:
            List of matching trading pairs
        """
        text = f"{title} {content}".lower()
        matched_pairs = []

        for pair, keywords in self.trading_pairs.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    matched_pairs.append(pair)
                    break

        # If no specific pairs matched, consider it general crypto news
        if not matched_pairs:
            # Apply to all pairs if general crypto keywords present
            general_keywords = ['crypto', 'cryptocurrency', 'blockchain', 'market']
            if any(keyword in text for keyword in general_keywords):
                matched_pairs = list(self.trading_pairs.keys())

        return matched_pairs

    def _classify_sentiment(self, score: float) -> str:
        """
        Classify sentiment score into a label

        Args:
            score: Sentiment score (-1.0 to 1.0)

        Returns:
            Sentiment label
        """
        if score >= self.SENTIMENT_THRESHOLDS['very_bullish']:
            return 'very_bullish'
        elif score >= self.SENTIMENT_THRESHOLDS['bullish']:
            return 'bullish'
        elif score <= self.SENTIMENT_THRESHOLDS['very_bearish']:
            return 'very_bearish'
        elif score <= self.SENTIMENT_THRESHOLDS['bearish']:
            return 'bearish'
        else:
            return 'neutral'

    def _process_news_article(self, news_data: Dict[str, Any]) -> None:
        """
        Process a single news article: analyze sentiment and publish signal

        Args:
            news_data: News article data from RabbitMQ
        """
        try:
            article_id = news_data.get('article_id', 'unknown')
            title = news_data.get('title', '')
            content = news_data.get('content', '')
            source = news_data.get('source', 'unknown')
            published = news_data.get('published', datetime.utcnow().isoformat())

            if not title:
                logger.warning(f"Article {article_id} has no title, skipping")
                return

            logger.info(f"Processing article from {source}: {title[:60]}...")

            # Perform sentiment analysis
            sentiment_score = self.analyzer.get_sentiment_score(
                headline=title,
                context=content[:500]  # First 500 chars of content as context
            )

            sentiment_label = self._classify_sentiment(sentiment_score)

            logger.info(
                f"Sentiment analysis complete: {sentiment_label} "
                f"(score: {sentiment_score:+.2f})"
            )

            # Match to trading pairs
            matched_pairs = self._match_article_to_pairs(title, content)

            if not matched_pairs:
                logger.debug(f"Article not relevant to any trading pairs, skipping")
                return

            logger.info(f"Article matched to pairs: {', '.join(matched_pairs)}")

            # Create sentiment signal for each matched pair
            for pair in matched_pairs:
                signal = {
                    'type': 'sentiment_signal',
                    'article_id': article_id,
                    'pair': pair,
                    'source': source,
                    'headline': title,
                    'sentiment_score': sentiment_score,
                    'sentiment_label': sentiment_label,
                    'published': published,
                    'analyzed_at': datetime.utcnow().isoformat(),
                    'model': self.analyzer.model_name
                }

                # Publish to output queue
                self.rabbitmq.publish(
                    self.output_queue,
                    signal,
                    persistent=True,
                    declare_queue=False
                )

                logger.info(
                    f"Published signal for {pair}: {sentiment_label} "
                    f"(score: {sentiment_score:+.2f})"
                )

        except Exception as e:
            logger.error(f"Error processing news article: {e}", exc_info=True)
            raise  # Re-raise to trigger message requeue

    def run(self):
        """Start consuming news articles and processing sentiment"""
        logger.info("Sentiment Processor starting...")
        logger.info(f"Consuming from: {self.input_queue}")
        logger.info(f"Publishing to: {self.output_queue}")

        # Create callback
        callback = create_consumer_callback(
            process_func=self._process_news_article,
            auto_ack=False
        )

        try:
            # Start consuming
            self.rabbitmq.consume(
                queue_name=self.input_queue,
                callback=callback,
                auto_ack=False,
                prefetch_count=1,  # Process one message at a time
                declare_queue=False
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Sentiment Processor...")

        try:
            self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")


def main():
    """Main function"""
    processor = SentimentProcessor(
        input_queue='raw_news_data',
        output_queue='sentiment_signals_queue'
    )

    processor.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
