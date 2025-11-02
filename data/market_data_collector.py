"""
Market Data Collector - Fetches OHLCV data from Binance
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd
import ccxt
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketDataCollector:
    """Collects and manages market data from Binance"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        data_dir: str = "data/ohlcv_data",
        exchange_name: str = "coinbase"
    ):
        """
        Initialize the market data collector

        Args:
            api_key: Exchange API key (optional for public data)
            api_secret: Exchange API secret (optional for public data)
            data_dir: Directory to store historical data
            exchange_name: Exchange to use ('coinbase', 'binance', etc.)
        """
        # Get credentials from environment if not provided
        if exchange_name == 'coinbase':
            api_key = api_key or os.getenv('COINBASE_API_KEY', '')
            api_secret = api_secret or os.getenv('COINBASE_API_SECRET', '')
        else:
            api_key = api_key or os.getenv('BINANCE_API_KEY', '')
            api_secret = api_secret or os.getenv('BINANCE_API_SECRET', '')
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Automatic rate limiting
            'options': {
                'defaultType': 'spot',
            }
        })
        
        self.exchange_name = exchange_name

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized MarketDataCollector with {exchange_name} exchange, data_dir: {self.data_dir}")

    def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a symbol

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h', '4h', '1d')
            start_date: Start date for historical data
            end_date: End date for historical data
            limit: Maximum candles per request

        Returns:
            DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        logger.info(f"Fetching historical data for {symbol} from {start_date} to {end_date}")

        all_ohlcv = []
        since = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        while since < end_timestamp:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1

                # Rate limiting compliance
                time.sleep(self.exchange.rateLimit / 1000)

                logger.debug(f"Fetched {len(ohlcv)} candles, total: {len(all_ohlcv)}")

            except Exception as e:
                logger.error(f"Error fetching OHLCV data: {e}")
                break

        if not all_ohlcv:
            logger.warning(f"No data fetched for {symbol}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol

        # Remove duplicates
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)

        logger.info(f"Fetched {len(df)} candles for {symbol}")
        return df

    def fetch_latest_candle(
        self,
        symbol: str,
        timeframe: str = '1h'
    ) -> Optional[Dict]:
        """
        Fetch the most recent candle for a symbol

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe

        Returns:
            Dictionary with latest candle data
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=1)
            if ohlcv:
                candle = ohlcv[0]
                return {
                    'timestamp': pd.to_datetime(candle[0], unit='ms'),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5],
                    'symbol': symbol
                }
        except Exception as e:
            logger.error(f"Error fetching latest candle for {symbol}: {e}")
        return None

    def save_to_csv(self, df: pd.DataFrame, symbol: str, timeframe: str = '1h'):
        """
        Save OHLCV data to CSV file

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair
            timeframe: Candle timeframe
        """
        if df.empty:
            logger.warning("Cannot save empty DataFrame")
            return

        filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
        filepath = self.data_dir / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} rows to {filepath}")

    def load_from_csv(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        """
        Load OHLCV data from CSV file

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe

        Returns:
            DataFrame with OHLCV data
        """
        filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return pd.DataFrame()

        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        logger.info(f"Loaded {len(df)} rows from {filepath}")
        return df

    def update_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        days: int = 365
    ) -> pd.DataFrame:
        """
        Update historical data by fetching new candles

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            days: Number of days to fetch if no existing data

        Returns:
            Updated DataFrame
        """
        existing_df = self.load_from_csv(symbol, timeframe)

        if existing_df.empty:
            # Fetch full historical data
            start_date = datetime.now() - timedelta(days=days)
            df = self.get_historical_ohlcv(symbol, timeframe, start_date)
        else:
            # Fetch only new data
            last_timestamp = existing_df['timestamp'].max()
            start_date = last_timestamp + timedelta(hours=1)
            new_df = self.get_historical_ohlcv(symbol, timeframe, start_date)

            if not new_df.empty:
                df = pd.concat([existing_df, new_df], ignore_index=True)
                df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
                df = df.sort_values('timestamp').reset_index(drop=True)
            else:
                df = existing_df

        if not df.empty:
            self.save_to_csv(df, symbol, timeframe)

        return df

    def validate_data_consistency(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data integrity

        Args:
            df: DataFrame to validate

        Returns:
            True if data is valid
        """
        if df.empty:
            logger.warning("Empty DataFrame")
            return False

        # Check for required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            logger.error(f"Missing columns: {missing_cols}")
            return False

        # Check for null values
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            logger.warning(f"Null values found:\n{null_counts[null_counts > 0]}")
            return False

        # Check timestamp ordering
        if not df['timestamp'].is_monotonic_increasing:
            logger.warning("Timestamps are not in ascending order")
            return False

        # Check price consistency (high >= low, etc.)
        invalid_prices = (
            (df['high'] < df['low'])
            | (df['high'] < df['open'])
            | (df['high'] < df['close'])
            | (df['low'] > df['open'])
            | (df['low'] > df['close'])
        )
        if invalid_prices.any():
            logger.error(f"Found {invalid_prices.sum()} rows with invalid price relationships")
            return False

        logger.info("Data validation passed")
        return True


if __name__ == "__main__":
    # Example usage
    from dotenv import load_dotenv
    load_dotenv()

    collector = MarketDataCollector(exchange_name='coinbase')

    # Fetch and save historical data for trading pairs
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    for symbol in symbols:
        logger.info(f"Processing {symbol}...")
        df = collector.update_data(symbol, timeframe='1h', days=365)

        if not df.empty:
            is_valid = collector.validate_data_consistency(df)
            logger.info(f"{symbol}: {len(df)} candles, valid={is_valid}")
            logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
