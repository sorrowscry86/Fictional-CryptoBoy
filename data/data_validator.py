"""
Data Validation Module - Ensures data quality and prevents look-ahead bias
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates market and news data quality"""

    def __init__(self, output_dir: str = "data"):
        """
        Initialize the data validator

        Args:
            output_dir: Directory to save validation reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_ohlcv_integrity(self, df: pd.DataFrame) -> Dict:
        """
        Validate OHLCV data integrity

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        if df.empty:
            results['valid'] = False
            results['errors'].append("DataFrame is empty")
            return results

        # Check required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            results['valid'] = False
            results['errors'].append(f"Missing columns: {missing_cols}")
            return results

        # Check for null values
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            results['valid'] = False
            results['errors'].append(f"Null values found: {null_counts[null_counts > 0].to_dict()}")

        # Check timestamp ordering
        if not df['timestamp'].is_monotonic_increasing:
            results['valid'] = False
            results['errors'].append("Timestamps not in ascending order")

        # Check for duplicate timestamps
        duplicate_timestamps = df['timestamp'].duplicated().sum()
        if duplicate_timestamps > 0:
            results['warnings'].append(f"Found {duplicate_timestamps} duplicate timestamps")

        # Check price consistency
        invalid_high = (df['high'] < df['low']).sum()
        if invalid_high > 0:
            results['valid'] = False
            results['errors'].append(f"High < Low in {invalid_high} rows")

        invalid_range = (
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        ).sum()
        if invalid_range > 0:
            results['valid'] = False
            results['errors'].append(f"Invalid price ranges in {invalid_range} rows")

        # Check for negative values
        negative_prices = (df[['open', 'high', 'low', 'close']] < 0).any().any()
        if negative_prices:
            results['valid'] = False
            results['errors'].append("Negative prices found")

        negative_volume = (df['volume'] < 0).any()
        if negative_volume:
            results['valid'] = False
            results['errors'].append("Negative volume found")

        # Detect outliers using IQR method
        for col in ['open', 'high', 'low', 'close']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < (Q1 - 3 * IQR)) | (df[col] > (Q3 + 3 * IQR))).sum()
            if outliers > 0:
                results['warnings'].append(f"Found {outliers} potential outliers in {col}")

        # Calculate statistics
        results['stats'] = {
            'total_rows': len(df),
            'date_range': {
                'start': str(df['timestamp'].min()),
                'end': str(df['timestamp'].max())
            },
            'missing_values': null_counts.to_dict(),
            'price_stats': {
                'mean_close': float(df['close'].mean()),
                'std_close': float(df['close'].std()),
                'min_close': float(df['close'].min()),
                'max_close': float(df['close'].max())
            },
            'volume_stats': {
                'mean': float(df['volume'].mean()),
                'median': float(df['volume'].median())
            }
        }

        return results

    def check_timestamp_alignment(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        timestamp_col1: str = 'timestamp',
        timestamp_col2: str = 'timestamp',
        tolerance_minutes: int = 60
    ) -> Dict:
        """
        Check timestamp alignment between two datasets

        Args:
            df1: First DataFrame
            df2: Second DataFrame
            timestamp_col1: Timestamp column in df1
            timestamp_col2: Timestamp column in df2
            tolerance_minutes: Acceptable time difference in minutes

        Returns:
            Dictionary with alignment results
        """
        results = {
            'aligned': True,
            'warnings': [],
            'stats': {}
        }

        if df1.empty or df2.empty:
            results['aligned'] = False
            results['warnings'].append("One or both DataFrames are empty")
            return results

        # Ensure timestamps are datetime
        df1[timestamp_col1] = pd.to_datetime(df1[timestamp_col1])
        df2[timestamp_col2] = pd.to_datetime(df2[timestamp_col2])

        # Check overlap
        df1_start = df1[timestamp_col1].min()
        df1_end = df1[timestamp_col1].max()
        df2_start = df2[timestamp_col2].min()
        df2_end = df2[timestamp_col2].max()

        overlap_start = max(df1_start, df2_start)
        overlap_end = min(df1_end, df2_end)

        if overlap_start >= overlap_end:
            results['aligned'] = False
            results['warnings'].append("No temporal overlap between datasets")
            return results

        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
        results['stats']['overlap_hours'] = overlap_hours

        # Check for gaps
        df1_gaps = df1[timestamp_col1].diff().dt.total_seconds() / 60
        df2_gaps = df2[timestamp_col2].diff().dt.total_seconds() / 60

        large_gaps_df1 = (df1_gaps > tolerance_minutes).sum()
        large_gaps_df2 = (df2_gaps > tolerance_minutes).sum()

        if large_gaps_df1 > 0:
            results['warnings'].append(f"Found {large_gaps_df1} large gaps in df1")
        if large_gaps_df2 > 0:
            results['warnings'].append(f"Found {large_gaps_df2} large gaps in df2")

        results['stats']['df1_range'] = {'start': str(df1_start), 'end': str(df1_end)}
        results['stats']['df2_range'] = {'start': str(df2_start), 'end': str(df2_end)}
        results['stats']['overlap_range'] = {'start': str(overlap_start), 'end': str(overlap_end)}

        return results

    def detect_look_ahead_bias(
        self,
        market_df: pd.DataFrame,
        sentiment_df: pd.DataFrame,
        market_timestamp_col: str = 'timestamp',
        sentiment_timestamp_col: str = 'timestamp'
    ) -> Dict:
        """
        Detect potential look-ahead bias in merged datasets

        Args:
            market_df: Market data DataFrame
            sentiment_df: Sentiment data DataFrame
            market_timestamp_col: Timestamp column in market_df
            sentiment_timestamp_col: Timestamp column in sentiment_df

        Returns:
            Dictionary with bias detection results
        """
        results = {
            'has_bias': False,
            'warnings': [],
            'safe_to_use': True
        }

        if market_df.empty or sentiment_df.empty:
            results['warnings'].append("One or both DataFrames are empty")
            return results

        # Ensure timestamps are datetime
        market_df[market_timestamp_col] = pd.to_datetime(market_df[market_timestamp_col])
        sentiment_df[sentiment_timestamp_col] = pd.to_datetime(sentiment_df[sentiment_timestamp_col])

        # Merge on nearest timestamp
        merged = pd.merge_asof(
            market_df.sort_values(market_timestamp_col),
            sentiment_df.sort_values(sentiment_timestamp_col),
            left_on=market_timestamp_col,
            right_on=sentiment_timestamp_col,
            direction='backward',  # Only use past sentiment data
            tolerance=pd.Timedelta(hours=6)  # Max 6 hours lookback
        )

        # Check if sentiment data is from the future
        if f"{sentiment_timestamp_col}_right" in merged.columns:
            time_diff = merged[market_timestamp_col] - merged[f"{sentiment_timestamp_col}_right"]
            future_lookups = (time_diff < pd.Timedelta(0)).sum()

            if future_lookups > 0:
                results['has_bias'] = True
                results['safe_to_use'] = False
                results['warnings'].append(
                    f"CRITICAL: Found {future_lookups} instances of future data leakage"
                )

        # Check for same-candle leakage (sentiment published after market close)
        # This is a subtle form of look-ahead bias
        if 'published' in sentiment_df.columns and 'close_time' in market_df.columns:
            same_candle_issues = (
                merged['published'] > merged['close_time']
            ).sum() if 'published' in merged.columns and 'close_time' in merged.columns else 0

            if same_candle_issues > 0:
                results['warnings'].append(
                    f"Warning: {same_candle_issues} instances where sentiment is from same candle period"
                )

        logger.info(f"Look-ahead bias check: {results}")
        return results

    def generate_quality_report(
        self,
        market_df: pd.DataFrame,
        sentiment_df: Optional[pd.DataFrame] = None,
        output_file: str = 'data_quality_report.txt'
    ) -> str:
        """
        Generate comprehensive data quality report

        Args:
            market_df: Market data DataFrame
            sentiment_df: Sentiment data DataFrame (optional)
            output_file: Output filename

        Returns:
            Report text
        """
        report_lines = [
            "=" * 80,
            "DATA QUALITY REPORT",
            "=" * 80,
            f"Generated at: {datetime.now()}",
            "",
            "MARKET DATA VALIDATION",
            "-" * 80
        ]

        # Validate market data
        market_results = self.validate_ohlcv_integrity(market_df)
        report_lines.append(f"Valid: {market_results['valid']}")
        report_lines.append(f"Total rows: {market_results['stats'].get('total_rows', 0)}")

        if market_results['errors']:
            report_lines.append("\nERRORS:")
            for error in market_results['errors']:
                report_lines.append(f"  - {error}")

        if market_results['warnings']:
            report_lines.append("\nWARNINGS:")
            for warning in market_results['warnings']:
                report_lines.append(f"  - {warning}")

        report_lines.append("\nSTATISTICS:")
        for key, value in market_results['stats'].items():
            report_lines.append(f"  {key}: {value}")

        # Validate sentiment data if provided
        if sentiment_df is not None and not sentiment_df.empty:
            report_lines.extend([
                "",
                "SENTIMENT DATA VALIDATION",
                "-" * 80
            ])

            report_lines.append(f"Total records: {len(sentiment_df)}")

            if 'timestamp' in sentiment_df.columns:
                sent_start = sentiment_df['timestamp'].min()
                sent_end = sentiment_df['timestamp'].max()
                report_lines.append(f"Date range: {sent_start} to {sent_end}")

            # Check for look-ahead bias
            bias_results = self.detect_look_ahead_bias(market_df, sentiment_df)
            report_lines.append(f"\nLook-ahead bias detected: {bias_results['has_bias']}")
            report_lines.append(f"Safe to use: {bias_results['safe_to_use']}")

            if bias_results['warnings']:
                report_lines.append("\nWARNINGS:")
                for warning in bias_results['warnings']:
                    report_lines.append(f"  - {warning}")

        report_lines.append("\n" + "=" * 80)

        report_text = "\n".join(report_lines)

        # Save report
        report_path = self.output_dir / output_file
        with open(report_path, 'w') as f:
            f.write(report_text)

        logger.info(f"Quality report saved to {report_path}")
        return report_text


if __name__ == "__main__":
    # Example usage
    validator = DataValidator()

    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1H')
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(40000, 50000, len(dates)),
        'high': np.random.uniform(40000, 50000, len(dates)),
        'low': np.random.uniform(40000, 50000, len(dates)),
        'close': np.random.uniform(40000, 50000, len(dates)),
        'volume': np.random.uniform(100, 1000, len(dates))
    })

    # Validate
    results = validator.validate_ohlcv_integrity(sample_df)
    print(f"Validation results: {results['valid']}")
    print(f"Errors: {results['errors']}")
    print(f"Warnings: {results['warnings']}")

    # Generate report
    report = validator.generate_quality_report(sample_df)
    print("\n" + report)
