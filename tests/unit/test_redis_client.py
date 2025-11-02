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
        mock_redis_instance.ping.return_value = True
        
        client = RedisClient(host='localhost', port=6379)
        
        # Connection should be established
        assert client.client is not None
        mock_redis_instance.ping.assert_called()

    @patch('services.common.redis_client.redis')
    def test_set_json(self, mock_redis):
        """Test setting JSON data"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.set.return_value = True
        
        client = RedisClient()
        result = client.set_json('test_key', {'data': 'value'})
        
        assert result is True
        mock_redis_instance.set.assert_called_once()

    @patch('services.common.redis_client.redis')
    def test_get_json(self, mock_redis):
        """Test getting JSON data"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = '{"data": "value"}'
        
        client = RedisClient()
        result = client.get_json('test_key')
        
        assert result == {'data': 'value'}
        mock_redis_instance.get.assert_called_once()

    @patch('services.common.redis_client.redis')
    def test_delete_key(self, mock_redis):
        """Test deleting a key"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.delete.return_value = 1
        
        client = RedisClient()
        result = client.delete('test_key')
        
        assert result == 1
        mock_redis_instance.delete.assert_called_once_with('test_key')

    @patch('services.common.redis_client.redis')
    def test_keys_pattern(self, mock_redis):
        """Test getting keys by pattern"""
        from services.common.redis_client import RedisClient
        
        mock_redis_instance = MagicMock()
        mock_redis.Redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.keys.return_value = ['key1', 'key2']
        
        client = RedisClient()
        result = client.keys('test:*')
        
        assert result == ['key1', 'key2']
        mock_redis_instance.keys.assert_called_once()


class TestRedisClientIntegration:
    """Integration-style tests for Redis client (requires actual service)"""

    @pytest.mark.integration
    def test_connection_to_real_service(self):
        """Test connection to actual Redis (skipped in unit tests)"""
        pytest.skip("Integration test - requires running Redis service")


if __name__ == '__main__':
    unittest.main()
