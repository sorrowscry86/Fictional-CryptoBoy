"""
Signal Cacher Service - Caches sentiment signals in Redis
Provides fast access to latest sentiment scores for trading strategies
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

from services.common.logging_config import setup_logging

# Add parent directories to path for imports
from services.common.rabbitmq_client import RabbitMQClient, create_consumer_callback
from services.common.redis_client import RedisClient

logger = setup_logging("signal-cacher")


class SignalCacher:
    """
    Signal caching service that consumes sentiment signals from RabbitMQ
    and stores them in Redis for fast access by trading strategies
    """

    def __init__(self, input_queue: str = "sentiment_signals_queue", cache_ttl: int = None):
        """
        Initialize signal cacher

        Args:
            input_queue: RabbitMQ queue to consume signals from
            cache_ttl: Time-to-live for cached signals in seconds (None = no expiry)
        """
        self.input_queue = input_queue
        self.cache_ttl = cache_ttl or int(os.getenv("SIGNAL_CACHE_TTL", 0))  # 0 = no expiry

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()
        self.rabbitmq.connect()
        self.rabbitmq.declare_queue(self.input_queue, durable=True)

        # Initialize Redis client with connection validation
        logger.info("Connecting to Redis...")
        try:
            self.redis = RedisClient()

            # CRITICAL: Validate connection immediately (fail fast if Redis unavailable)
            if not self.redis.ping():
                raise ConnectionError("Redis PING failed")

            logger.info("✓ Redis connection validated")

        except ConnectionError as e:
            logger.critical(f"✗ Redis connection failed: {e}")
            logger.critical("Signal Cacher CANNOT start without Redis")
            raise SystemExit(1)  # Fail fast - don't start with broken cache
        except Exception as e:
            logger.critical(f"✗ Unexpected Redis initialization error: {e}", exc_info=True)
            raise SystemExit(1)

        # Statistics
        self.stats = {"signals_processed": 0, "cache_updates": 0, "errors": 0}

        logger.info("Initialized SignalCacher")
        logger.info(f"Input queue: {self.input_queue}")
        logger.info(f"Cache TTL: {self.cache_ttl}s (0 = no expiry)")

    def _process_sentiment_signal(self, signal: Dict[str, Any]) -> None:
        """
        Process a sentiment signal and update Redis cache

        Args:
            signal: Sentiment signal data from RabbitMQ
        """
        try:
            self.stats["signals_processed"] += 1

            # Extract signal data
            pair = signal.get("pair")
            sentiment_score = signal.get("sentiment_score")
            sentiment_label = signal.get("sentiment_label")
            headline = signal.get("headline", "")
            source = signal.get("source", "unknown")
            analyzed_at = signal.get("analyzed_at", datetime.utcnow().isoformat())
            article_id = signal.get("article_id", "unknown")

            if not pair or sentiment_score is None:
                logger.warning("Invalid signal data: missing pair or score")
                self.stats["errors"] += 1
                return

            logger.debug(f"Processing signal for {pair}: {sentiment_label} ({sentiment_score:+.2f})")

            # Store latest sentiment in Redis hash
            cache_key = f"sentiment:{pair}"

            cache_data = {
                "score": sentiment_score,
                "label": sentiment_label,
                "timestamp": analyzed_at,
                "headline": headline[:100],  # Truncate for storage
                "source": source,
                "article_id": article_id,
            }

            # Update Redis hash
            fields_set = self.redis.hset_json(cache_key, cache_data)

            if fields_set:
                self.stats["cache_updates"] += 1
                logger.info(f"Updated cache for {pair}: {sentiment_label} " f"(score: {sentiment_score:+.2f})")

            # Set TTL if configured
            if self.cache_ttl > 0:
                self.redis.expire(cache_key, self.cache_ttl)

            # Also maintain a time-series list for historical tracking (optional)
            self._update_history(pair, signal)

            # Log statistics periodically
            if self.stats["signals_processed"] % 50 == 0:
                self._log_statistics()

        except Exception as e:
            logger.error(f"Error processing sentiment signal: {e}", exc_info=True)
            self.stats["errors"] += 1
            raise  # Re-raise to trigger message requeue

    def _update_history(self, pair: str, signal: Dict[str, Any]) -> None:
        """
        Optionally maintain historical signal data in Redis

        Args:
            pair: Trading pair
            signal: Signal data
        """
        try:
            history_key = f"sentiment_history:{pair}"

            # Store as JSON string in list
            import json

            history_entry = json.dumps(
                {
                    "score": signal.get("sentiment_score"),
                    "label": signal.get("sentiment_label"),
                    "timestamp": signal.get("analyzed_at"),
                    "headline": signal.get("headline", "")[:50],
                }
            )

            # Add to list (newest first)
            self.redis.lpush(history_key, history_entry)

            # Keep only last 100 entries
            # Trim list to 100 elements
            self.redis.ltrim(history_key, 0, 99)

        except Exception as e:
            logger.warning(f"Failed to update history for {pair}: {e}")

    def _log_statistics(self) -> None:
        """Log processing statistics"""
        logger.info(
            f"Statistics: "
            f"processed={self.stats['signals_processed']}, "
            f"cached={self.stats['cache_updates']}, "
            f"errors={self.stats['errors']}"
        )

    def run(self):
        """Start consuming sentiment signals and caching"""
        logger.info("Signal Cacher starting...")
        logger.info(f"Consuming from: {self.input_queue}")

        # Create callback
        callback = create_consumer_callback(process_func=self._process_sentiment_signal, auto_ack=False)

        try:
            # Start consuming
            self.rabbitmq.consume(
                queue_name=self.input_queue,
                callback=callback,
                auto_ack=False,
                prefetch_count=10,  # Can process multiple in parallel for caching
                declare_queue=False,
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Signal Cacher...")

        # Log final statistics
        self._log_statistics()

        try:
            self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")

        try:
            self.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")


def main():
    """Main function"""
    cacher = SignalCacher(input_queue="sentiment_signals_queue", cache_ttl=0)  # No expiry by default

    cacher.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
