"""
Unit Tests for RabbitMQ Client
VoidCat RDC - CryptoBoy Trading Bot

Tests RabbitMQClient in isolation using mocking.
"""
import json
import unittest
from unittest.mock import MagicMock, Mock, patch, call

import pytest


class TestRabbitMQClient(unittest.TestCase):
    """Test RabbitMQClient functionality"""

    @patch('services.common.rabbitmq_client.pika')
    def test_connect(self, mock_pika):
        """Test successful connection"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        # Setup mocks
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # Create client and connect
        client = RabbitMQClient(host='localhost', port=5672, username='test', password='test')
        client.connect()
        
        # Verify connection was established
        assert client.connection is not None
        assert client.channel is not None
        mock_pika.BlockingConnection.assert_called()

    @patch('services.common.rabbitmq_client.pika')
    def test_declare_queue(self, mock_pika):
        """Test queue declaration"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        # Setup mocks
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        client = RabbitMQClient()
        client.connect()
        
        # Declare queue
        client.declare_queue('test_queue', durable=True)
        
        # Verify queue was declared
        mock_channel.queue_declare.assert_called()

    @patch('services.common.rabbitmq_client.pika')
    def test_publish_message(self, mock_pika):
        """Test message publishing"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        # Setup mocks
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        client = RabbitMQClient()
        client.connect()
        
        # Publish message
        test_message = {'test': 'data'}
        client.publish('test_queue', test_message)
        
        # Verify message was published
        mock_channel.basic_publish.assert_called()

    @patch('services.common.rabbitmq_client.pika')
    def test_close_connection(self, mock_pika):
        """Test connection closure"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        # Setup mocks
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        mock_channel.is_closed = False
        mock_connection.is_closed = False
        
        client = RabbitMQClient()
        client.connect()
        
        # Close connection
        client.close()
        
        # Verify channel and connection were closed
        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()


class TestRabbitMQClientIntegration:
    """Integration-style tests for RabbitMQ client (requires actual service)"""

    @pytest.mark.integration
    def test_connection_to_real_service(self):
        """Test connection to actual RabbitMQ (skipped in unit tests)"""
        pytest.skip("Integration test - requires running RabbitMQ service")


if __name__ == '__main__':
    unittest.main()
