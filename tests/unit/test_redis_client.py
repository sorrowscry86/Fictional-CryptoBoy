"""
Unit Tests for Redis Client
VoidCat RDC - CryptoBoy Trading Bot

Tests RedisClient in isolation using mocking.
"""
import unittest
from unittest.mock import MagicMock, patch

import pytest


class TestRedisClient(unittest.TestCase):
    """Test RedisClient functionality"""

    @patch('services.common.redis_client.redis')
    def test_connect(self, mock_redis):
        """Test successful connection"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient(host='localhost', port=6379)
        
        mock_redis.Redis.assert_called_once_with(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        assert client.redis is not None

    @patch('services.common.redis_client.redis')
    def test_set_sentiment(self, mock_redis):
        """Test setting sentiment data"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient()
        client.set_sentiment('BTC/USDT', 0.75, 'Test headline', 'test_source')
        
        mock_redis_instance.hset.assert_called()

    @patch('services.common.redis_client.redis')
    def test_get_sentiment(self, mock_redis):
        """Test getting sentiment data"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.hgetall.return_value = {
            'score': '0.75',
            'timestamp': '2025-11-01T00:00:00',
            'headline': 'Test headline',
            'source': 'test_source'
        }
        
        client = RedisClient()
        result = client.get_sentiment('BTC/USDT')
        
        assert result is not None
        assert result['score'] == '0.75'
        mock_redis_instance.hgetall.assert_called_once()

    @patch('services.common.redis_client.redis')
    def test_delete_key(self, mock_redis):
        """Test deleting a key"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient()
        client.delete('test_key')
        
        mock_redis_instance.delete.assert_called_once_with('test_key')

    @patch('services.common.redis_client.redis')
    def test_ping(self, mock_redis):
        """Test Redis ping"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        
        client = RedisClient()
        result = client.ping()
        
        assert result is True
        mock_redis_instance.ping.assert_called_once()


class TestRedisClientIntegration:
    """Integration-style tests for Redis client (requires actual service)"""

    @pytest.mark.integration
    def test_connection_to_real_service(self):
        """Test connection to actual Redis (skipped in unit tests)"""
        pytest.skip("Integration test - requires running Redis service")


if __name__ == '__main__':
    unittest.main()
