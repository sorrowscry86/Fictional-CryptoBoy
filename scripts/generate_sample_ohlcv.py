"""
Generate sample OHLCV data for backtesting when live exchange data is unavailable
VoidCat RDC - CryptoBoy Trading Bot
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_ohlcv(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    timeframe_hours: int = 1,
    initial_price: float = None
) -> pd.DataFrame:
    """
    Generate realistic sample OHLCV data
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        start_date: Start datetime
        end_date: End datetime
        timeframe_hours: Hours per candle
        initial_price: Starting price (auto-set based on symbol if None)
        
    Returns:
        DataFrame with OHLCV data
    """
    # Set realistic initial prices
    if initial_price is None:
        price_map = {
            'BTC/USDT': 67000,
            'ETH/USDT': 2600,
            'SOL/USDT': 160
        }
        initial_price = price_map.get(symbol, 100)
    
    # Generate timestamps
    timestamps = []
    current = start_date
    while current <= end_date:
        timestamps.append(current)
        current += timedelta(hours=timeframe_hours)
    
    n_candles = len(timestamps)
    logger.info(f"Generating {n_candles} candles for {symbol}")
    
    # Generate price movement with realistic volatility
    np.random.seed(42)  # For reproducibility
    
    # Random walk with drift
    returns = np.random.normal(0.0002, 0.02, n_candles)  # ~2% hourly volatility
    prices = initial_price * np.cumprod(1 + returns)
    
    # Generate OHLCV
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Add intracandle variation
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[i-1] if i > 0 else close
        
        # Ensure high >= low
        if high < low:
            high, low = low, high
        
        # Ensure OHLC relationships make sense
        if open_price > high:
            high = open_price
        if open_price < low:
            low = open_price
        if close > high:
            high = close
        if close < low:
            low = close
        
        # Generate volume (with some correlation to price movement)
        volatility = abs(close - open_price) / open_price
        base_volume = 1000000
        volume = base_volume * (1 + volatility * 10) * np.random.uniform(0.5, 1.5)
        
        data.append({
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': round(volume, 2),
            'symbol': symbol
        })
    
    df = pd.DataFrame(data)
    logger.info(f"Generated data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df


def main():
    """Generate sample data for all trading pairs"""
    output_dir = Path("data/ohlcv_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    for pair in pairs:
        logger.info(f"\nGenerating sample data for {pair}...")
        
        df = generate_sample_ohlcv(
            symbol=pair,
            start_date=start_date,
            end_date=end_date,
            timeframe_hours=1
        )
        
        # Save to CSV
        filename = f"{pair.replace('/', '_')}_1h.csv"
        filepath = output_dir / filename
        df.to_csv(filepath, index=False)
        
        logger.info(f"✓ Saved {len(df)} candles to {filepath}")
    
    logger.info("\n" + "="*80)
    logger.info("Sample OHLCV data generation complete")
    logger.info("="*80)


if __name__ == "__main__":
    main()
