"""
LLM Sentiment Trading Strategy for Freqtrade
Combines technical indicators with LLM-based sentiment analysis
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from pandas import DataFrame
from freqtrade.strategy import IStrategy, informative
import talib.abstract as ta
from freqtrade.persistence import Trade

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
    sentiment_data_path = "data/sentiment_signals.csv"
    sentiment_buy_threshold = 0.3  # Lowered from 0.7 to trigger trades with available data
    sentiment_sell_threshold = -0.3  # Adjusted to match buy threshold

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

        self.sentiment_df = None
        self.last_sentiment_load = None
        self.sentiment_load_interval = 3600  # Reload every hour

    def bot_start(self, **kwargs) -> None:
        """
        Called only once when the bot starts.
        Load sentiment data here.
        """
        logger.info("LLMSentimentStrategy started")
        self._load_sentiment_data()

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        Called at the start of each bot loop.
        Reload sentiment data periodically.
        """
        if (self.last_sentiment_load is None or
            (current_time - self.last_sentiment_load).total_seconds() > self.sentiment_load_interval):
            self._load_sentiment_data()
            self.last_sentiment_load = current_time

    def _load_sentiment_data(self) -> None:
        """Load sentiment data from CSV file"""
        try:
            sentiment_path = Path(self.sentiment_data_path)

            if not sentiment_path.exists():
                logger.warning(f"Sentiment data not found at {sentiment_path}")
                self.sentiment_df = None
                return

            self.sentiment_df = pd.read_csv(sentiment_path)
            
            # Convert timestamp to datetime (timezone-naive for consistency with Freqtrade)
            self.sentiment_df['timestamp'] = pd.to_datetime(
                self.sentiment_df['timestamp'], 
                utc=True
            ).dt.tz_localize(None)

            # Sort by timestamp
            self.sentiment_df = self.sentiment_df.sort_values('timestamp')

            logger.info(f"Loaded {len(self.sentiment_df)} sentiment records")
            logger.debug(f"Sentiment date range: {self.sentiment_df['timestamp'].min()} to {self.sentiment_df['timestamp'].max()}")

        except Exception as e:
            logger.error(f"Error loading sentiment data: {e}")
            self.sentiment_df = None

    def _get_sentiment_score(self, timestamp: datetime) -> float:
        """
        Get sentiment score for a given timestamp

        Args:
            timestamp: The timestamp to look up

        Returns:
            Sentiment score (0.0 if not found)
        """
        if self.sentiment_df is None or self.sentiment_df.empty:
            return 0.0

        try:
            # Ensure timestamp is timezone-naive
            if hasattr(timestamp, 'tz') and timestamp.tz is not None:
                timestamp = timestamp.tz_localize(None)
            
            # Convert to pandas Timestamp for comparison
            timestamp = pd.Timestamp(timestamp)
            
            # Find the most recent sentiment before or at this timestamp
            mask = self.sentiment_df['timestamp'] <= timestamp
            matching_rows = self.sentiment_df[mask]

            if matching_rows.empty:
                return 0.0

            # Get the most recent sentiment
            latest_sentiment = matching_rows.iloc[-1]
            score = latest_sentiment.get('sentiment_score', 0.0)

            # Check if smoothed sentiment is available
            if 'smoothed_sentiment' in matching_rows.columns:
                score = latest_sentiment.get('smoothed_sentiment', score)

            return float(score)

        except Exception as e:
            logger.error(f"Error getting sentiment score: {e}")
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

        # Add sentiment scores
        dataframe['sentiment'] = 0.0
        for idx, row in dataframe.iterrows():
            timestamp = row['date']
            sentiment_score = self._get_sentiment_score(timestamp)
            dataframe.at[idx, 'sentiment'] = sentiment_score

        # Sentiment momentum (rate of change)
        dataframe['sentiment_momentum'] = dataframe['sentiment'].diff()

        logger.debug(f"Populated indicators for {metadata.get('pair', 'unknown')}")
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
        sentiment_score = self._get_sentiment_score(current_time)

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
        sentiment = self._get_sentiment_score(current_time)

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
        sentiment = self._get_sentiment_score(current_time)

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
