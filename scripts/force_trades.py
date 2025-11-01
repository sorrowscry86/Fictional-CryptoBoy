#!/usr/bin/env python3
"""
Force trades by injecting bullish sentiment into Redis cache
"""
import os
import sys
import redis
from datetime import datetime
import json

def force_trades():
    """Inject bullish sentiment for trading pairs to trigger buy signals"""
    
    # Connect to Redis
    redis_host = os.getenv('REDIS_HOST', 'redis')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        print(f"✓ Connected to Redis at {redis_host}:{redis_port}")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        return False
    
    # Trading pairs from config
    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    # Inject bullish sentiment for each pair
    for pair in pairs:
        sentiment_data = {
            'score': 0.85,  # Strong bullish (>0.7 threshold)
            'timestamp': datetime.now().isoformat(),
            'headline': f'{pair} showing strong upward momentum - BUY SIGNAL',
            'source': 'force_trades_script'
        }
        
        key = f"sentiment:{pair}"
        try:
            redis_client.hset(key, mapping=sentiment_data)
            print(f"✓ Injected bullish sentiment for {pair}: score={sentiment_data['score']}")
        except Exception as e:
            print(f"✗ Failed to set sentiment for {pair}: {e}")
            return False
    
    print("\n" + "="*70)
    print("TRADES FORCED - WAITING FOR SIGNALS")
    print("="*70)
    print("Bullish sentiment injected for all pairs:")
    for pair in pairs:
        print(f"  • {pair}: 0.85 (bullish)")
    print("\nThe strategy should trigger BUY signals on the next candle.")
    print("Monitor window will show new trades appearing shortly...")
    print("="*70)
    
    return True

if __name__ == "__main__":
    success = force_trades()
    sys.exit(0 if success else 1)
