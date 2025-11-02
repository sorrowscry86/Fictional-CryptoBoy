"""
Unit Tests for Signal Processor
VoidCat RDC - CryptoBoy Trading Bot

Tests signal processing logic.
"""
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest


class TestSignalProcessor(unittest.TestCase):
    """Test SignalProcessor functionality"""

    def test_signal_processor_initialization(self):
        """Test that signal processor can be initialized"""
        from llm.signal_processor import SignalProcessor
        
        processor = SignalProcessor()
        assert processor is not None
        assert hasattr(processor, 'output_dir')

    def test_calculate_rolling_sentiment(self):
        """Test rolling sentiment calculation"""
        from llm.signal_processor import SignalProcessor
        
        # Create test data with correct column name
        test_data = {
            'timestamp': pd.date_range('2025-11-01', periods=10, freq='1h'),
            'sentiment_score': [0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.4, 0.5, 0.6]
        }
        df = pd.DataFrame(test_data)
        
        processor = SignalProcessor()
        result = processor.calculate_rolling_sentiment(df, window_hours=3)
        
        # Check that rolling calculation was performed
        assert 'rolling_sentiment' in result.columns
        assert len(result) == len(df)

    def test_aggregate_signals(self):
        """Test signal aggregation"""
        from llm.signal_processor import SignalProcessor
        
        # Create test data with correct column names (needs headline column)
        test_data = {
            'timestamp': pd.date_range('2025-11-01', periods=5, freq='1h'),
            'sentiment_score': [0.5, 0.6, 0.7, 0.8, 0.7],
            'headline': ['News 1', 'News 2', 'News 3', 'News 4', 'News 5']
        }
        df = pd.DataFrame(test_data)
        
        processor = SignalProcessor()
        result = processor.aggregate_signals(df, timeframe='1H', aggregation_method='mean')
        
        # Should aggregate and return result
        assert result is not None
        assert 'sentiment_score' in result.columns
        assert 'article_count' in result.columns

    def test_smooth_signal_noise(self):
        """Test signal noise smoothing"""
        from llm.signal_processor import SignalProcessor
        
        # Create test data with noise and correct column name
        test_data = {
            'timestamp': pd.date_range('2025-11-01', periods=10, freq='1h'),
            'sentiment_score': [0.5, 0.9, 0.1, 0.8, 0.2, 0.7, 0.3, 0.6, 0.4, 0.5]
        }
        df = pd.DataFrame(test_data)
        
        processor = SignalProcessor()
        result = processor.smooth_signal_noise(df, method='ema', window=3)
        
        # Smoothed signal should have less variation
        assert result is not None
        assert 'smoothed_sentiment' in result.columns

    def test_merge_with_market_data(self):
        """Test merging sentiment with market data"""
        from llm.signal_processor import SignalProcessor
        
        # Create sentiment data with correct column name
        sentiment_data = {
            'timestamp': pd.date_range('2025-11-01 00:00', periods=3, freq='1h'),
            'sentiment_score': [0.5, 0.7, 0.6]
        }
        sentiment_df = pd.DataFrame(sentiment_data)
        
        # Create market data
        market_data = {
            'timestamp': pd.date_range('2025-11-01 00:00', periods=5, freq='1h'),
            'close': [100, 101, 102, 103, 104]
        }
        market_df = pd.DataFrame(market_data)
        
        processor = SignalProcessor()
        result = processor.merge_with_market_data(market_df, sentiment_df)
        
        # Should merge successfully
        assert result is not None
        assert 'close' in result.columns
        assert len(result) > 0


class TestSignalProcessorWithData:
    """Tests requiring sample data files"""

    @pytest.mark.integration
    def test_process_historical_data(self):
        """Test processing historical data files"""
        pytest.skip("Integration test - requires historical data files")


if __name__ == '__main__':
    unittest.main()
