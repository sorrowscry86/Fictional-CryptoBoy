"""
Integration Tests for Redis Client
VoidCat RDC - CryptoBoy Trading Bot

Tests Redis client with actual Redis service.
Requires Redis to be running.
"""
import os
import time
from datetime import datetime

import pytest


@pytest.fixture
def redis_config():
    """Redis configuration from environment"""
    return {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379))
    }


@pytest.fixture
def redis_client(redis_config):
    """Create Redis client for testing"""
    from services.common.redis_client import RedisClient
    
    client = RedisClient(**redis_config)
    yield client
    
    # Cleanup - remove test keys
    try:
        client.delete('test:*')
    except:
        pass


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis"""

    def test_connection(self, redis_client):
        """Test connection to Redis"""
        assert redis_client.ping() is True

    def test_set_and_get_sentiment(self, redis_client):
        """Test setting and getting sentiment data"""
        pair = 'BTC/USDT'
        score = 0.75
        headline = 'Bitcoin surges to new highs'
        source = 'coindesk'
        
        # Set sentiment
        redis_client.set_sentiment(pair, score, headline, source)
        
        # Get sentiment
        result = redis_client.get_sentiment(pair)
        
        assert result is not None
        assert float(result['score']) == score
        assert result['headline'] == headline
        assert result['source'] == source
        assert 'timestamp' in result

    def test_sentiment_staleness(self, redis_client):
        """Test sentiment staleness check"""
        pair = 'ETH/USDT'
        
        # Set sentiment
        redis_client.set_sentiment(pair, 0.5, 'Test', 'test')
        
        # Get sentiment immediately
        result = redis_client.get_sentiment(pair)
        timestamp = datetime.fromisoformat(result['timestamp'])
        
        # Should be fresh (less than 1 second old)
        now = datetime.now()
        age_seconds = (now - timestamp).total_seconds()
        assert age_seconds < 2  # Allow 2 second margin

    def test_multiple_pairs(self, redis_client):
        """Test storing sentiment for multiple trading pairs"""
        pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        scores = [0.8, 0.6, -0.2]
        
        # Set sentiment for all pairs
        for pair, score in zip(pairs, scores):
            redis_client.set_sentiment(pair, score, f'News for {pair}', 'test')
        
        # Verify all pairs
        for pair, expected_score in zip(pairs, scores):
            result = redis_client.get_sentiment(pair)
            assert result is not None
            assert float(result['score']) == expected_score

    def test_update_sentiment(self, redis_client):
        """Test updating existing sentiment"""
        pair = 'BTC/USDT'
        
        # Set initial sentiment
        redis_client.set_sentiment(pair, 0.5, 'Initial news', 'source1')
        time.sleep(0.1)
        
        # Update sentiment
        redis_client.set_sentiment(pair, 0.9, 'Updated news', 'source2')
        
        # Get updated sentiment
        result = redis_client.get_sentiment(pair)
        assert float(result['score']) == 0.9
        assert result['headline'] == 'Updated news'
        assert result['source'] == 'source2'

    def test_delete_sentiment(self, redis_client):
        """Test deleting sentiment data"""
        pair = 'BTC/USDT'
        
        # Set sentiment
        redis_client.set_sentiment(pair, 0.5, 'Test', 'test')
        
        # Delete
        redis_client.delete(f'sentiment:{pair}')
        
        # Verify deleted
        result = redis_client.get_sentiment(pair)
        assert result == {} or result is None

    def test_keys_pattern(self, redis_client):
        """Test getting keys by pattern"""
        # Set multiple sentiments
        redis_client.set_sentiment('BTC/USDT', 0.5, 'Test', 'test')
        redis_client.set_sentiment('ETH/USDT', 0.6, 'Test', 'test')
        
        # Get all sentiment keys
        keys = redis_client.keys('sentiment:*')
        
        assert len(keys) >= 2
        assert any('BTC/USDT' in k for k in keys)
        assert any('ETH/USDT' in k for k in keys)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
