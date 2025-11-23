"""
Strategy State Monitor - Real-time entry condition visibility
Displays why trades are/aren't executing by showing all entry conditions
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from services.common.redis_client import RedisClient
from services.common.logging_config import setup_logging

logger = setup_logging("strategy-monitor")


class StrategyStateMonitor:
    """
    Monitors trading strategy state and entry conditions in real-time.

    Reads strategy state from Redis and provides formatted output showing:
    - Current sentiment score
    - Technical indicator values (EMA, RSI, MACD, volume, Bollinger Bands)
    - Which entry conditions are met/failing
    - Blocking reasons if trade cannot execute

    Used by dashboard to diagnose "why no trades?" questions.
    """

    # Entry thresholds (must match llm_sentiment_strategy.py)
    SENTIMENT_BUY_THRESHOLD = 0.7
    RSI_MIN = 30
    RSI_MAX = 70

    def __init__(self, redis_host: str = None, redis_port: int = None):
        """
        Initialize strategy state monitor.

        Args:
            redis_host: Redis server host (defaults to REDIS_HOST env var or 'redis')
            redis_port: Redis server port (defaults to REDIS_PORT env var or 6379)
        """
        self.redis = RedisClient(
            host=redis_host or os.getenv("REDIS_HOST", "redis"),
            port=redis_port or int(os.getenv("REDIS_PORT", 6379))
        )

        logger.info("StrategyStateMonitor initialized")

    def get_entry_conditions(self, pair: str) -> Dict[str, Any]:
        """
        Get current entry conditions for a trading pair.

        Reads strategy state from Redis and evaluates all 6 entry conditions:
        1. Sentiment score > 0.7 (strongly bullish)
        2. EMA(12) > EMA(26) - uptrend
        3. 30 < RSI < 70 - not overbought/oversold
        4. MACD > MACD Signal - bullish crossover
        5. Volume > Average Volume - liquidity
        6. Price < Upper Bollinger Band - not overextended

        Args:
            pair: Trading pair (e.g., "BTC/USDT")

        Returns:
            Dictionary with:
                - pair: Trading pair
                - conditions: List of condition dicts with name/value/threshold/met
                - can_enter: True if ALL conditions met
                - blocking_reasons: List of failed condition names
                - last_updated: Timestamp of state data
                - data_age_seconds: How old the state data is
        """
        # Fetch strategy state from Redis
        state = self.redis.hgetall(f"strategy_state:{pair}")

        if not state:
            logger.warning(f"No strategy state found for {pair} in Redis")
            return {
                "pair": pair,
                "error": "No strategy state data available",
                "conditions": [],
                "can_enter": False,
                "blocking_reasons": ["No data in Redis - bot may not be running"],
                "last_updated": None,
                "data_age_seconds": None,
            }

        # Parse state values
        sentiment_score = float(state.get("sentiment_score", 0.0))
        ema_12 = float(state.get("ema_12", 0.0))
        ema_26 = float(state.get("ema_26", 0.0))
        rsi = float(state.get("rsi", 50.0))
        macd = float(state.get("macd", 0.0))
        macd_signal = float(state.get("macd_signal", 0.0))
        volume = float(state.get("volume", 0.0))
        volume_avg = float(state.get("volume_avg", 0.0))
        price = float(state.get("price", 0.0))
        bb_upper = float(state.get("bb_upper", 0.0))
        last_updated_str = state.get("last_updated", "")

        # Calculate data age
        data_age_seconds = None
        if last_updated_str:
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                data_age_seconds = (datetime.utcnow() - last_updated).total_seconds()
            except ValueError:
                logger.warning(f"Invalid timestamp format: {last_updated_str}")

        # Evaluate all 6 entry conditions
        conditions = [
            {
                "name": "Sentiment Score",
                "value": sentiment_score,
                "threshold": f"> {self.SENTIMENT_BUY_THRESHOLD}",
                "met": sentiment_score > self.SENTIMENT_BUY_THRESHOLD,
                "description": "Strong bullish sentiment from news analysis",
            },
            {
                "name": "EMA Trend",
                "value": f"EMA12={ema_12:.2f}, EMA26={ema_26:.2f}",
                "threshold": "EMA12 > EMA26",
                "met": ema_12 > ema_26,
                "description": "Price in uptrend (short EMA above long EMA)",
            },
            {
                "name": "RSI Range",
                "value": rsi,
                "threshold": f"{self.RSI_MIN} < RSI < {self.RSI_MAX}",
                "met": self.RSI_MIN < rsi < self.RSI_MAX,
                "description": "Not overbought or oversold",
            },
            {
                "name": "MACD Crossover",
                "value": f"MACD={macd:.4f}, Signal={macd_signal:.4f}",
                "threshold": "MACD > Signal",
                "met": macd > macd_signal,
                "description": "Bullish momentum (MACD above signal line)",
            },
            {
                "name": "Volume Confirmation",
                "value": f"Vol={volume:.0f}, Avg={volume_avg:.0f}",
                "threshold": "Volume > Average",
                "met": volume > volume_avg if volume_avg > 0 else False,
                "description": "Sufficient liquidity for trade execution",
            },
            {
                "name": "Bollinger Band Position",
                "value": f"Price={price:.2f}, BB Upper={bb_upper:.2f}",
                "threshold": "Price < BB Upper",
                "met": price < bb_upper if bb_upper > 0 else False,
                "description": "Price not overextended (below upper band)",
            },
        ]

        # Determine if can enter (ALL conditions must be True)
        can_enter = all(c["met"] for c in conditions)

        # Get blocking reasons (failed conditions)
        blocking_reasons = [c["name"] for c in conditions if not c["met"]]

        return {
            "pair": pair,
            "conditions": conditions,
            "can_enter": can_enter,
            "blocking_reasons": blocking_reasons,
            "last_updated": last_updated_str,
            "data_age_seconds": data_age_seconds,
        }

    def get_sentiment_status(self, pair: str) -> Dict[str, Any]:
        """
        Get current sentiment status for a trading pair.

        Args:
            pair: Trading pair (e.g., "BTC/USDT")

        Returns:
            Dictionary with sentiment data:
                - score: Sentiment score (-1.0 to +1.0)
                - label: Sentiment label (very_bullish, bullish, etc.)
                - headline: News headline that generated score
                - source: News source
                - timestamp: When sentiment was generated
                - age_seconds: How old the sentiment is
                - is_stale: True if > 4 hours old
        """
        sentiment_data = self.redis.hgetall(f"sentiment:{pair}")

        if not sentiment_data:
            logger.warning(f"No sentiment data found for {pair}")
            return {
                "pair": pair,
                "error": "No sentiment data available",
                "score": 0.0,
                "is_stale": True,
            }

        score = float(sentiment_data.get("score", 0.0))
        timestamp_str = sentiment_data.get("timestamp", "")
        headline = sentiment_data.get("headline", "N/A")
        source = sentiment_data.get("source", "N/A")

        # Calculate age
        age_seconds = None
        is_stale = True
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                age_seconds = (datetime.utcnow() - timestamp).total_seconds()
                is_stale = age_seconds > (4 * 3600)  # 4 hours staleness threshold
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}")

        # Classify sentiment
        if score >= 0.7:
            label = "very_bullish"
        elif score >= 0.3:
            label = "bullish"
        elif score <= -0.7:
            label = "very_bearish"
        elif score <= -0.3:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "pair": pair,
            "score": score,
            "label": label,
            "headline": headline,
            "source": source,
            "timestamp": timestamp_str,
            "age_seconds": age_seconds,
            "is_stale": is_stale,
        }

    def format_entry_conditions_text(self, pair: str) -> str:
        """
        Format entry conditions as human-readable text (for terminal display).

        Args:
            pair: Trading pair

        Returns:
            Formatted multi-line string showing all conditions with ✓/✗ markers
        """
        result = self.get_entry_conditions(pair)

        if "error" in result:
            return f"❌ {result['error']}"

        lines = [f"\n📊 Entry Conditions for {pair}"]
        lines.append("=" * 60)

        # Show data age
        if result.get("data_age_seconds"):
            age = result["data_age_seconds"]
            age_str = f"{int(age)}s ago" if age < 60 else f"{int(age/60)}m ago"
            lines.append(f"Last Updated: {result['last_updated']} ({age_str})")

        lines.append("")

        # Show each condition
        for i, cond in enumerate(result["conditions"], 1):
            marker = "✅" if cond["met"] else "❌"
            lines.append(f"{i}. {marker} {cond['name']}")
            lines.append(f"   Value: {cond['value']}")
            lines.append(f"   Required: {cond['threshold']}")
            lines.append(f"   {cond['description']}")
            lines.append("")

        # Show verdict
        lines.append("=" * 60)
        if result["can_enter"]:
            lines.append("✅ ALL CONDITIONS MET - Can enter trade!")
        else:
            lines.append(f"❌ Cannot enter - {len(result['blocking_reasons'])} conditions failing:")
            for reason in result["blocking_reasons"]:
                lines.append(f"   • {reason}")

        return "\n".join(lines)

    def get_all_pairs_status(self) -> List[Dict[str, Any]]:
        """
        Get entry condition status for all tracked trading pairs.

        Scans Redis for all pairs with strategy state data.

        Returns:
            List of status dictionaries (one per pair)
        """
        # Get all strategy state keys
        keys = self.redis.keys("strategy_state:*")

        if not keys:
            logger.warning("No strategy state keys found in Redis")
            return []

        # Extract pair names from keys
        pairs = [key.replace("strategy_state:", "") for key in keys]

        # Get status for each pair
        statuses = []
        for pair in pairs:
            status = self.get_entry_conditions(pair)
            statuses.append(status)

        return statuses

    def check_redis_health(self) -> Dict[str, Any]:
        """
        Check if Redis is reachable and contains strategy data.

        Returns:
            Dictionary with:
                - redis_connected: True if PING successful
                - strategy_state_keys: Count of strategy state keys
                - sentiment_keys: Count of sentiment keys
                - sample_pairs: List of pairs with data
        """
        try:
            # Test connection
            connected = self.redis.ping()

            # Count keys
            strategy_keys = self.redis.keys("strategy_state:*")
            sentiment_keys = self.redis.keys("sentiment:*")

            # Get sample pairs
            sample_pairs = [key.replace("strategy_state:", "") for key in strategy_keys[:5]]

            return {
                "redis_connected": connected,
                "strategy_state_keys": len(strategy_keys),
                "sentiment_keys": len(sentiment_keys),
                "sample_pairs": sample_pairs,
                "healthy": connected and len(strategy_keys) > 0,
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "redis_connected": False,
                "error": str(e),
                "healthy": False,
            }


def main() -> None:
    """Test function - print entry conditions for BTC/USDT"""
    monitor = StrategyStateMonitor()

    # Check Redis health
    print("\n🏥 Redis Health Check")
    print("=" * 60)
    health = monitor.check_redis_health()
    if health["healthy"]:
        print(f"✅ Redis connected")
        print(f"Strategy state keys: {health['strategy_state_keys']}")
        print(f"Sentiment keys: {health['sentiment_keys']}")
        print(f"Sample pairs: {', '.join(health['sample_pairs'])}")
    else:
        print(f"❌ Redis not healthy: {health.get('error', 'Unknown error')}")
        return

    # Show status for all pairs
    print("\n📈 All Pairs Status")
    print("=" * 60)
    statuses = monitor.get_all_pairs_status()

    for status in statuses:
        pair = status["pair"]
        can_enter = status["can_enter"]
        marker = "✅" if can_enter else "❌"
        blocking = len(status["blocking_reasons"])

        print(f"{marker} {pair}: ", end="")
        if can_enter:
            print("Ready to trade!")
        else:
            print(f"{blocking} conditions failing")

    # Show detailed view for first pair
    if statuses:
        first_pair = statuses[0]["pair"]
        print(monitor.format_entry_conditions_text(first_pair))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
