"""
Sentiment Processor Service - Consumes news and publishes sentiment signals
Integrates with FinBERT for sentiment analysis
"""

import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List

from llm.huggingface_sentiment import HuggingFaceFinancialSentiment
from services.common.logging_config import setup_logging

# Add parent directories to path for imports
from services.common.rabbitmq_client import RabbitMQClient, create_consumer_callback

logger = setup_logging("sentiment-processor")


class SentimentAnalysisError(Exception):
    """Custom exception for sentiment analysis failures"""

    pass


class SentimentProcessor:
    """
    Sentiment analysis service that processes news articles from RabbitMQ
    Publishes enriched sentiment signals for trading strategies
    """

    # Trading pairs to match articles against
    TRADING_PAIRS = {
        "BTC/USDT": ["bitcoin", "btc"],
        "ETH/USDT": ["ethereum", "eth", "ether"],
        "BNB/USDT": ["binance", "bnb", "binance coin"],
    }

    # Sentiment classification thresholds
    SENTIMENT_THRESHOLDS = {
        "very_bullish": 0.7,
        "bullish": 0.3,
        "neutral": (-0.3, 0.3),
        "bearish": -0.3,
        "very_bearish": -0.7,
    }

    def __init__(
        self,
        input_queue: str = "raw_news_data",
        output_queue: str = "sentiment_signals_queue",
        model_name: str = None,
        ollama_host: str = None,
    ):
        """
        Initialize sentiment processor

        Args:
            input_queue: RabbitMQ queue to consume news from
            output_queue: RabbitMQ queue to publish sentiment signals
            model_name: FinBERT model name (defaults to 'ProsusAI/finbert')
            ollama_host: Deprecated (kept for backward compatibility)
        """
        self.input_queue = input_queue
        self.output_queue = output_queue

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()
        self.rabbitmq.connect()
        self.rabbitmq.declare_queue(self.input_queue, durable=True)
        self.rabbitmq.declare_queue(self.output_queue, durable=True)

        # Initialize FinBERT Sentiment Analyzer
        model = model_name or os.getenv("HUGGINGFACE_MODEL", "ProsusAI/finbert")
        logger.info(f"Loading FinBERT model: {model}")

        self.analyzer = HuggingFaceFinancialSentiment(model_name=model)

        # Get custom trading pairs from environment if available
        pairs_env = os.getenv("TRADING_PAIRS", "")
        if pairs_env:
            self.trading_pairs = self._parse_trading_pairs(pairs_env)
        else:
            self.trading_pairs = self.TRADING_PAIRS

        logger.info("Initialized SentimentProcessor")
        logger.info(f"Model: {model}")
        logger.info(f"Tracking pairs: {', '.join(self.trading_pairs.keys())}")

        # Test connection
        self._test_connection()

    @staticmethod
    def _parse_trading_pairs(pairs_str: str) -> Dict[str, List[str]]:
        """
        Parse and validate trading pairs from environment variable.

        Security: Validates format to prevent injection of malicious strings
        into Redis keys or message payloads.

        Args:
            pairs_str: Comma-separated trading pairs (e.g., "BTC/USDT,ETH/USDT")

        Returns:
            Dictionary mapping pair to keywords {" BTC/USDT": ["btc"], ...}

        Raises:
            ValueError: If any pair has invalid format
        """
        # Regex pattern: 3-5 uppercase letters, slash, 3-5 uppercase letters
        # Example: BTC/USDT, MATIC/USDT, SHIB/USDT
        TRADING_PAIR_PATTERN = re.compile(r"^[A-Z]{3,5}/[A-Z]{3,5}$")

        pairs = {}
        skipped = []

        for pair in pairs_str.split(","):
            pair = pair.strip()

            if not pair:  # Skip empty strings
                continue

            # Validate format with regex
            if not TRADING_PAIR_PATTERN.match(pair):
                logger.warning(
                    f"Skipping invalid trading pair format: '{pair}' "
                    f"(expected format: XXX/YYY where X,Y are 3-5 uppercase letters)"
                )
                skipped.append(pair)
                continue

            # Extract base currency keywords
            base = pair.split("/")[0].lower()
            pairs[pair] = [base]
            logger.debug(f"Parsed trading pair: {pair} (keywords: [{base}])")

        if skipped:
            logger.warning(
                f"Skipped {len(skipped)} invalid trading pairs: {', '.join(skipped)}"
            )

        if not pairs:
            raise ValueError(
                f"No valid trading pairs found in: '{pairs_str}'. "
                f"Expected format: BTC/USDT,ETH/USDT (3-5 uppercase letters each side)"
            )

        return pairs

    def _test_connection(self) -> None:
        """Test connection to FinBERT model"""
        logger.info("Testing FinBERT sentiment analysis...")
        try:
            test_score = self.analyzer.analyze_sentiment("Bitcoin price rises")
            if test_score is not None:
                logger.info(f"FinBERT test successful (test score: {test_score:.2f})")
            else:
                logger.warning("FinBERT test returned None score")
        except Exception as e:
            logger.error(f"FinBERT test failed: {e}")
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
                if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                    matched_pairs.append(pair)
                    break

        # If no specific pairs matched, consider it general crypto news
        if not matched_pairs:
            # Apply to all pairs if general crypto keywords present
            general_keywords = ["crypto", "cryptocurrency", "blockchain", "market"]
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
        if score >= self.SENTIMENT_THRESHOLDS["very_bullish"]:
            return "very_bullish"
        elif score >= self.SENTIMENT_THRESHOLDS["bullish"]:
            return "bullish"
        elif score <= self.SENTIMENT_THRESHOLDS["very_bearish"]:
            return "very_bearish"
        elif score <= self.SENTIMENT_THRESHOLDS["bearish"]:
            return "bearish"
        else:
            return "neutral"

    def _fallback_sentiment_analysis(self, text: str) -> float:
        """
        Fallback sentiment analysis using simple keyword matching.
        Used when FinBERT fails to prevent pipeline collapse.

        Args:
            text: Text to analyze

        Returns:
            Sentiment score (-1.0 to 1.0) based on keyword heuristics

        Note:
            This is a CRUDE fallback for resilience. FinBERT is far superior.
            Logs warning when fallback is used.
        """
        text_lower = text.lower()

        # Bullish keywords
        bullish = [
            "surge", "rally", "gain", "increase", "rise", "bullish", "adoption",
            "breakout", "high", "record", "institutional", "approval", "upgrade"
        ]

        # Bearish keywords
        bearish = [
            "crash", "drop", "fall", "decline", "bearish", "sell-off", "plunge",
            "loss", "fraud", "hack", "regulation", "ban", "concern"
        ]

        # Count keyword matches
        bullish_count = sum(1 for word in bullish if word in text_lower)
        bearish_count = sum(1 for word in bearish if word in text_lower)

        # Calculate simple score
        if bullish_count == 0 and bearish_count == 0:
            score = 0.0  # Neutral
        else:
            score = (bullish_count - bearish_count) / (bullish_count + bearish_count + 1)
            # Clamp to [-1, 1]
            score = max(-1.0, min(1.0, score))

        logger.warning(
            f"FALLBACK SENTIMENT USED (FinBERT unavailable): "
            f"score={score:.2f} (bullish={bullish_count}, bearish={bearish_count})"
        )

        return score

    def _process_news_article(self, news_data: Dict[str, Any]) -> None:
        """
        Process a single news article: analyze sentiment and publish signal

        Args:
            news_data: News article data from RabbitMQ
        """
        try:
            article_id = news_data.get("article_id", "unknown")
            title = news_data.get("title", "")
            content = news_data.get("content", "")
            source = news_data.get("source", "unknown")
            published = news_data.get("published", datetime.utcnow().isoformat())

            if not title:
                logger.warning(f"Article {article_id} has no title, skipping")
                return

            logger.info(f"Processing article from {source}: {title[:60]}...")

            # Perform sentiment analysis with FinBERT (with fallback)
            # Combine title and content snippet for better context
            text_to_analyze = f"{title}. {content[:500]}"

            # Try primary oracle (FinBERT)
            sentiment_score = None
            model_used = "finbert"

            try:
                sentiment_score = self.analyzer.analyze_sentiment(text_to_analyze)

                if sentiment_score is None:
                    logger.warning("FinBERT returned None - attempting fallback")
                    raise SentimentAnalysisError("FinBERT returned None score")

            except Exception as e:
                logger.error(
                    f"Primary sentiment analysis (FinBERT) failed for article {article_id}: {e}",
                    exc_info=False,  # Don't spam logs with full traceback
                )

                # Graceful degradation: Use fallback keyword analysis
                try:
                    sentiment_score = self._fallback_sentiment_analysis(text_to_analyze)
                    model_used = "fallback_keywords"
                    logger.info(
                        f"Fallback sentiment analysis succeeded: score={sentiment_score:+.2f}"
                    )

                except Exception as fallback_error:
                    # Even fallback failed - use neutral score to prevent pipeline collapse
                    logger.error(
                        f"Fallback sentiment analysis also failed: {fallback_error}",
                        exc_info=True,
                    )
                    sentiment_score = 0.0  # Neutral score
                    model_used = "neutral_default"
                    logger.warning(
                        f"Using neutral default score (0.0) for article {article_id} "
                        f"to prevent pipeline collapse"
                    )

            sentiment_label = self._classify_sentiment(sentiment_score)

            logger.info(
                f"Sentiment analysis complete ({model_used}): {sentiment_label} "
                f"(score: {sentiment_score:+.2f})"
            )

            # Match to trading pairs
            matched_pairs = self._match_article_to_pairs(title, content)

            if not matched_pairs:
                logger.debug("Article not relevant to any trading pairs, skipping")
                return

            logger.info(f"Article matched to pairs: {', '.join(matched_pairs)}")

            # Create sentiment signal for each matched pair
            for pair in matched_pairs:
                signal = {
                    "type": "sentiment_signal",
                    "article_id": article_id,
                    "pair": pair,
                    "source": source,
                    "headline": title,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "published": published,
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "model": model_used,  # Track which model was actually used
                    "fallback_used": model_used != "finbert",  # Flag if fallback was triggered
                }

                # Publish to output queue
                self.rabbitmq.publish(self.output_queue, signal, persistent=True, declare_queue=False)

                logger.info(f"Published signal for {pair}: {sentiment_label} (score: {sentiment_score:+.2f})")

        except Exception as e:
            # Catch unexpected errors (not sentiment analysis failures - those are handled above)
            # Log but DON'T re-raise to avoid message requeue loop
            logger.error(
                f"Unexpected error processing article: {e}",
                exc_info=True,
                extra={"article_id": news_data.get("article_id", "unknown")},
            )
            # Note: Message will be ACKed and not requeued to prevent poison pill messages
            # Sentiment analysis failures are handled gracefully above with fallback

    def run(self) -> None:
        """Start consuming news articles and processing sentiment"""
        logger.info("Sentiment Processor starting...")
        logger.info(f"Consuming from: {self.input_queue}")
        logger.info(f"Publishing to: {self.output_queue}")

        # Create callback
        callback = create_consumer_callback(process_func=self._process_news_article, auto_ack=False)

        try:
            # Start consuming
            self.rabbitmq.consume(
                queue_name=self.input_queue,
                callback=callback,
                auto_ack=False,
                prefetch_count=1,  # Process one message at a time
                declare_queue=False,
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown"""
        logger.info("Shutting down Sentiment Processor...")

        try:
            self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")


def main() -> None:
    """Main function"""
    processor = SentimentProcessor(input_queue="raw_news_data", output_queue="sentiment_signals_queue")

    processor.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
