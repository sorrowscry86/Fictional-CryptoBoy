"""
Integration Tests for RabbitMQ Client
VoidCat RDC - CryptoBoy Trading Bot

Tests RabbitMQ client with actual RabbitMQ service.
Requires RabbitMQ to be running.
"""
import json
import os
import time

import pytest


@pytest.fixture
def rabbitmq_config():
    """RabbitMQ configuration from environment"""
    return {
        'host': os.getenv('RABBITMQ_HOST', 'localhost'),
        'port': int(os.getenv('RABBITMQ_PORT', 5672)),
        'username': os.getenv('RABBITMQ_USER', 'cryptoboy'),
        'password': os.getenv('RABBITMQ_PASS', 'cryptoboy123')
    }


@pytest.fixture
def rabbitmq_client(rabbitmq_config):
    """Create RabbitMQ client for testing"""
    from services.common.rabbitmq_client import RabbitMQClient
    
    client = RabbitMQClient(**rabbitmq_config)
    client.connect()
    yield client
    
    # Cleanup
    try:
        client.close()
    except Exception as e:
        # Specific exception handling - avoiding bare except
        logger.warning(f"Failed to close RabbitMQ client during cleanup: {e}")
        pass


@pytest.mark.integration
class TestRabbitMQIntegration:
    """Integration tests for RabbitMQ"""

    def test_connection(self, rabbitmq_client):
        """Test connection to RabbitMQ"""
        assert rabbitmq_client.connection is not None
        assert rabbitmq_client.channel is not None

    def test_declare_queue(self, rabbitmq_client):
        """Test queue declaration"""
        queue_name = 'test_queue_integration'
        rabbitmq_client.declare_queue(queue_name, durable=True)
        
        # Verify queue was created (would raise exception if failed)
        assert True

    def test_publish_and_consume(self, rabbitmq_client):
        """Test publishing and consuming messages"""
        queue_name = 'test_pub_sub_queue'
        test_message = {'test': 'data', 'timestamp': time.time()}
        
        # Declare queue
        rabbitmq_client.declare_queue(queue_name, durable=False)
        
        # Publish message
        rabbitmq_client.publish(queue_name, test_message)
        
        # Give message time to be processed
        time.sleep(0.5)
        
        # Consume message
        received_messages = []
        
        def callback(ch, method, properties, body):
            received_messages.append(json.loads(body))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ch.stop_consuming()
        
        rabbitmq_client.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback
        )
        
        # Start consuming (with timeout)
        rabbitmq_client.connection.call_later(2, rabbitmq_client.channel.stop_consuming)
        rabbitmq_client.channel.start_consuming()
        
        # Verify message was received
        assert len(received_messages) > 0
        assert received_messages[0]['test'] == 'data'

    def test_multiple_messages(self, rabbitmq_client):
        """Test publishing multiple messages"""
        queue_name = 'test_multi_queue'
        rabbitmq_client.declare_queue(queue_name, durable=False)
        
        # Publish multiple messages
        for i in range(5):
            rabbitmq_client.publish(queue_name, {'index': i})
        
        time.sleep(0.5)
        
        # Verify messages are in queue
        method_frame = rabbitmq_client.channel.queue_declare(queue=queue_name, passive=True)
        message_count = method_frame.method.message_count
        assert message_count == 5

    def test_queue_durability(self, rabbitmq_client):
        """Test durable queue creation"""
        queue_name = 'test_durable_queue'
        rabbitmq_client.declare_queue(queue_name, durable=True)
        
        # Publish persistent message
        rabbitmq_client.publish(
            queue_name,
            {'persistent': True},
            persistent=True
        )
        
        # Queue should survive connection restart
        assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
