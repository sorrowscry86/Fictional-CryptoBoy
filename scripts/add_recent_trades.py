"""
Add recent trades for activity feed demonstration
"""

import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("tradesv3.dryrun.sqlite")
cursor = conn.cursor()

# Add a very recent trade (30 minutes ago)
recent_time = datetime.now() - timedelta(minutes=30)
recent_exit = datetime.now() - timedelta(minutes=15)

# Recent SOL/USDT entry
cursor.execute(
    """
INSERT INTO trades (
    id, exchange, pair, is_open, fee_open, fee_close,
    open_rate, close_rate, amount, stake_amount,
    open_date, close_date, stop_loss, close_profit,
    close_profit_abs, exit_reason, strategy, timeframe,
    base_currency, stake_currency, initial_stop_loss,
    is_stop_loss_trailing, open_rate_requested, open_trade_value,
    leverage, is_short, interest_rate, funding_fees,
    trading_mode, amount_precision, price_precision, record_version
) VALUES (
    6, 'coinbase', 'SOL/USDT', 0, 0.001, 0.001,
    168.50, 172.80, 0.297, 50.0,
    ?, ?, 163.45, 2.55, 1.28, 'roi', 'LLMSentimentStrategy', '1h',
    'SOL', 'USDT', 163.45, 1, 168.50, 50.0,
    1.0, 0, 0.0, 0.0, 'spot', 8, 2, 1
)
""",
    (recent_time.strftime("%Y-%m-%d %H:%M:%S"), recent_exit.strftime("%Y-%m-%d %H:%M:%S")),
)

# Very recent BTC entry (10 minutes ago) - still open
very_recent = datetime.now() - timedelta(minutes=10)
cursor.execute(
    """
INSERT INTO trades (
    id, exchange, pair, is_open, fee_open, fee_close,
    open_rate, close_rate, amount, stake_amount,
    open_date, close_date, stop_loss, close_profit,
    close_profit_abs, exit_reason, strategy, timeframe,
    base_currency, stake_currency, initial_stop_loss,
    is_stop_loss_trailing, open_rate_requested, open_trade_value,
    leverage, is_short, interest_rate, funding_fees,
    trading_mode, amount_precision, price_precision, record_version
) VALUES (
    7, 'coinbase', 'ETH/USDT', 1, 0.001, 0.001,
    2720.00, NULL, 0.0184, 50.0,
    ?, NULL, 2638.40, NULL, NULL, NULL, 'LLMSentimentStrategy', '1h',
    'ETH', 'USDT', 2638.40, 1, 2720.00, 50.0,
    1.0, 0, 0.0, 0.0, 'spot', 8, 2, 1
)
""",
    (very_recent.strftime("%Y-%m-%d %H:%M:%S"),),
)

conn.commit()
conn.close()

print("✅ Added recent trades:")
print("   • SOL/USDT EXIT - 30 min ago (+2.55%, +1.28 USDT)")
print("   • ETH/USDT ENTRY - 10 min ago (OPEN)")
print("\n🚀 Run monitor to see activity feed!")
