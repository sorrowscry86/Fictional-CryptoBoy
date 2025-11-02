"""
Real-Time Trading Performance Monitor
VoidCat RDC - CryptoBoy Trading Bot

Monitors paper trading performance with live updates
"""

import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import pandas as pd


# ANSI color codes with Windows support
class Colors:
    GREEN = "\033[92m"  # Profit, wins, positive values
    RED = "\033[91m"  # Loss, errors, negative values
    YELLOW = "\033[93m"  # Warnings, neutral, waiting states
    BLUE = "\033[94m"  # General info
    CYAN = "\033[96m"  # Headers, borders
    MAGENTA = "\033[95m"  # Important highlights
    WHITE = "\033[97m"  # Bright text
    BOLD = "\033[1m"  # Bold text
    UNDERLINE = "\033[4m"  # Underlined text
    END = "\033[0m"  # Reset

    # ASCII-safe indicators (Windows compatible)
    UP = "+"  # Bullish/Up
    DOWN = "-"  # Bearish/Down
    NEUTRAL = "="  # Sideways
    CHECK = "+"  # Success
    CROSS = "X"  # Failure
    STAR = "*"  # Important
    CLOCK = "@"  # Time-based
    CHART = "#"  # Statistics
    LOCK = "!"  # Security
    FIRE = "!"  # Hot/Active


def clear_screen():
    """Clear terminal screen and enable color support on Windows"""
    # Enable ANSI colors on Windows
    if os.name == "nt":
        os.system("")  # Enables ANSI escape codes in Windows 10+
    os.system("cls" if os.name == "nt" else "clear")


def get_db_connection(db_path: str = "tradesv3.dryrun.sqlite"):
    """Connect to the trading database"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"{Colors.RED}Error connecting to database: {e}{Colors.END}")
        return None


def get_open_trades(conn):
    """Get all currently open trades"""
    query = """
    SELECT
        id,
        pair,
        is_open,
        open_date,
        open_rate,
        amount,
        stake_amount,
        stop_loss,
        exit_reason,
        close_date,
        close_rate,
        close_profit
    FROM trades
    WHERE is_open = 1
    ORDER BY open_date DESC
    """
    return pd.read_sql_query(query, conn)


def get_closed_trades(conn, limit=10):
    """Get recent closed trades"""
    query = f"""
    SELECT
        id,
        pair,
        open_date,
        close_date,
        open_rate,
        close_rate,
        amount,
        stake_amount,
        close_profit,
        close_profit_abs,
        exit_reason,
        (julianday(close_date) - julianday(open_date)) * 24 as duration_hours
    FROM trades
    WHERE is_open = 0
    ORDER BY close_date DESC
    LIMIT {limit}
    """
    return pd.read_sql_query(query, conn)


def get_trade_stats(conn):
    """Calculate trading statistics"""
    query = """
    SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN close_profit > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN close_profit < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(CASE WHEN close_profit = 0 THEN 1 ELSE 0 END) as breakeven_trades,
        AVG(close_profit) as avg_profit_pct,
        SUM(close_profit_abs) as total_profit_abs,
        MAX(close_profit) as best_trade_pct,
        MIN(close_profit) as worst_trade_pct,
        AVG((julianday(close_date) - julianday(open_date)) * 24) as avg_duration_hours
    FROM trades
    WHERE is_open = 0
    """
    result = pd.read_sql_query(query, conn)
    return result.iloc[0] if len(result) > 0 else None


def get_pair_performance(conn):
    """Get performance by trading pair"""
    query = """
    SELECT
        pair,
        COUNT(*) as trades,
        SUM(CASE WHEN close_profit > 0 THEN 1 ELSE 0 END) as wins,
        SUM(close_profit_abs) as profit_abs,
        AVG(close_profit) as avg_profit_pct
    FROM trades
    WHERE is_open = 0
    GROUP BY pair
    ORDER BY profit_abs DESC
    """
    return pd.read_sql_query(query, conn)


def get_balance_info(conn, initial_balance: float = 1000.0):
    """Calculate current balance and P/L"""
    # Get total realized profit from closed trades
    query_closed = """
    SELECT COALESCE(SUM(close_profit_abs), 0) as realized_profit
    FROM trades
    WHERE is_open = 0
    """
    result = pd.read_sql_query(query_closed, conn)
    realized_profit = result["realized_profit"].iloc[0]

    # Get unrealized profit from open trades (mark-to-market)
    query_open = """
    SELECT COALESCE(SUM(stake_amount), 0) as total_stake
    FROM trades
    WHERE is_open = 1
    """
    open_result = pd.read_sql_query(query_open, conn)
    locked_capital = open_result["total_stake"].iloc[0]

    current_balance = initial_balance + realized_profit
    available_balance = current_balance - locked_capital
    total_gain_loss = realized_profit
    gain_loss_pct = (total_gain_loss / initial_balance) * 100 if initial_balance > 0 else 0

    return {
        "initial": initial_balance,
        "current": current_balance,
        "available": available_balance,
        "locked": locked_capital,
        "realized_pl": realized_profit,
        "total_pl": total_gain_loss,
        "pl_pct": gain_loss_pct,
    }


def get_recent_headlines(csv_path: str = "data/sentiment_signals.csv", limit: int = 10):
    """Get recent headlines from sentiment signals"""
    try:
        df = pd.read_csv(csv_path)
        # Get unique headlines (deduplicate by article_id)
        df_unique = df.drop_duplicates(subset=["article_id"]).sort_values("timestamp", ascending=False)
        headlines = []
        for _, row in df_unique.head(limit).iterrows():
            sentiment_emoji = (
                Colors.UP
                if row["sentiment_label"] == "BULLISH"
                else Colors.DOWN if row["sentiment_label"] == "BEARISH" else Colors.NEUTRAL
            )
            headlines.append(
                {
                    "headline": row["headline"],
                    "sentiment": row["sentiment_label"],
                    "emoji": sentiment_emoji,
                    "score": row["sentiment_score"],
                }
            )
        return headlines
    except Exception:
        return []


def get_recent_activity(conn, minutes: int = 60):
    """Get recent trade activity (entries and exits)"""
    cutoff_time = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")

    activities = []

    # Get recent entries (open trades)
    query_entries = f"""
    SELECT
        'ENTRY' as activity_type,
        pair,
        open_date as activity_time,
        open_rate as rate,
        stake_amount,
        id
    FROM trades
    WHERE open_date >= '{cutoff_time}'
    ORDER BY open_date DESC
    """

    # Get recent exits (closed trades)
    query_exits = f"""
    SELECT
        'EXIT' as activity_type,
        pair,
        close_date as activity_time,
        close_rate as rate,
        close_profit,
        close_profit_abs,
        exit_reason,
        id
    FROM trades
    WHERE close_date >= '{cutoff_time}' AND is_open = 0
    ORDER BY close_date DESC
    """

    try:
        entries = pd.read_sql_query(query_entries, conn)
        exits = pd.read_sql_query(query_exits, conn)

        for _, entry in entries.iterrows():
            activities.append(
                {
                    "type": "ENTRY",
                    "pair": entry["pair"],
                    "time": pd.to_datetime(entry["activity_time"]),
                    "rate": entry["rate"],
                    "stake": entry["stake_amount"],
                    "id": entry["id"],
                }
            )

        for _, exit in exits.iterrows():
            activities.append(
                {
                    "type": "EXIT",
                    "pair": exit["pair"],
                    "time": pd.to_datetime(exit["activity_time"]),
                    "rate": exit["rate"],
                    "profit": exit["close_profit"],
                    "profit_abs": exit["close_profit_abs"],
                    "reason": exit["exit_reason"],
                    "id": exit["id"],
                }
            )

        # Sort by time (most recent first)
        activities.sort(key=lambda x: x["time"], reverse=True)
        return activities[:10]  # Return last 10 activities

    except Exception:
        return []


def format_duration(hours):
    """Format duration in hours to readable string"""
    if pd.isna(hours):
        return "N/A"

    if hours < 1:
        return f"{int(hours * 60)}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        days = hours / 24
        return f"{days:.1f}d"


def display_dashboard(db_path: str = "tradesv3.dryrun.sqlite"):
    """Display the trading dashboard"""
    conn = get_db_connection(db_path)
    if not conn:
        return False

    try:
        clear_screen()

        # Get balance info
        balance = get_balance_info(conn, initial_balance=1000.0)

        # Header with Balance
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}  [*] CRYPTOBOY TRADING MONITOR - VOIDCAT RDC{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.YELLOW}{Colors.BOLD}  [LOCK] Paper Trading Mode (DRY_RUN){Colors.END}")
        print(f"{Colors.BLUE}  [TIME] Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")

        # Balance Display
        pl_color = Colors.GREEN if balance["total_pl"] > 0 else Colors.RED if balance["total_pl"] < 0 else Colors.YELLOW
        pl_indicator = (
            Colors.UP if balance["total_pl"] > 0 else Colors.DOWN if balance["total_pl"] < 0 else Colors.NEUTRAL
        )

        print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
        print(
            f"{Colors.BOLD}{Colors.WHITE}  [BALANCE]{Colors.END} | "
            f"Starting: {Colors.BLUE}{balance['initial']:.2f} USDT{Colors.END} | "
            f"Current: {Colors.WHITE}{Colors.BOLD}{balance['current']:.2f} USDT{Colors.END} | "
            f"P/L: {pl_color}{Colors.BOLD}{pl_indicator} {balance['total_pl']:+.2f} USDT ({balance['pl_pct']:+.2f}%){Colors.END}"
        )
        print(
            f"  Available: {Colors.GREEN}{balance['available']:.2f} USDT{Colors.END} | "
            f"Locked in Trades: {Colors.YELLOW}{balance['locked']:.2f} USDT{Colors.END}"
        )
        print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")

        # Trading Statistics
        stats = get_trade_stats(conn)

        if stats is not None and stats["total_trades"] > 0:
            win_rate = (stats["winning_trades"] / stats["total_trades"]) * 100

            print(f"{Colors.BOLD}{Colors.WHITE}  [STATS] OVERALL STATISTICS{Colors.END}")
            print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
            print(f"  Total Trades:      {Colors.WHITE}{Colors.BOLD}{int(stats['total_trades'])}{Colors.END}")
            print(
                f"  Winning Trades:    {Colors.GREEN}{Colors.BOLD}{Colors.UP} {int(stats['winning_trades'])}{Colors.END}"
            )
            print(
                f"  Losing Trades:     {Colors.RED}{Colors.BOLD}{Colors.DOWN} {int(stats['losing_trades'])}{Colors.END}"
            )
            print(f"  Breakeven:         {Colors.YELLOW}{Colors.NEUTRAL} {int(stats['breakeven_trades'])}{Colors.END}")

            # Win rate with color and indicator
            if win_rate >= 60:
                win_rate_color = Colors.GREEN
                win_indicator = f"{Colors.STAR}{Colors.STAR}"
            elif win_rate >= 50:
                win_rate_color = Colors.GREEN
                win_indicator = Colors.STAR
            elif win_rate >= 40:
                win_rate_color = Colors.YELLOW
                win_indicator = Colors.NEUTRAL
            else:
                win_rate_color = Colors.RED
                win_indicator = Colors.DOWN

            print(f"  Win Rate:          {win_rate_color}{Colors.BOLD}{win_indicator} {win_rate:.2f}%{Colors.END}")

            # Total profit with color and indicator
            if stats["total_profit_abs"] > 50:
                profit_color = Colors.GREEN
                profit_indicator = f"{Colors.FIRE}{Colors.UP}"
            elif stats["total_profit_abs"] > 0:
                profit_color = Colors.GREEN
                profit_indicator = Colors.UP
            elif stats["total_profit_abs"] == 0:
                profit_color = Colors.YELLOW
                profit_indicator = Colors.NEUTRAL
            else:
                profit_color = Colors.RED
                profit_indicator = Colors.DOWN

            print(
                f"  Total Profit:      {profit_color}{Colors.BOLD}{profit_indicator} {stats['total_profit_abs']:+.2f} USDT{Colors.END}"
            )
            print(f"  Avg Profit:        {Colors.BLUE}{stats['avg_profit_pct']:.2f}%{Colors.END}")
            print(
                f"  Best Trade:        {Colors.GREEN}{Colors.BOLD}{Colors.UP} +{stats['best_trade_pct']:.2f}%{Colors.END}"
            )
            print(
                f"  Worst Trade:       {Colors.RED}{Colors.BOLD}{Colors.DOWN} {stats['worst_trade_pct']:.2f}%{Colors.END}"
            )
            print(f"  Avg Duration:      {Colors.BLUE}{format_duration(stats['avg_duration_hours'])}{Colors.END}")
            print()
        else:
            print(f"{Colors.BOLD}{Colors.WHITE}  [STATS] OVERALL STATISTICS{Colors.END}")
            print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
            print(f"  {Colors.YELLOW}[WAIT] No trades executed yet. Waiting for entry signals...{Colors.END}\n")

        # Pair Performance
        pair_perf = get_pair_performance(conn)
        if not pair_perf.empty:
            print(f"{Colors.BOLD}{Colors.WHITE}  [CHART] PERFORMANCE BY PAIR{Colors.END}")
            print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
            for _, row in pair_perf.iterrows():
                win_rate = (row["wins"] / row["trades"]) * 100 if row["trades"] > 0 else 0

                # Color code by profitability
                if row["profit_abs"] > 10:
                    profit_color = Colors.GREEN
                    profit_indicator = f"{Colors.FIRE}{Colors.UP}"
                elif row["profit_abs"] > 0:
                    profit_color = Colors.GREEN
                    profit_indicator = Colors.UP
                elif row["profit_abs"] == 0:
                    profit_color = Colors.YELLOW
                    profit_indicator = Colors.NEUTRAL
                else:
                    profit_color = Colors.RED
                    profit_indicator = Colors.DOWN

                # Color code win rate
                if win_rate >= 60:
                    wr_color = Colors.GREEN
                elif win_rate >= 50:
                    wr_color = Colors.YELLOW
                else:
                    wr_color = Colors.RED

                print(
                    f"  {Colors.BOLD}{row['pair']:12}{Colors.END} | "
                    f"Trades: {Colors.WHITE}{int(row['trades']):3}{Colors.END} | "
                    f"Win Rate: {wr_color}{win_rate:5.1f}%{Colors.END} | "
                    f"P/L: {profit_color}{Colors.BOLD}{profit_indicator} {row['profit_abs']:+8.2f} USDT{Colors.END}"
                )
            print()

        # Open Trades
        open_trades = get_open_trades(conn)
        print(f"{Colors.BOLD}{Colors.WHITE}  [OPEN] OPEN TRADES ({len(open_trades)}){Colors.END}")
        print(f"{Colors.CYAN}{'-'*80}{Colors.END}")

        if not open_trades.empty:
            for _, trade in open_trades.iterrows():
                open_date = pd.to_datetime(trade["open_date"])
                duration = datetime.now() - open_date
                hours = duration.total_seconds() / 3600

                # Color code by duration (warning if too long)
                if hours > 24:
                    duration_color = Colors.YELLOW
                elif hours > 48:
                    duration_color = Colors.RED
                else:
                    duration_color = Colors.BLUE

                print(
                    f"  {Colors.MAGENTA}ID {trade['id']:3}{Colors.END} | "
                    f"{Colors.BOLD}{trade['pair']:12}{Colors.END} | "
                    f"Entry: {Colors.WHITE}${trade['open_rate']:.2f}{Colors.END} | "
                    f"Amount: {Colors.BLUE}{trade['amount']:.4f}{Colors.END} | "
                    f"Stake: {Colors.YELLOW}{trade['stake_amount']:.2f} USDT{Colors.END} | "
                    f"Duration: {duration_color}{format_duration(hours)}{Colors.END}"
                )
        else:
            print(f"  {Colors.YELLOW}{Colors.NEUTRAL} No open positions{Colors.END}")
        print()

        # Recent Closed Trades
        closed_trades = get_closed_trades(conn, limit=5)
        print(f"{Colors.BOLD}{Colors.WHITE}  [HISTORY] RECENT CLOSED TRADES (Last 5){Colors.END}")
        print(f"{Colors.CYAN}{'-'*80}{Colors.END}")

        if not closed_trades.empty:
            for _, trade in closed_trades.iterrows():
                # Color code by profit
                if trade["close_profit"] > 2:
                    profit_color = Colors.GREEN
                    profit_indicator = f"{Colors.STAR}{Colors.UP}"
                elif trade["close_profit"] > 0:
                    profit_color = Colors.GREEN
                    profit_indicator = Colors.UP
                elif trade["close_profit"] == 0:
                    profit_color = Colors.YELLOW
                    profit_indicator = Colors.NEUTRAL
                elif trade["close_profit"] < -2:
                    profit_color = Colors.RED
                    profit_indicator = f"{Colors.CROSS}{Colors.DOWN}"
                else:
                    profit_color = Colors.RED
                    profit_indicator = Colors.DOWN

                close_date = pd.to_datetime(trade["close_date"]).strftime("%m-%d %H:%M")

                # Color code exit reason
                exit_color = (
                    Colors.GREEN
                    if "roi" in str(trade["exit_reason"]).lower()
                    else Colors.RED if "stop" in str(trade["exit_reason"]).lower() else Colors.BLUE
                )

                print(
                    f"  {Colors.BLUE}{close_date}{Colors.END} | "
                    f"{Colors.BOLD}{trade['pair']:12}{Colors.END} | "
                    f"{profit_color}{Colors.BOLD}{profit_indicator} {trade['close_profit']:+6.2f}%{Colors.END} "
                    f"({profit_color}{trade['close_profit_abs']:+7.2f} USDT{Colors.END}) | "
                    f"Duration: {Colors.BLUE}{format_duration(trade['duration_hours'])}{Colors.END} | "
                    f"Exit: {exit_color}{trade['exit_reason']}{Colors.END}"
                )
        else:
            print(f"  {Colors.YELLOW}{Colors.NEUTRAL} No closed trades yet{Colors.END}")
        print()

        # Recent Activity / Trade Notifications
        activities = get_recent_activity(conn, minutes=120)  # Last 2 hours
        if activities:
            print(f"{Colors.BOLD}{Colors.WHITE}  [ACTIVITY] RECENT TRADE UPDATES (Last 2 Hours){Colors.END}")
            print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
            for activity in activities:
                time_str = activity["time"].strftime("%H:%M:%S")

                if activity["type"] == "ENTRY":
                    print(
                        f"  {Colors.GREEN}[{time_str}]{Colors.END} {Colors.BOLD}ENTERED{Colors.END} "
                        f"{Colors.WHITE}{activity['pair']:12}{Colors.END} | "
                        f"Rate: {Colors.BLUE}${activity['rate']:.2f}{Colors.END} | "
                        f"Stake: {Colors.YELLOW}{activity['stake']:.2f} USDT{Colors.END} | "
                        f"ID: {Colors.MAGENTA}{activity['id']}{Colors.END}"
                    )
                else:  # EXIT
                    profit_color = Colors.GREEN if activity["profit"] > 0 else Colors.RED
                    profit_indicator = Colors.UP if activity["profit"] > 0 else Colors.DOWN
                    reason_color = (
                        Colors.GREEN
                        if "roi" in activity["reason"].lower()
                        else Colors.RED if "stop" in activity["reason"].lower() else Colors.BLUE
                    )

                    print(
                        f"  {Colors.YELLOW}[{time_str}]{Colors.END} {Colors.BOLD}EXITED{Colors.END}  "
                        f"{Colors.WHITE}{activity['pair']:12}{Colors.END} | "
                        f"P/L: {profit_color}{Colors.BOLD}{profit_indicator} {activity['profit']:+.2f}%{Colors.END} "
                        f"({profit_color}{activity['profit_abs']:+.2f} USDT{Colors.END}) | "
                        f"Reason: {reason_color}{activity['reason']}{Colors.END}"
                    )
            print()

        # News Headlines Ticker
        headlines = get_recent_headlines(limit=5)
        if headlines:
            print(f"{Colors.BOLD}{Colors.WHITE}  [NEWS] RECENT SENTIMENT HEADLINES{Colors.END}")
            print(f"{Colors.CYAN}{'-'*80}{Colors.END}")
            for h in headlines:
                # Color code by sentiment
                if h["sentiment"] == "BULLISH":
                    sent_color = Colors.GREEN
                    sent_text = f"{Colors.UP} BULLISH"
                elif h["sentiment"] == "BEARISH":
                    sent_color = Colors.RED
                    sent_text = f"{Colors.DOWN} BEARISH"
                else:
                    sent_color = Colors.YELLOW
                    sent_text = f"{Colors.NEUTRAL} NEUTRAL"

                # Truncate headline if too long
                headline_text = h["headline"][:65] + "..." if len(h["headline"]) > 65 else h["headline"]
                print(
                    f"  {sent_color}{Colors.BOLD}{sent_text}{Colors.END} | "
                    f"{Colors.WHITE}{headline_text}{Colors.END}"
                )
            print()

        # Footer
        print(f"{Colors.CYAN}{'='*80}{Colors.END}")
        print(
            f"{Colors.MAGENTA}  Press Ctrl+C to exit {Colors.END}| "
            f"{Colors.BLUE}Refreshing every 10 seconds...{Colors.END}"
        )
        print(f"{Colors.CYAN}{'='*80}{Colors.END}")

        conn.close()
        return True

    except Exception as e:
        print(f"{Colors.RED}Error displaying dashboard: {e}{Colors.END}")
        if conn:
            conn.close()
        return False


def monitor_live(db_path: str = "tradesv3.dryrun.sqlite", refresh_interval: int = 10):
    """
    Monitor trading in real-time with periodic updates

    Args:
        db_path: Path to SQLite database
        refresh_interval: Seconds between refreshes
    """
    print(f"{Colors.GREEN}Starting CryptoBoy Trading Monitor...{Colors.END}\n")
    time.sleep(1)

    try:
        while True:
            success = display_dashboard(db_path)
            if not success:
                print(f"{Colors.RED}Failed to connect to database. Retrying in {refresh_interval}s...{Colors.END}")

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Monitor stopped by user{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CryptoBoy Trading Monitor")
    parser.add_argument("--db", type=str, default="tradesv3.dryrun.sqlite", help="Path to trading database")
    parser.add_argument("--interval", type=int, default=10, help="Refresh interval in seconds")
    parser.add_argument("--once", action="store_true", help="Display once and exit (no live monitoring)")

    args = parser.parse_args()

    if args.once:
        display_dashboard(args.db)
    else:
        monitor_live(args.db, args.interval)
