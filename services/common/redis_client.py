"""
Redis Client for CryptoBoy Microservices
Provides connection management and caching utilities
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisClient:
    """Thread-safe Redis client with automatic reconnection"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: str = None,
        decode_responses: bool = True,
        max_retries: int = 5,
        retry_delay: int = 2,
    ):
        """
        Initialize Redis client

        Args:
            host: Redis host (defaults to env REDIS_HOST or 'redis')
            port: Redis port (defaults to env REDIS_PORT or 6379)
            db: Redis database number
            password: Redis password (if authentication is enabled)
            decode_responses: Whether to decode responses to strings
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.host = host or os.getenv("REDIS_HOST", "redis")
        self.port = int(port or os.getenv("REDIS_PORT", 6379))
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.decode_responses = decode_responses
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=self.decode_responses,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )

                # Test connection
                self.client.ping()
                logger.info(f"Successfully connected to Redis at {self.host}:{self.port}")
                return

            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"Failed to connect to Redis (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise ConnectionError(f"Could not connect to Redis after {self.max_retries} attempts")

    def ensure_connection(self) -> None:
        """Ensure connection is active, reconnect if needed"""
        try:
            self.client.ping()
        except (ConnectionError, TimeoutError, AttributeError):
            logger.info("Redis connection lost, reconnecting...")
            self._connect()

    def set_json(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        """
        Store a JSON-serializable value in Redis

        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if successful
        """
        try:
            self.ensure_connection()
            json_value = json.dumps(value)
            if ttl:
                return self.client.setex(key, ttl, json_value)
            return self.client.set(key, json_value)
        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            return False

    def get_json(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a JSON value from Redis

        Args:
            key: Redis key
            default: Default value if key doesn't exist

        Returns:
            Deserialized JSON value or default
        """
        try:
            self.ensure_connection()
            value = self.client.get(key)
            if value is None:
                return default
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key '{key}': {e}")
            return default
        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            return default

    def hset_json(self, name: str, mapping: Dict[str, Any]) -> int:
        """
        Set multiple hash fields with JSON serialization for complex values

        Args:
            name: Hash name
            mapping: Dictionary of field-value pairs

        Returns:
            Number of fields added
        """
        try:
            self.ensure_connection()
            # Serialize complex values to JSON
            serialized_mapping = {}
            for field, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_mapping[field] = json.dumps(value)
                else:
                    serialized_mapping[field] = str(value)

            return self.client.hset(name, mapping=serialized_mapping)
        except Exception as e:
            logger.error(f"Failed to hset '{name}': {e}")
            return 0

    def hgetall_json(self, name: str) -> Dict[str, Any]:
        """
        Get all hash fields with JSON deserialization

        Args:
            name: Hash name

        Returns:
            Dictionary of field-value pairs
        """
        try:
            self.ensure_connection()
            data = self.client.hgetall(name)
            if not data:
                return {}

            # Try to deserialize JSON values
            result = {}
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value

            return result
        except Exception as e:
            logger.error(f"Failed to hgetall '{name}': {e}")
            return {}

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        Get a single hash field value

        Args:
            name: Hash name
            key: Field key
            default: Default value if field doesn't exist

        Returns:
            Field value or default
        """
        try:
            self.ensure_connection()
            value = self.client.hget(name, key)
            return value if value is not None else default
        except Exception as e:
            logger.error(f"Failed to hget '{name}':'{key}': {e}")
            return default

    def lpush(self, key: str, *values: str) -> int:
        """
        Push values to the head of a list

        Args:
            key: List key
            values: Values to push

        Returns:
            Length of list after push
        """
        try:
            self.ensure_connection()
            return self.client.lpush(key, *values)
        except Exception as e:
            logger.error(f"Failed to lpush to '{key}': {e}")
            return 0

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """
        Get a range of values from a list

        Args:
            key: List key
            start: Start index
            end: End index (-1 for all)

        Returns:
            List of values
        """
        try:
            self.ensure_connection()
            return self.client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Failed to lrange '{key}': {e}")
            return []

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if successful
        """
        try:
            self.ensure_connection()
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expiration for '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            self.ensure_connection()
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        try:
            self.ensure_connection()
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Failed to check existence: {e}")
            return 0

    def keys(self, pattern: str = "*") -> List[str]:
        """
        Find all keys matching pattern

        Args:
            pattern: Key pattern (e.g., 'sentiment:*')

        Returns:
            List of matching keys
        """
        try:
            self.ensure_connection()
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Failed to get keys with pattern '{pattern}': {e}")
            return []

    def flushdb(self) -> bool:
        """
        Delete all keys in current database

        Returns:
            True if successful
        """
        try:
            self.ensure_connection()
            return self.client.flushdb()
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False

    def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")


# Singleton instance for easy access
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get or create singleton Redis client

    Returns:
        RedisClient instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
