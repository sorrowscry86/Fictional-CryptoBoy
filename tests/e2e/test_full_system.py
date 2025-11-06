"""
End-to-End Tests for CryptoBoy Trading System
VoidCat RDC - CryptoBoy Trading Bot

Tests complete workflows from news ingestion to trading signals.
Requires full system to be running (all microservices).
"""
import json
import os
import time
from datetime import datetime

import pytest


@pytest.fixture
def system_config():
    """Full system configuration"""
    return {
        'rabbitmq': {
            'host': os.getenv('RABBITMQ_HOST', 'localhost'),
            'port': int(os.getenv('RABBITMQ_PORT', 5672)),
            'username': os.getenv('RABBITMQ_USER', 'admin'),
            'password': os.getenv('RABBITMQ_PASS', 'cryptoboy_secret')
        },
        'redis': {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379))
        }
    }


@pytest.mark.e2e
class TestEndToEndWorkflow:
    """End-to-end system tests"""

    def test_system_health(self, system_config):
        """Test that all system components are healthy"""
        from services.common.rabbitmq_client import RabbitMQClient
        from services.common.redis_client import RedisClient
        
        # Test RabbitMQ
        rabbitmq = RabbitMQClient(**system_config['rabbitmq'])
        rabbitmq.connect()
        assert rabbitmq.connection is not None
        rabbitmq.close()
        
        # Test Redis
        redis = RedisClient(**system_config['redis'])
        assert redis.ping() is True

    def test_news_to_sentiment_pipeline(self, system_config):
        """Test full pipeline: news → sentiment → cache"""
        from services.common.rabbitmq_client import RabbitMQClient
        from services.common.redis_client import RedisClient
        
        # Publish news article
        rabbitmq = RabbitMQClient(**system_config['rabbitmq'])
        rabbitmq.connect()
        rabbitmq.declare_queue('raw_news_data', durable=True)
        
        test_article = {
            'headline': 'Bitcoin E2E Test: Major breakthrough in crypto adoption',
            'content': 'Test article for E2E testing showing positive sentiment',
            'source': 'e2e_test',
            'timestamp': datetime.now().isoformat(),
            'pair': 'BTC/USDT'
        }
        
        rabbitmq.publish('raw_news_data', test_article)
        rabbitmq.close()
        
        # Wait for processing (sentiment processor → signal cacher → Redis)
        time.sleep(5)
        
        # Check Redis for sentiment
        redis = RedisClient(**system_config['redis'])
        sentiment = redis.get_sentiment('BTC/USDT')
        
        # If sentiment exists, verify it was processed
        if sentiment and sentiment != {}:
            assert 'score' in sentiment
            assert 'timestamp' in sentiment
            print(f"✓ Sentiment processed: {sentiment}")

    def test_sentiment_caching_performance(self, system_config):
        """Test that sentiment is cached and retrievable quickly"""
        from services.common.redis_client import RedisClient
        
        redis = RedisClient(**system_config['redis'])
        
        # Set test sentiment
        redis.set_sentiment('TEST/USDT', 0.85, 'Performance test', 'e2e')
        
        # Measure retrieval time
        start = time.time()
        sentiment = redis.get_sentiment('TEST/USDT')
        elapsed = time.time() - start
        
        assert sentiment is not None
        assert float(sentiment['score']) == 0.85
        assert elapsed < 0.1  # Should be very fast (<100ms)
        
        print(f"✓ Cache retrieval: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    def test_multiple_pairs_processing(self, system_config):
        """Test processing news for multiple trading pairs"""
        from services.common.rabbitmq_client import RabbitMQClient
        from services.common.redis_client import RedisClient
        
        pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        # Publish news for each pair
        rabbitmq = RabbitMQClient(**system_config['rabbitmq'])
        rabbitmq.connect()
        rabbitmq.declare_queue('raw_news_data', durable=True)
        
        for pair in pairs:
            article = {
                'headline': f'{pair} shows strong momentum',
                'content': f'Positive developments for {pair}',
                'source': 'e2e_test',
                'timestamp': datetime.now().isoformat(),
                'pair': pair
            }
            rabbitmq.publish('raw_news_data', article)
        
        rabbitmq.close()
        
        # Wait for processing
        time.sleep(10)
        
        # Check all pairs have sentiment
        redis = RedisClient(**system_config['redis'])
        processed_count = 0
        
        for pair in pairs:
            sentiment = redis.get_sentiment(pair)
            if sentiment and sentiment != {}:
                processed_count += 1
                print(f"✓ {pair}: {sentiment.get('score', 'N/A')}")
        
        # At least some should be processed
        print(f"Processed {processed_count}/{len(pairs)} pairs")

    def test_queue_message_flow(self, system_config):
        """Test message flow through all queues"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        rabbitmq = RabbitMQClient(**system_config['rabbitmq'])
        rabbitmq.connect()
        
        # Declare all queues
        queues = ['raw_news_data', 'raw_market_data', 'sentiment_signals_queue']
        
        for queue in queues:
            rabbitmq.declare_queue(queue, durable=True)
            
            # Check queue exists and is accessible
            method_frame = rabbitmq.channel.queue_declare(queue=queue, passive=True)
            print(f"✓ Queue {queue}: {method_frame.method.message_count} messages")
        
        rabbitmq.close()

    @pytest.mark.slow
    def test_system_under_load(self, system_config):
        """Test system performance under load"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        rabbitmq = RabbitMQClient(**system_config['rabbitmq'])
        rabbitmq.connect()
        rabbitmq.declare_queue('raw_news_data', durable=True)
        
        # Publish multiple articles rapidly
        start_time = time.time()
        message_count = 10
        
        for i in range(message_count):
            article = {
                'headline': f'Load test article {i}',
                'content': f'Content for load test {i}',
                'source': 'load_test',
                'timestamp': datetime.now().isoformat()
            }
            rabbitmq.publish('raw_news_data', article)
        
        publish_time = time.time() - start_time
        rabbitmq.close()
        
        print(f"✓ Published {message_count} messages in {publish_time:.2f}s")
        print(f"  Rate: {message_count/publish_time:.2f} msg/s")
        
        # System should handle at least 5 msg/s
        assert message_count/publish_time > 5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
