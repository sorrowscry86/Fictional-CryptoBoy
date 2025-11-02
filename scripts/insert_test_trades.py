"""
Insert test trades into the database for monitor demonstration
VoidCat RDC - CryptoBoy Testing
"""

import sqlite3
from datetime import datetime, timedelta


def insert_test_trades():
    """Insert realistic test trades into the database"""
    conn = sqlite3.connect("tradesv3.dryrun.sqlite")
    cursor = conn.cursor()

    # Test trades data
    base_time = datetime.now() - timedelta(hours=48)

    trades = [
        # Trade 1: BTC/USDT - Closed Win
        {
            "pair": "BTC/USDT",
            "is_open": 0,
            "open_date": (base_time + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "close_date": (base_time + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "open_rate": 67500.00,
            "close_rate": 68700.00,
            "amount": 0.000741,
            "stake_amount": 50.0,
            "close_profit": 1.78,
            "close_profit_abs": 0.89,
            "exit_reason": "roi",
            "strategy": "LLMSentimentStrategy",
            "timeframe": "1h",
        },
        # Trade 2: ETH/USDT - Closed Win
        {
            "pair": "ETH/USDT",
            "is_open": 0,
            "open_date": (base_time + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S"),
            "close_date": (base_time + timedelta(hours=16)).strftime("%Y-%m-%d %H:%M:%S"),
            "open_rate": 2650.00,
            "close_rate": 2730.00,
            "amount": 0.0189,
            "stake_amount": 50.0,
            "close_profit": 3.02,
            "close_profit_abs": 1.51,
            "exit_reason": "roi",
            "strategy": "LLMSentimentStrategy",
            "timeframe": "1h",
        },
        # Trade 3: SOL/USDT - Closed Loss
        {
            "pair": "SOL/USDT",
            "is_open": 0,
            "open_date": (base_time + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "close_date": (base_time + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
            "open_rate": 165.50,
            "close_rate": 162.00,
            "amount": 0.302,
            "stake_amount": 50.0,
            "close_profit": -2.11,
            "close_profit_abs": -1.06,
            "exit_reason": "stop_loss",
            "strategy": "LLMSentimentStrategy",
            "timeframe": "1h",
        },
        # Trade 4: BTC/USDT - Open Position
        {
            "pair": "BTC/USDT",
            "is_open": 1,
            "open_date": (base_time + timedelta(hours=35)).strftime("%Y-%m-%d %H:%M:%S"),
            "close_date": None,
            "open_rate": 68200.00,
            "close_rate": None,
            "amount": 0.000733,
            "stake_amount": 50.0,
            "stop_loss": 66154.00,
            "close_profit": None,
            "close_profit_abs": None,
            "exit_reason": None,
            "strategy": "LLMSentimentStrategy",
            "timeframe": "1h",
        },
        # Trade 5: ETH/USDT - Closed Win (recent)
        {
            "pair": "ETH/USDT",
            "is_open": 0,
            "open_date": (base_time + timedelta(hours=40)).strftime("%Y-%m-%d %H:%M:%S"),
            "close_date": (base_time + timedelta(hours=45)).strftime("%Y-%m-%d %H:%M:%S"),
            "open_rate": 2680.00,
            "close_rate": 2815.00,
            "amount": 0.0187,
            "stake_amount": 50.0,
            "close_profit": 5.04,
            "close_profit_abs": 2.52,
            "exit_reason": "roi",
            "strategy": "LLMSentimentStrategy",
            "timeframe": "1h",
        },
    ]

    for i, trade in enumerate(trades, start=1):
        # Build INSERT query with all required fields
        columns = [
            "id",
            "exchange",
            "pair",
            "is_open",
            "fee_open",
            "fee_close",
            "open_rate",
            "close_rate",
            "amount",
            "stake_amount",
            "open_date",
            "close_date",
            "stop_loss",
            "close_profit",
            "close_profit_abs",
            "exit_reason",
            "strategy",
            "timeframe",
            "base_currency",
            "stake_currency",
            "initial_stop_loss",
            "is_stop_loss_trailing",
            "open_rate_requested",
            "open_trade_value",
            "leverage",
            "is_short",
            "interest_rate",
            "funding_fees",
            "trading_mode",
            "amount_precision",
            "price_precision",
            "record_version",
        ]

        stop_loss_val = trade.get(
            "stop_loss", trade["open_rate"] * 0.97 if trade["is_open"] else trade["open_rate"] * 0.97
        )

        values = [
            i,  # id
            "coinbase",  # exchange
            trade["pair"],
            trade["is_open"],
            0.001,  # fee_open
            0.001,  # fee_close
            trade["open_rate"],
            trade["close_rate"],
            trade["amount"],
            trade["stake_amount"],
            trade["open_date"],
            trade["close_date"],
            stop_loss_val,  # stop_loss
            trade.get("close_profit"),
            trade.get("close_profit_abs"),
            trade.get("exit_reason"),
            trade["strategy"],
            trade["timeframe"],
            trade["pair"].split("/")[0],  # base_currency
            trade["pair"].split("/")[1],  # stake_currency
            stop_loss_val,  # initial_stop_loss
            1,  # is_stop_loss_trailing
            trade["open_rate"],  # open_rate_requested
            trade["stake_amount"],  # open_trade_value
            1.0,  # leverage
            0,  # is_short
            0.0,  # interest_rate
            0.0,  # funding_fees
            "spot",  # trading_mode
            8,  # amount_precision
            2,  # price_precision
            1,  # record_version
        ]

        placeholders = ",".join(["?" for _ in values])
        query = f"INSERT INTO trades ({','.join(columns)}) VALUES ({placeholders})"

        cursor.execute(query, values)
        print(f"✓ Inserted trade {i}: {trade['pair']} - {'OPEN' if trade['is_open'] else 'CLOSED'}")

    conn.commit()
    conn.close()

    print(f"\n✅ Successfully inserted {len(trades)} test trades!")
    print("   • 4 closed trades (3 wins, 1 loss)")
    print("   • 1 open position (BTC/USDT)")
    print(f"   • Total P/L: +{sum(t.get('close_profit_abs', 0) for t in trades if not t['is_open']):.2f} USDT")
    print("\n🚀 Run the monitor to see them:")
    print("   python scripts/monitor_trading.py --once")
    print("   OR: start_monitor.bat")


if __name__ == "__main__":
    print("Inserting test trades into database...\n")
    insert_test_trades()
