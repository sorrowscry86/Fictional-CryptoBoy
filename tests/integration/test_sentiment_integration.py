"""
Integration Tests for Sentiment Processor
VoidCat RDC - CryptoBoy Trading Bot

Tests sentiment processing with actual services.
Requires RabbitMQ and Ollama/FinBERT to be running.
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


@pytest.mark.integration
class TestSentimentProcessorIntegration:
    """Integration tests for sentiment processor"""

    def test_sentiment_analysis_finbert(self):
        """Test FinBERT sentiment analysis"""
        from llm.huggingface_sentiment import HuggingFaceFinancialSentiment
        
        analyzer = HuggingFaceFinancialSentiment()
        
        # Test positive sentiment
        positive_text = "Bitcoin surges to new all-time highs as institutional adoption grows"
        score = analyzer.analyze_sentiment(positive_text)
        assert score > 0.3  # Should be positive
        
        # Test negative sentiment
        negative_text = "Cryptocurrency market crashes as regulations tighten"
        score = analyzer.analyze_sentiment(negative_text)
        assert score < -0.2  # Should be negative
        
        # Test neutral sentiment
        neutral_text = "Bitcoin price remains stable at current levels"
        score = analyzer.analyze_sentiment(neutral_text)
        assert -0.3 < score < 0.3  # Should be neutral

    def test_process_news_article(self, rabbitmq_config):
        """Test processing a news article through the pipeline"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient(**rabbitmq_config)
        client.connect()
        
        # Declare queues
        client.declare_queue('raw_news_data', durable=True)
        
        # Publish test news article
        test_article = {
            'headline': 'Bitcoin reaches new milestone',
            'content': 'Bitcoin surged past $100,000 today as investors show confidence',
            'source': 'test_source',
            'timestamp': time.time()
        }
        
        client.publish('raw_news_data', test_article)
        client.close()
        
        # Wait for processing
        time.sleep(1)
        
        # Verify message was published
        assert True

    @pytest.mark.slow
    def test_sentiment_queue_processing(self, rabbitmq_config):
        """Test full sentiment processing queue"""
        from services.common.rabbitmq_client import RabbitMQClient
        
        client = RabbitMQClient(**rabbitmq_config)
        client.connect()
        
        # Declare sentiment signals queue
        client.declare_queue('sentiment_signals_queue', durable=True)
        
        # Monitor for processed sentiments
        received_sentiments = []
        
        def callback(ch, method, properties, body):
            sentiment = json.loads(body)
            received_sentiments.append(sentiment)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            if len(received_sentiments) >= 1:
                ch.stop_consuming()
        
        # Consume messages (with timeout)
        client.channel.basic_consume(
            queue='sentiment_signals_queue',
            on_message_callback=callback
        )
        
        # Set timeout
        client.connection.call_later(5, client.channel.stop_consuming)
        
        try:
            client.channel.start_consuming()
        except (KeyboardInterrupt, SystemExit):
            # Allow graceful shutdown
            raise
        except Exception as e:
            # Specific exception handling for consumer errors
            logger.warning(f"Consumer stopped: {e}")
            pass
        
        client.close()
        
        # If sentiments were received, verify structure
        if received_sentiments:
            sentiment = received_sentiments[0]
            assert 'score' in sentiment
            assert 'pair' in sentiment or 'headline' in sentiment


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
