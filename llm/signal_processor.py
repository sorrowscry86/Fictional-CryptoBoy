"""
Signal Processor - Aggregates sentiment scores into trading signals
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes and aggregates sentiment signals for trading"""

    def __init__(self, output_dir: str = "data"):
        """
        Initialize the signal processor

        Args:
            output_dir: Directory to save processed signals
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate_rolling_sentiment(
        self,
        df: pd.DataFrame,
        window_hours: int = 24,
        timestamp_col: str = "timestamp",
        score_col: str = "sentiment_score",
    ) -> pd.DataFrame:
        """
        Calculate rolling average sentiment

        Args:
            df: DataFrame with sentiment scores
            window_hours: Rolling window size in hours
            timestamp_col: Name of timestamp column
            score_col: Name of sentiment score column

        Returns:
            DataFrame with rolling sentiment
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return df

        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values(timestamp_col)

        # Set timestamp as index for rolling calculation
        df_indexed = df.set_index(timestamp_col)

        # Calculate rolling mean
        window = f"{window_hours}H"
        df["rolling_sentiment"] = df_indexed[score_col].rolling(window=window, min_periods=1).mean().values

        # Calculate rolling std for volatility
        df["sentiment_volatility"] = df_indexed[score_col].rolling(window=window, min_periods=1).std().values

        logger.info(f"Calculated rolling sentiment with {window_hours}h window")
        return df

    def aggregate_signals(
        self,
        df: pd.DataFrame,
        timeframe: str = "1H",
        timestamp_col: str = "timestamp",
        score_col: str = "sentiment_score",
        aggregation_method: str = "mean",
    ) -> pd.DataFrame:
        """
        Aggregate sentiment signals to match trading timeframe

        Args:
            df: DataFrame with sentiment scores
            timeframe: Target timeframe (e.g., '1H', '4H', '1D')
            timestamp_col: Name of timestamp column
            score_col: Name of sentiment score column
            aggregation_method: How to aggregate ('mean', 'weighted', 'exponential')

        Returns:
            Aggregated DataFrame
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return pd.DataFrame()

        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values(timestamp_col)

        # Resample to target timeframe
        df_resampled = (
            df.set_index(timestamp_col)
            .resample(timeframe)
            .agg(
                {
                    score_col: aggregation_method if aggregation_method == "mean" else "mean",
                    "headline": "count",  # Count articles per period
                }
            )
            .reset_index()
        )

        df_resampled.columns = [timestamp_col, "sentiment_score", "article_count"]

        # Fill missing values with neutral sentiment
        df_resampled["sentiment_score"] = df_resampled["sentiment_score"].fillna(0.0)
        df_resampled["article_count"] = df_resampled["article_count"].fillna(0).astype(int)

        logger.info(f"Aggregated signals to {timeframe} timeframe: {len(df_resampled)} periods")
        return df_resampled

    def smooth_signal_noise(
        self, df: pd.DataFrame, method: str = "ema", window: int = 3, score_col: str = "sentiment_score"
    ) -> pd.DataFrame:
        """
        Smooth sentiment signals to reduce noise

        Args:
            df: DataFrame with sentiment scores
            method: Smoothing method ('ema', 'sma', 'gaussian')
            window: Window size for smoothing
            score_col: Name of sentiment score column

        Returns:
            DataFrame with smoothed signals
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return df

        df = df.copy()

        if method == "ema":
            # Exponential Moving Average
            df["smoothed_sentiment"] = df[score_col].ewm(span=window, adjust=False).mean()
        elif method == "sma":
            # Simple Moving Average
            df["smoothed_sentiment"] = df[score_col].rolling(window=window, min_periods=1).mean()
        elif method == "gaussian":
            # Gaussian smoothing
            from scipy.ndimage import gaussian_filter1d

            df["smoothed_sentiment"] = gaussian_filter1d(df[score_col].values, sigma=window)
        else:
            logger.warning(f"Unknown smoothing method: {method}")
            df["smoothed_sentiment"] = df[score_col]

        logger.info(f"Applied {method} smoothing with window={window}")
        return df

    def create_trading_signals(
        self,
        df: pd.DataFrame,
        score_col: str = "sentiment_score",
        bullish_threshold: float = 0.3,
        bearish_threshold: float = -0.3,
    ) -> pd.DataFrame:
        """
        Create binary trading signals from sentiment scores

        Args:
            df: DataFrame with sentiment scores
            score_col: Name of sentiment score column
            bullish_threshold: Threshold for bullish signal
            bearish_threshold: Threshold for bearish signal

        Returns:
            DataFrame with trading signals
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return df

        df = df.copy()

        # Create signal column
        df["signal"] = 0  # Neutral

        df.loc[df[score_col] >= bullish_threshold, "signal"] = 1  # Buy
        df.loc[df[score_col] <= bearish_threshold, "signal"] = -1  # Sell

        # Calculate signal strength (distance from threshold)
        df["signal_strength"] = df[score_col].abs()

        # Count signals
        buy_signals = (df["signal"] == 1).sum()
        sell_signals = (df["signal"] == -1).sum()
        neutral = (df["signal"] == 0).sum()

        logger.info(f"Created signals - Buy: {buy_signals}, Sell: {sell_signals}, Neutral: {neutral}")
        return df

    def merge_with_market_data(
        self,
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        sentiment_timestamp_col: str = "timestamp",
        market_timestamp_col: str = "timestamp",
        tolerance_hours: int = 1,
    ) -> pd.DataFrame:
        """
        Merge sentiment data with market OHLCV data

        Args:
            sentiment_df: DataFrame with sentiment scores
            market_df: DataFrame with OHLCV data
            sentiment_timestamp_col: Timestamp column in sentiment_df
            market_timestamp_col: Timestamp column in market_df
            tolerance_hours: Maximum time difference for merge

        Returns:
            Merged DataFrame
        """
        if sentiment_df.empty or market_df.empty:
            logger.warning("One or both DataFrames are empty")
            return pd.DataFrame()

        # Ensure timestamps are datetime
        sentiment_df = sentiment_df.copy()
        market_df = market_df.copy()

        sentiment_df[sentiment_timestamp_col] = pd.to_datetime(sentiment_df[sentiment_timestamp_col])
        market_df[market_timestamp_col] = pd.to_datetime(market_df[market_timestamp_col])

        # Sort both dataframes
        sentiment_df = sentiment_df.sort_values(sentiment_timestamp_col)
        market_df = market_df.sort_values(market_timestamp_col)

        # Merge using backward direction to prevent look-ahead bias
        merged_df = pd.merge_asof(
            market_df,
            sentiment_df,
            left_on=market_timestamp_col,
            right_on=sentiment_timestamp_col,
            direction="backward",
            tolerance=pd.Timedelta(hours=tolerance_hours),
        )

        # Fill missing sentiment scores with neutral
        if "sentiment_score" in merged_df.columns:
            merged_df["sentiment_score"] = merged_df["sentiment_score"].fillna(0.0)

        # Remove rows where sentiment data is from the future (safety check)
        if sentiment_timestamp_col in merged_df.columns and market_timestamp_col in merged_df.columns:
            future_mask = merged_df[sentiment_timestamp_col] > merged_df[market_timestamp_col]
            if future_mask.any():
                logger.warning(f"Removing {future_mask.sum()} rows with future sentiment data")
                merged_df = merged_df[~future_mask]

        logger.info(f"Merged data: {len(merged_df)} rows")
        return merged_df

    def export_signals_csv(
        self, df: pd.DataFrame, filename: str = "sentiment_signals.csv", columns: Optional[List[str]] = None
    ) -> None:
        """
        Export processed signals to CSV

        Args:
            df: DataFrame with signals
            filename: Output filename
            columns: Specific columns to export (optional)
        """
        if df.empty:
            logger.warning("Cannot export empty DataFrame")
            return

        output_path = self.output_dir / filename

        if columns:
            df_to_save = df[columns].copy()
        else:
            df_to_save = df.copy()

        df_to_save.to_csv(output_path, index=False)
        logger.info(f"Exported signals to {output_path}")

    def generate_signal_summary(self, df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for signals

        Args:
            df: DataFrame with signals

        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {}

        summary = {
            "total_periods": len(df),
            "date_range": {
                "start": str(df["timestamp"].min()) if "timestamp" in df.columns else None,
                "end": str(df["timestamp"].max()) if "timestamp" in df.columns else None,
            },
        }

        if "sentiment_score" in df.columns:
            summary["sentiment_stats"] = {
                "mean": float(df["sentiment_score"].mean()),
                "median": float(df["sentiment_score"].median()),
                "std": float(df["sentiment_score"].std()),
                "min": float(df["sentiment_score"].min()),
                "max": float(df["sentiment_score"].max()),
                "positive_periods": int((df["sentiment_score"] > 0).sum()),
                "negative_periods": int((df["sentiment_score"] < 0).sum()),
                "neutral_periods": int((df["sentiment_score"] == 0).sum()),
            }

        if "signal" in df.columns:
            summary["signal_stats"] = {
                "buy_signals": int((df["signal"] == 1).sum()),
                "sell_signals": int((df["signal"] == -1).sum()),
                "neutral_signals": int((df["signal"] == 0).sum()),
            }

        return summary


if __name__ == "__main__":
    # Example usage
    processor = SignalProcessor()

    # Create sample sentiment data
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="1H")
    sample_sentiment_df = pd.DataFrame(
        {
            "timestamp": dates,
            "sentiment_score": np.random.uniform(-0.5, 0.5, len(dates)),
            "headline": ["Sample headline"] * len(dates),
        }
    )

    # Calculate rolling sentiment
    df_with_rolling = processor.calculate_rolling_sentiment(sample_sentiment_df, window_hours=24)
    print(f"Added rolling sentiment: {df_with_rolling.columns.tolist()}")

    # Create trading signals
    df_with_signals = processor.create_trading_signals(df_with_rolling, bullish_threshold=0.2)
    print("\nSignal distribution:")
    print(df_with_signals["signal"].value_counts())

    # Generate summary
    summary = processor.generate_signal_summary(df_with_signals)
    print("\nSignal summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
