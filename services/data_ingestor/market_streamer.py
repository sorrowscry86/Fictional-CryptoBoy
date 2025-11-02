"""
Market Data Streamer - Real-time market data ingestion via WebSockets
Publishes OHLCV candles to RabbitMQ for downstream processing
"""
import os
import sys
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import ccxt.pro as ccxtpro

from services.common.rabbitmq_client import RabbitMQClient
from services.common.logging_config import setup_logging

logger = setup_logging('market-streamer')


class MarketDataStreamer:
    """
    Real-time market data streamer using WebSocket connections
    Publishes candle data to RabbitMQ for microservices consumption
    """

    def __init__(
        self,
        symbols: List[str] = None,
        timeframe: str = '1m',
        queue_name: str = 'raw_market_data'
    ):
        """
        Initialize market data streamer

        Args:
            symbols: List of trading pairs to stream (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, etc.)
            queue_name: RabbitMQ queue for publishing data
        """
        self.symbols = symbols or self._get_default_symbols()
        self.timeframe = timeframe
        self.queue_name = queue_name

        # Initialize RabbitMQ client
        self.rabbitmq = RabbitMQClient()
        self.rabbitmq.connect()
        self.rabbitmq.declare_queue(self.queue_name, durable=True)

        # Initialize CCXT Pro exchange
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')

        self.exchange = ccxtpro.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })

        # Track last published candles to avoid duplicates
        self.last_candles = {}

        logger.info(f"Initialized MarketDataStreamer for {len(self.symbols)} symbols")
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        logger.info(f"Timeframe: {self.timeframe}")

    @staticmethod
    def _get_default_symbols() -> List[str]:
        """Get default trading pairs from environment or use defaults"""
        env_symbols = os.getenv('TRADING_PAIRS', '')
        if env_symbols:
            return [s.strip() for s in env_symbols.split(',')]
        return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

    def _format_candle_message(
        self,
        symbol: str,
        candle: List[Any]
    ) -> Dict[str, Any]:
        """
        Format a candle into a standardized message

        Args:
            symbol: Trading pair
            candle: OHLCV candle [timestamp, open, high, low, close, volume]

        Returns:
            Formatted message dictionary
        """
        timestamp_ms = int(candle[0])
        timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()

        return {
            'type': 'market_data',
            'source': 'binance_websocket',
            'symbol': symbol,
            'timeframe': self.timeframe,
            'timestamp': timestamp_iso,
            'timestamp_ms': timestamp_ms,
            'data': {
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            },
            'collected_at': datetime.utcnow().isoformat()
        }

    def _should_publish_candle(self, symbol: str, timestamp_ms: int) -> bool:
        """
        Check if a candle should be published (avoid duplicates)

        Args:
            symbol: Trading pair
            timestamp_ms: Candle timestamp in milliseconds

        Returns:
            True if candle should be published
        """
        last_ts = self.last_candles.get(symbol, 0)
        if timestamp_ms > last_ts:
            self.last_candles[symbol] = timestamp_ms
            return True
        return False

    async def stream_symbol(self, symbol: str):
        """
        Stream OHLCV candles for a single symbol

        Args:
            symbol: Trading pair to stream
        """
        logger.info(f"Starting stream for {symbol}")

        try:
            while True:
                try:
                    # Watch OHLCV candles via WebSocket
                    candles = await self.exchange.watch_ohlcv(symbol, self.timeframe)

                    # Process the latest candle
                    if candles:
                        latest_candle = candles[-1]
                        timestamp_ms = int(latest_candle[0])

                        # Only publish new candles
                        if self._should_publish_candle(symbol, timestamp_ms):
                            message = self._format_candle_message(symbol, latest_candle)

                            # Publish to RabbitMQ
                            self.rabbitmq.publish(
                                self.queue_name,
                                message,
                                persistent=True,
                                declare_queue=False
                            )

                            logger.info(
                                f"Published {symbol} candle: "
                                f"close={message['data']['close']:.2f}, "
                                f"volume={message['data']['volume']:.2f}"
                            )

                except ccxtpro.NetworkError as e:
                    logger.error(f"Network error for {symbol}: {e}")
                    await asyncio.sleep(5)  # Wait before retry
                except ccxtpro.ExchangeError as e:
                    logger.error(f"Exchange error for {symbol}: {e}")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Unexpected error for {symbol}: {e}", exc_info=True)
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for {symbol}")
        except Exception as e:
            logger.error(f"Fatal error streaming {symbol}: {e}", exc_info=True)

    async def stream_all_symbols(self):
        """Stream all configured symbols concurrently"""
        logger.info(f"Starting streams for {len(self.symbols)} symbols")

        # Create streaming tasks for all symbols
        tasks = [
            asyncio.create_task(self.stream_symbol(symbol))
            for symbol in self.symbols
        ]

        # Wait for all tasks (runs indefinitely)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run(self):
        """Main entry point for the streamer"""
        logger.info("Market Data Streamer starting...")

        try:
            await self.stream_all_symbols()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Clean shutdown of connections"""
        logger.info("Shutting down Market Data Streamer...")

        try:
            # Close exchange connection
            await self.exchange.close()
            logger.info("Exchange connection closed")
        except Exception as e:
            logger.error(f"Error closing exchange: {e}")

        try:
            # Close RabbitMQ connection
            self.rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {e}")


async def main():
    """Main function"""
    # Get configuration from environment
    symbols_env = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT,BNB/USDT')
    symbols = [s.strip() for s in symbols_env.split(',')]
    timeframe = os.getenv('CANDLE_TIMEFRAME', '1m')

    # Create and run streamer
    streamer = MarketDataStreamer(
        symbols=symbols,
        timeframe=timeframe,
        queue_name='raw_market_data'
    )

    await streamer.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
