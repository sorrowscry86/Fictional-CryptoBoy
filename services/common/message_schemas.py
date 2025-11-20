"""
Message Schema Validation for CryptoBoy Microservices
VoidCat RDC - Input Validation Framework

This module provides Pydantic models for validating RabbitMQ message payloads,
preventing injection attacks and ensuring data integrity across microservices.

Security Enhancement: FLAW-011 Resolution
Phase 3: Wards & Security
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class RawNewsMessage(BaseModel):
    """
    Schema for raw_news_data queue messages
    Sent by: News Poller
    Consumed by: Sentiment Processor
    """

    timestamp: datetime = Field(..., description="When the article was published")
    source: str = Field(..., min_length=1, max_length=100, description="RSS feed source name")
    title: str = Field(..., min_length=1, max_length=500, description="Article headline")
    url: str = Field(..., description="Article URL")
    content: str = Field(..., min_length=10, max_length=50000, description="Full article text")

    @validator("url")
    def validate_url(cls, v):
        """Ensure URL is well-formed"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("source")
    def validate_source(cls, v):
        """Whitelist allowed sources"""
        allowed_sources = {"coindesk", "cointelegraph", "decrypt", "bitcoin_magazine", "cryptoslate"}
        if v.lower() not in allowed_sources:
            raise ValueError(f"Source must be one of: {allowed_sources}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-20T08:00:00Z",
                "source": "coindesk",
                "title": "Bitcoin Surges to New Highs",
                "url": "https://coindesk.com/article/123",
                "content": "Bitcoin reached a new all-time high today...",
            }
        }


class RawMarketDataMessage(BaseModel):
    """
    Schema for raw_market_data queue messages
    Sent by: Market Streamer
    Consumed by: Trading Bot
    """

    timestamp: datetime = Field(..., description="Candle timestamp")
    pair: str = Field(..., regex=r"^[A-Z]{3,5}/[A-Z]{3,5}$", description="Trading pair (e.g. BTC/USDT)")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trading volume")

    @validator("high")
    def validate_high(cls, v, values):
        """Ensure high >= low, open, close"""
        if "low" in values and v < values["low"]:
            raise ValueError("High must be >= low")
        if "open" in values and v < values["open"]:
            raise ValueError("High must be >= open")
        if "close" in values and v < values["close"]:
            raise ValueError("High must be >= close")
        return v

    @validator("low")
    def validate_low(cls, v, values):
        """Ensure low <= high, open, close"""
        if "open" in values and v > values["open"]:
            raise ValueError("Low must be <= open")
        if "close" in values and v > values["close"]:
            raise ValueError("Low must be <= close")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-20T08:00:00Z",
                "pair": "BTC/USDT",
                "open": 50000.0,
                "high": 51000.0,
                "low": 49500.0,
                "close": 50500.0,
                "volume": 1234.56,
            }
        }


class SentimentSignalMessage(BaseModel):
    """
    Schema for sentiment_signals_queue messages
    Sent by: Sentiment Processor
    Consumed by: Signal Cacher
    """

    timestamp: datetime = Field(..., description="When sentiment was analyzed")
    pair: str = Field(..., regex=r"^[A-Z]{3,5}/[A-Z]{3,5}$", description="Trading pair")
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score (-1.0 to +1.0)")
    headline: str = Field(..., min_length=1, max_length=500, description="News headline")
    source: str = Field(..., min_length=1, max_length=100, description="News source")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence")
    model: str = Field(default="finbert", description="Model used for analysis")

    @validator("score")
    def validate_score_range(cls, v):
        """Ensure sentiment score is in valid range"""
        if not -1.0 <= v <= 1.0:
            raise ValueError("Sentiment score must be between -1.0 and +1.0")
        return v

    @validator("model")
    def validate_model(cls, v):
        """Whitelist allowed sentiment models"""
        allowed_models = {"finbert", "distilroberta-financial", "ollama", "lmstudio"}
        if v.lower() not in allowed_models:
            raise ValueError(f"Model must be one of: {allowed_models}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-20T08:00:00Z",
                "pair": "BTC/USDT",
                "score": 0.75,
                "headline": "Bitcoin Adoption Grows Among Institutions",
                "source": "coindesk",
                "confidence": 0.92,
                "model": "finbert",
            }
        }


# Validation Helper Functions


def validate_message(message_dict: dict, schema: BaseModel) -> BaseModel:
    """
    Validate a message dictionary against a Pydantic schema.

    Args:
        message_dict: Raw message payload from RabbitMQ
        schema: Pydantic model class to validate against

    Returns:
        Validated message object

    Raises:
        ValidationError: If message doesn't match schema

    Example:
        >>> validated = validate_message(raw_data, RawNewsMessage)
        >>> print(validated.title)
    """
    return schema(**message_dict)


def safe_message_consumer(callback, schema: BaseModel):
    """
    Decorator for RabbitMQ message consumers that validates input.

    Args:
        callback: Consumer function to wrap
        schema: Pydantic model for validation

    Returns:
        Wrapped callback with validation

    Example:
        >>> @safe_message_consumer(callback=process_news, schema=RawNewsMessage)
        >>> def wrapped_consumer(ch, method, properties, body):
        >>>     # Callback receives validated message object
        >>>     pass
    """
    import json
    import logging

    logger = logging.getLogger(__name__)

    def wrapper(ch, method, properties, body):
        try:
            # Parse JSON
            message_dict = json.loads(body)

            # Validate against schema
            validated_message = schema(**message_dict)

            # Call original callback with validated object
            callback(ch, method, properties, validated_message)

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}", extra={"body": body})
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except ValueError as e:
            logger.error(f"Message validation failed: {e}", extra={"message": message_dict})
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # Retry

    return wrapper


# Usage Example
if __name__ == "__main__":
    # Test validation
    valid_sentiment = {
        "timestamp": datetime.now(),
        "pair": "BTC/USDT",
        "score": 0.8,
        "headline": "Bitcoin surges",
        "source": "coindesk",
        "model": "finbert",
    }

    try:
        validated = SentimentSignalMessage(**valid_sentiment)
        print(f"✓ Valid message: {validated.score}")
    except ValueError as e:
        print(f"✗ Validation failed: {e}")

    # Test invalid score
    invalid_sentiment = valid_sentiment.copy()
    invalid_sentiment["score"] = 1.5  # Out of range!

    try:
        SentimentSignalMessage(**invalid_sentiment)
    except ValueError as e:
        print(f"✓ Correctly rejected invalid score: {e}")
