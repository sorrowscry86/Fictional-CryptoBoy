"""
Common Utilities for CryptoBoy Microservices
VoidCat RDC

Shared modules used across all microservices for connection management,
configuration validation, logging, and message validation.

Modules:
    - rabbitmq_client: RabbitMQ connection pooling and message publishing
    - redis_client: Redis connection pooling and caching utilities
    - config_validator: Environment variable validation framework
    - logging_config: Centralized logging configuration
    - message_schemas: Pydantic models for RabbitMQ message validation

Usage:
    from services.common.rabbitmq_client import RabbitMQClient
    from services.common.redis_client import RedisClient
    from services.common.message_schemas import RawNewsMessage, SentimentSignalMessage

Security Features:
    - Input validation on all RabbitMQ messages (Pydantic schemas)
    - Connection pooling for efficient resource usage
    - Automatic reconnection with exponential backoff
    - Environment variable validation with fail-fast on missing config
"""

__all__ = [
    "RabbitMQClient",
    "RedisClient",
    "RawNewsMessage",
    "RawMarketDataMessage",
    "SentimentSignalMessage",
]
