"""
LLM Sentiment Trading Strategy for Freqtrade
Combines technical indicators with LLM-based sentiment analysis
"""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from pandas import DataFrame
from freqtrade.strategy import IStrategy, informative
import talib.abstract as ta
from freqtrade.persistence import Trade
import redis

logger = logging.getLogger(__name__)


class LLMSentimentStrategy(IStrategy):
    """
    Trading strategy that combines sentiment analysis with technical indicators

    Strategy Logic:
    - BUY when: Positive sentiment (>0.7) + positive momentum + RSI not overbought
    - SELL when: Negative sentiment (<-0.5) OR take profit OR stop loss
    """

    # Strategy configuration
    INTERFACE_VERSION = 3

    # Minimal ROI - Take profit levels
    minimal_roi = {
        "0": 0.05,    # 5% profit target
        "30": 0.03,   # 3% after 30 minutes
        "60": 0.02,   # 2% after 1 hour
        "120": 0.01   # 1% after 2 hours
    }

    # Stop loss
    stoploss = -0.03  # -3% stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Timeframe
    timeframe = '1h'

    # Startup candle count
    startup_candle_count: int = 50

    # Process only new candles
    process_only_new_candles = True

    # Use sell signal
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.0

    # Sentiment configuration
    sentiment_buy_threshold = 0.7
    sentiment_sell_threshold = -0.5
    sentiment_stale_hours = 4  # Consider sentiment stale after this many hours

    # Technical indicator parameters
    rsi_period = 14
    rsi_buy_threshold = 30
    rsi_sell_threshold = 70

    ema_short_period = 12
    ema_long_period = 26

    # Position sizing
    position_adjustment_enable = False

    def __init__(self, config: dict) -> None:
        """Initialize strategy"""
        super().__init__(config)

        # Initialize Redis client for sentiment cache
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', 6379))

        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def bot_start(self, **kwargs) -> None:
        """
        Called only once when the bot starts.
        """
        logger.info("LLMSentimentStrategy started with Redis cache")
        if self.redis_client:
            logger.info("Redis connection active - real-time sentiment enabled")
        else:
            logger.warning("Redis connection unavailable - sentiment signals disabled")

    def _get_sentiment_score(self, pair: str, current_candle_timestamp: pd.Timestamp) -> float:
        """
        Get sentiment score for a given pair from Redis cache

        Args:
            pair: Trading pair (e.g., 'BTC/USDT')
            current_candle_timestamp: The timestamp of the current candle

        Returns:
            Sentiment score (0.0 if not found or stale)
        """
        if not self.redis_client:
            return 0.0

        try:
            key = f"sentiment:{pair}"
            cached_data = self.redis_client.hgetall(key)

            if not cached_data or 'score' not in cached_data:
                logger.debug(f"No sentiment found for {pair}")
                return 0.0

            # Check if sentiment is reasonably fresh
            cached_ts = pd.to_datetime(cached_data.get('timestamp', '1970-01-01'), utc=True)
            # Make current_candle_timestamp timezone-aware if needed
            if current_candle_timestamp.tzinfo is None:
                current_candle_timestamp = current_candle_timestamp.tz_localize('UTC')
            age = (current_candle_timestamp - cached_ts).total_seconds() / 3600  # hours

            if age > self.sentiment_stale_hours:
                logger.debug(
                    f"Stale sentiment for {pair}: {age:.1f} hours old "
                    f"(threshold: {self.sentiment_stale_hours}h)"
                )
                return 0.0

            score = float(cached_data['score'])
            logger.debug(
                f"Sentiment for {pair}: {score:+.2f} "
                f"(age: {age:.1f}h, headline: {cached_data.get('headline', '')[:30]}...)"
            )
            return score

        except Exception as e:
            logger.error(f"Error fetching sentiment from Redis for {pair}: {e}")
            return 0.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add technical indicators and sentiment scores to the dataframe

        Args:
            dataframe: DataFrame with OHLCV data
            metadata: Additional metadata

        Returns:
            DataFrame with indicators
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)

        # EMAs
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=self.ema_short_period)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=self.ema_long_period)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']

        # Volume indicators
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()

        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # Add sentiment scores from Redis cache
        pair = metadata['pair']
        dataframe['sentiment'] = dataframe['date'].apply(
            lambda x: self._get_sentiment_score(pair, x)
        )

        # Sentiment momentum (rate of change)
        dataframe['sentiment_momentum'] = dataframe['sentiment'].diff()

        logger.debug(f"Populated indicators for {pair}")
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define buy conditions

        Args:
            dataframe: DataFrame with indicators
            metadata: Additional metadata

        Returns:
            DataFrame with buy signals
        """
        dataframe.loc[
            (
                # Sentiment is strongly positive
                (dataframe['sentiment'] > self.sentiment_buy_threshold) &

                # Technical confirmation: upward momentum
                (dataframe['ema_short'] > dataframe['ema_long']) &

                # RSI not overbought
                (dataframe['rsi'] < self.rsi_sell_threshold) &
                (dataframe['rsi'] > self.rsi_buy_threshold) &

                # MACD bullish
                (dataframe['macd'] > dataframe['macdsignal']) &

                # Volume above average
                (dataframe['volume'] > dataframe['volume_mean']) &

                # Safety: not at upper Bollinger Band
                (dataframe['close'] < dataframe['bb_upper'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define sell conditions

        Args:
            dataframe: DataFrame with indicators
            metadata: Additional metadata

        Returns:
            DataFrame with sell signals
        """
        dataframe.loc[
            (
                # Sentiment turns negative
                (
                    (dataframe['sentiment'] < self.sentiment_sell_threshold) |

                    # OR technical signals show weakness
                    (
                        (dataframe['ema_short'] < dataframe['ema_long']) &
                        (dataframe['rsi'] > self.rsi_sell_threshold)
                    ) |

                    # OR MACD turns bearish
                    (dataframe['macd'] < dataframe['macdsignal'])
                )
            ),
            'exit_long'] = 1

        return dataframe

    def custom_stake_amount(self,
                           pair: str,
                           current_time: datetime,
                           current_rate: float,
                           proposed_stake: float,
                           min_stake: Optional[float],
                           max_stake: float,
                           leverage: float,
                           entry_tag: Optional[str],
                           side: str,
                           **kwargs) -> float:
        """
        Customize stake amount based on sentiment strength

        Args:
            pair: Trading pair
            current_time: Current timestamp
            current_rate: Current price
            proposed_stake: Proposed stake amount
            min_stake: Minimum stake amount
            max_stake: Maximum stake amount
            leverage: Leverage
            entry_tag: Entry tag
            side: Trade side
            **kwargs: Additional arguments

        Returns:
            Stake amount to use
        """
        sentiment_score = self._get_sentiment_score(pair, pd.Timestamp(current_time))

        # Adjust stake based on sentiment strength
        if sentiment_score > 0.8:
            # Very strong sentiment: use max stake
            return max_stake
        elif sentiment_score > 0.7:
            # Strong sentiment: use 75% of max stake
            return max_stake * 0.75
        else:
            # Default stake
            return proposed_stake

    def confirm_trade_entry(self,
                           pair: str,
                           order_type: str,
                           amount: float,
                           rate: float,
                           time_in_force: str,
                           current_time: datetime,
                           entry_tag: Optional[str],
                           side: str,
                           **kwargs) -> bool:
        """
        Confirm trade entry (last chance to reject)

        Args:
            pair: Trading pair
            order_type: Order type
            amount: Trade amount
            rate: Entry rate
            time_in_force: Time in force
            current_time: Current timestamp
            entry_tag: Entry tag
            side: Trade side
            **kwargs: Additional arguments

        Returns:
            True to allow trade, False to reject
        """
        # Double-check sentiment before entry
        sentiment = self._get_sentiment_score(pair, pd.Timestamp(current_time))

        if sentiment < self.sentiment_buy_threshold:
            logger.info(f"Rejecting trade for {pair}: sentiment {sentiment:.2f} below threshold")
            return False

        return True

    def custom_exit(self,
                   pair: str,
                   trade: Trade,
                   current_time: datetime,
                   current_rate: float,
                   current_profit: float,
                   **kwargs) -> Optional[str]:
        """
        Custom exit logic

        Args:
            pair: Trading pair
            trade: Trade object
            current_time: Current timestamp
            current_rate: Current rate
            current_profit: Current profit
            **kwargs: Additional arguments

        Returns:
            Exit reason string or None
        """
        # Check for sentiment reversal
        sentiment = self._get_sentiment_score(pair, pd.Timestamp(current_time))

        if sentiment < -0.3 and current_profit > 0:
            logger.info(f"Exiting {pair} due to sentiment reversal: {sentiment:.2f}")
            return "sentiment_reversal"

        # Take profit on very strong gains even if sentiment is positive
        if current_profit > 0.10:  # 10% profit
            logger.info(f"Taking profit on {pair}: {current_profit:.2%}")
            return "take_profit_10pct"

        return None

    def leverage(self,
                pair: str,
                current_time: datetime,
                current_rate: float,
                proposed_leverage: float,
                max_leverage: float,
                entry_tag: Optional[str],
                side: str,
                **kwargs) -> float:
        """
        Set leverage (default: no leverage)

        Args:
            pair: Trading pair
            current_time: Current timestamp
            current_rate: Current rate
            proposed_leverage: Proposed leverage
            max_leverage: Maximum leverage
            entry_tag: Entry tag
            side: Trade side
            **kwargs: Additional arguments

        Returns:
            Leverage to use
        """
        # Conservative: no leverage
        return 1.0


if __name__ == "__main__":
    # This section is for testing the strategy independently
    print("LLM Sentiment Strategy for Freqtrade")
    print("=" * 60)
    print(f"Timeframe: {LLMSentimentStrategy.timeframe}")
    print(f"Stop Loss: {LLMSentimentStrategy.stoploss:.1%}")
    print(f"Minimal ROI: {LLMSentimentStrategy.minimal_roi}")
    print(f"Sentiment Buy Threshold: {LLMSentimentStrategy.sentiment_buy_threshold}")
    print(f"Sentiment Sell Threshold: {LLMSentimentStrategy.sentiment_sell_threshold}")
