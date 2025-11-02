"""
Unit Tests for RabbitMQ Client
VoidCat RDC - CryptoBoy Trading Bot

Tests RabbitMQClient in isolation using mocking.
"""
import json
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestRabbitMQClient(unittest.TestCase):
    """Test RabbitMQClient functionality"""

    @patch('services.common.rabbitmq_client.pika')
    def setUp(self, mock_pika):
        """Set up test fixtures"""
        self.mock_pika = mock_pika
        from services.common.rabbitmq_client import RabbitMQClient
        
        self.client = RabbitMQClient(
            host='localhost',
            port=5672,
            username='test',
            password='test'
        )

    @patch('services.common.rabbitmq_client.pika')
    def test_connect(self, mock_pika):
        """Test successful connection"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient()
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        client.connect()
        
        assert client.connection is not None
        assert client.channel is not None
        mock_pika.BlockingConnection.assert_called_once()

    @patch('services.common.rabbitmq_client.pika')
    def test_declare_queue(self, mock_pika):
        """Test queue declaration"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient()
        mock_channel = MagicMock()
        client.channel = mock_channel
        
        client.declare_queue('test_queue', durable=True)
        
        mock_channel.queue_declare.assert_called_once_with(
            queue='test_queue',
            durable=True
        )

    @patch('services.common.rabbitmq_client.pika')
    def test_publish_message(self, mock_pika):
        """Test message publishing"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient()
        mock_channel = MagicMock()
        client.channel = mock_channel
        
        test_message = {'test': 'data'}
        client.publish('test_queue', test_message)
        
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]['routing_key'] == 'test_queue'
        assert json.loads(call_args[1]['body']) == test_message

    @patch('services.common.rabbitmq_client.pika')
    def test_close_connection(self, mock_pika):
        """Test connection closure"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient()
        mock_connection = MagicMock()
        client.connection = mock_connection
        
        client.close()
        
        mock_connection.close.assert_called_once()


class TestRabbitMQClientIntegration:
    """Integration-style tests for RabbitMQ client (requires actual service)"""

    @pytest.mark.integration
    def test_connection_to_real_service(self):
        """Test connection to actual RabbitMQ (skipped in unit tests)"""
        pytest.skip("Integration test - requires running RabbitMQ service")


if __name__ == '__main__':
    unittest.main()
