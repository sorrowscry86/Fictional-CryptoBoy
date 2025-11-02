"""
RabbitMQ Client for CryptoBoy Microservices
Provides connection management and publishing/consuming utilities
"""
import os
import time
import json
import logging
from typing import Callable, Dict, Any, Optional
import pika
from pika.exceptions import AMQPConnectionError

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """Thread-safe RabbitMQ client with automatic reconnection"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        max_retries: int = 5,
        retry_delay: int = 5
    ):
        """
        Initialize RabbitMQ client

        Args:
            host: RabbitMQ host (defaults to env RABBITMQ_HOST or 'rabbitmq')
            port: RabbitMQ port (defaults to env RABBITMQ_PORT or 5672)
            username: RabbitMQ username (defaults to env RABBITMQ_USER or 'cryptoboy')
            password: RabbitMQ password (defaults to env RABBITMQ_PASS or 'cryptoboy123')
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.host = host or os.getenv('RABBITMQ_HOST', 'rabbitmq')
        self.port = int(port or os.getenv('RABBITMQ_PORT', 5672))
        self.username = username or os.getenv('RABBITMQ_USER', 'cryptoboy')
        self.password = password or os.getenv('RABBITMQ_PASS', 'cryptoboy123')
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None

    def connect(self) -> None:
        """Establish connection to RabbitMQ with retry logic"""
        for attempt in range(self.max_retries):
            try:
                credentials = pika.PlainCredentials(self.username, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )

                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()

                logger.info(f"Successfully connected to RabbitMQ at {self.host}:{self.port}")
                return

            except AMQPConnectionError as e:
                logger.warning(
                    f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise ConnectionError(f"Could not connect to RabbitMQ after {self.max_retries} attempts")

    def ensure_connection(self) -> None:
        """Ensure connection is active, reconnect if needed"""
        if self.connection is None or self.connection.is_closed:
            logger.info("Connection is closed, reconnecting...")
            self.connect()

        if self.channel is None or self.channel.is_closed:
            logger.info("Channel is closed, recreating...")
            self.channel = self.connection.channel()

    def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        auto_delete: bool = False,
        arguments: Dict[str, Any] = None
    ) -> None:
        """
        Declare a queue

        Args:
            queue_name: Name of the queue
            durable: Whether the queue survives broker restart
            auto_delete: Whether queue is deleted when no longer in use
            arguments: Additional queue arguments (e.g., message TTL, max length)
        """
        self.ensure_connection()
        self.channel.queue_declare(
            queue=queue_name,
            durable=durable,
            auto_delete=auto_delete,
            arguments=arguments or {}
        )
        logger.info(f"Queue '{queue_name}' declared (durable={durable})")

    def publish(
        self,
        queue_name: str,
        message: Dict[str, Any],
        persistent: bool = True,
        declare_queue: bool = True
    ) -> None:
        """
        Publish a message to a queue

        Args:
            queue_name: Target queue name
            message: Message data (will be JSON serialized)
            persistent: Whether message survives broker restart
            declare_queue: Whether to declare the queue before publishing
        """
        self.ensure_connection()

        if declare_queue:
            self.declare_queue(queue_name)

        body = json.dumps(message).encode('utf-8')
        properties = pika.BasicProperties(
            delivery_mode=2 if persistent else 1,  # 2 = persistent
            content_type='application/json'
        )

        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=body,
                properties=properties
            )
            logger.debug(f"Published message to '{queue_name}': {len(body)} bytes")
        except Exception as e:
            logger.error(f"Failed to publish message to '{queue_name}': {e}")
            raise

    def consume(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False,
        prefetch_count: int = 1,
        declare_queue: bool = True
    ) -> None:
        """
        Start consuming messages from a queue

        Args:
            queue_name: Queue to consume from
            callback: Function to call for each message (ch, method, properties, body)
            auto_ack: Whether to automatically acknowledge messages
            prefetch_count: Number of messages to prefetch (QoS)
            declare_queue: Whether to declare the queue before consuming
        """
        self.ensure_connection()

        if declare_queue:
            self.declare_queue(queue_name)

        self.channel.basic_qos(prefetch_count=prefetch_count)
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=auto_ack
        )

        logger.info(f"Starting to consume from '{queue_name}' (prefetch={prefetch_count})")

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping consumer...")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error during consumption: {e}")
            raise

    def stop_consuming(self) -> None:
        """Stop consuming messages"""
        if self.channel and not self.channel.is_closed:
            self.channel.stop_consuming()
            logger.info("Stopped consuming messages")

    def close(self) -> None:
        """Close channel and connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
            logger.info("Channel closed")

        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Connection closed")


def create_consumer_callback(
    process_func: Callable[[Dict[str, Any]], None],
    auto_ack: bool = False
) -> Callable:
    """
    Create a callback function for message consumption

    Args:
        process_func: Function that processes the message data (takes Dict, returns None)
        auto_ack: Whether to automatically acknowledge messages

    Returns:
        Callback function compatible with pika's basic_consume
    """
    def callback(ch, method, properties, body):
        try:
            # Decode and parse message
            message = json.loads(body.decode('utf-8'))
            logger.debug(f"Received message: {message.get('type', 'unknown')}")

            # Process message
            process_func(message)

            # Acknowledge if not auto-ack
            if not auto_ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Message acknowledged: {method.delivery_tag}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message JSON: {e}")
            # Reject message without requeue (send to dead letter queue if configured)
            if not auto_ack:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Requeue message for retry (or send to dead letter after max retries)
            if not auto_ack:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    return callback
