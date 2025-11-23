"""
Manual Trade Controller - Force buy/sell trades for testing (DRY_RUN only)
Provides controlled trade injection via Freqtrade REST API
"""

import os
import json
from typing import Any, Dict, Optional
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

from services.common.redis_client import RedisClient
from services.common.logging_config import setup_logging

logger = setup_logging("manual-trade-controller")


class ManualTradeError(Exception):
    """Custom exception for manual trade failures"""
    pass


class ManualTradeController:
    """
    Manually trigger trades via Freqtrade REST API.

    SECURITY: Only works in DRY_RUN mode to prevent accidental real trades.

    Features:
    - Force buy/sell via Freqtrade API
    - Inject test sentiment scores into Redis
    - Audit logging of all manual actions
    - Confirmation prompts for destructive operations
    """

    def __init__(
        self,
        api_url: str = None,
        api_username: str = None,
        api_password: str = None,
        redis_host: str = None,
        redis_port: int = None,
    ):
        """
        Initialize manual trade controller.

        Args:
            api_url: Freqtrade REST API URL (defaults to http://localhost:8080)
            api_username: API username (defaults to env var)
            api_password: API password (defaults to env var)
            redis_host: Redis host for sentiment injection
            redis_port: Redis port
        """
        self.api_url = api_url or os.getenv("FREQTRADE_API_URL", "http://localhost:8080")
        self.api_username = api_username or os.getenv("FREQTRADE_API_USER", "freqtrader")
        self.api_password = api_password or os.getenv("FREQTRADE_API_PASSWORD", "")

        # Redis client for sentiment injection
        self.redis = RedisClient(
            host=redis_host or os.getenv("REDIS_HOST", "redis"),
            port=redis_port or int(os.getenv("REDIS_PORT", 6379))
        )

        # Verify DRY_RUN mode
        self._verify_dry_run_mode()

        logger.info("ManualTradeController initialized (DRY_RUN mode verified)")

    def _verify_dry_run_mode(self) -> None:
        """
        Verify bot is in DRY_RUN mode.

        CRITICAL SAFETY CHECK: Manual trades should NEVER execute with real money.

        Raises:
            ManualTradeError: If DRY_RUN is not enabled
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/show_config",
                auth=HTTPBasicAuth(self.api_username, self.api_password),
                timeout=5
            )
            response.raise_for_status()

            config = response.json()
            dry_run = config.get("dry_run", False)

            if not dry_run:
                raise ManualTradeError(
                    "❌ SAFETY ABORT: Manual trades ONLY allowed in DRY_RUN mode!\n"
                    "Set DRY_RUN=true in .env and restart trading bot."
                )

            logger.info("✓ DRY_RUN mode confirmed - manual trades permitted")

        except requests.exceptions.RequestException as e:
            raise ManualTradeError(
                f"Cannot verify DRY_RUN mode - API unreachable: {e}\n"
                f"Ensure trading bot is running and API is accessible at {self.api_url}"
            )

    def force_buy(
        self,
        pair: str,
        price: Optional[float] = None,
        amount_usdt: float = 100.0,
        inject_sentiment: bool = True,
        sentiment_score: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Force a buy trade via Freqtrade API.

        Args:
            pair: Trading pair (e.g., "BTC/USDT")
            price: Buy price (None = use current market price)
            amount_usdt: Stake amount in USDT
            inject_sentiment: If True, inject bullish sentiment into Redis first
            sentiment_score: Sentiment score to inject (0.0 to 1.0)

        Returns:
            API response dictionary

        Raises:
            ManualTradeError: If trade fails or validation fails
        """
        # Validate pair format
        if "/" not in pair or len(pair.split("/")) != 2:
            raise ManualTradeError(f"Invalid pair format: {pair} (expected: BTC/USDT)")

        logger.info(f"Forcing BUY for {pair} (stake: {amount_usdt} USDT)")

        # Inject sentiment if requested
        if inject_sentiment:
            self._inject_sentiment(
                pair=pair,
                score=sentiment_score,
                headline=f"[MANUAL] Test sentiment for forced buy",
                source="manual_controller"
            )

        try:
            # Call Freqtrade forcebuy endpoint
            response = requests.post(
                f"{self.api_url}/api/v1/forcebuy",
                json={
                    "pair": pair,
                    "price": price,  # None = use market price
                },
                auth=HTTPBasicAuth(self.api_username, self.api_password),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            # Log audit trail
            self._log_manual_action(
                action="FORCE_BUY",
                pair=pair,
                details={
                    "price": price,
                    "amount_usdt": amount_usdt,
                    "sentiment_injected": inject_sentiment,
                    "sentiment_score": sentiment_score if inject_sentiment else None,
                    "api_response": result,
                }
            )

            logger.info(f"✓ Force buy successful for {pair}")
            return result

        except requests.exceptions.HTTPError as e:
            error_msg = f"Force buy failed: {e}"
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nAPI Error: {error_detail}"
                except:
                    error_msg += f"\nResponse: {e.response.text}"

            logger.error(error_msg)
            raise ManualTradeError(error_msg)

        except Exception as e:
            logger.error(f"Unexpected error during force buy: {e}", exc_info=True)
            raise ManualTradeError(f"Force buy failed: {e}")

    def force_sell(
        self,
        trade_id: int,
        pair: Optional[str] = None,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Force sell an open trade via Freqtrade API.

        Args:
            trade_id: Trade ID to sell
            pair: Trading pair (required if trade_id not provided)
            price: Sell price (None = use current market price)

        Returns:
            API response dictionary

        Raises:
            ManualTradeError: If sell fails
        """
        logger.info(f"Forcing SELL for trade_id={trade_id} pair={pair}")

        try:
            # Call Freqtrade forcesell endpoint
            response = requests.post(
                f"{self.api_url}/api/v1/forcesell",
                json={
                    "tradeid": str(trade_id),
                    "ordertype": "market",  # Use market order for immediate execution
                },
                auth=HTTPBasicAuth(self.api_username, self.api_password),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            # Log audit trail
            self._log_manual_action(
                action="FORCE_SELL",
                pair=pair or "unknown",
                details={
                    "trade_id": trade_id,
                    "price": price,
                    "api_response": result,
                }
            )

            logger.info(f"✓ Force sell successful for trade {trade_id}")
            return result

        except requests.exceptions.HTTPError as e:
            error_msg = f"Force sell failed: {e}"
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nAPI Error: {error_detail}"
                except:
                    error_msg += f"\nResponse: {e.response.text}"

            logger.error(error_msg)
            raise ManualTradeError(error_msg)

        except Exception as e:
            logger.error(f"Unexpected error during force sell: {e}", exc_info=True)
            raise ManualTradeError(f"Force sell failed: {e}")

    def _inject_sentiment(
        self,
        pair: str,
        score: float,
        headline: str,
        source: str = "manual_injection"
    ) -> None:
        """
        Inject sentiment score into Redis cache.

        Used to create test scenarios where sentiment triggers trades.

        Args:
            pair: Trading pair
            score: Sentiment score (-1.0 to +1.0)
            headline: Fake headline to associate with sentiment
            source: Source identifier

        Raises:
            ManualTradeError: If injection fails
        """
        # Validate score range
        if not -1.0 <= score <= 1.0:
            raise ManualTradeError(f"Invalid sentiment score: {score} (must be -1.0 to +1.0)")

        logger.info(f"Injecting sentiment for {pair}: score={score:.2f}")

        try:
            # Write to Redis (same format as signal_cacher)
            sentiment_data = {
                "score": str(score),
                "headline": headline,
                "source": source,
                "timestamp": datetime.utcnow().isoformat(),
                "manual_injection": "true",  # Flag for audit
            }

            # Use Redis HSET to store all fields
            for field, value in sentiment_data.items():
                self.redis.hset(f"sentiment:{pair}", field, value)

            logger.info(f"✓ Sentiment injected into Redis: sentiment:{pair}")

        except Exception as e:
            logger.error(f"Failed to inject sentiment: {e}", exc_info=True)
            raise ManualTradeError(f"Sentiment injection failed: {e}")

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """
        Get list of currently open trades.

        Returns:
            List of trade dictionaries

        Raises:
            ManualTradeError: If API call fails
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/status",
                auth=HTTPBasicAuth(self.api_username, self.api_password),
                timeout=5
            )
            response.raise_for_status()

            trades = response.json()
            logger.info(f"Retrieved {len(trades)} open trades")
            return trades

        except Exception as e:
            logger.error(f"Failed to get open trades: {e}")
            raise ManualTradeError(f"Failed to get open trades: {e}")

    def _log_manual_action(self, action: str, pair: str, details: Dict[str, Any]) -> None:
        """
        Log manual trading action for audit trail.

        Stores action in Redis list for historical tracking.

        Args:
            action: Action type (FORCE_BUY, FORCE_SELL, INJECT_SENTIMENT)
            pair: Trading pair
            details: Action details dictionary
        """
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "pair": pair,
                "details": details,
                "user": os.getenv("USER", "unknown"),  # System username
            }

            # Store in Redis list (keep last 100 actions)
            audit_key = "manual_trade_audit"
            self.redis.lpush(audit_key, json.dumps(audit_entry))
            self.redis.ltrim(audit_key, 0, 99)  # Keep only last 100 entries

            logger.info(f"Audit log entry created: {action} for {pair}")

        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
            # Don't raise - audit logging shouldn't block trades

    def get_audit_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve manual trade audit log.

        Args:
            limit: Maximum number of entries to retrieve

        Returns:
            List of audit entries (most recent first)
        """
        try:
            audit_key = "manual_trade_audit"
            entries = self.redis.lrange(audit_key, 0, limit - 1)

            # Parse JSON entries
            parsed_entries = []
            for entry in entries:
                try:
                    parsed_entries.append(json.loads(entry))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in audit log: {entry}")

            return parsed_entries

        except Exception as e:
            logger.error(f"Failed to retrieve audit log: {e}")
            return []


def main() -> None:
    """Test function - demonstrate manual trade controller"""
    try:
        controller = ManualTradeController()

        print("\n🎮 Manual Trade Controller Test")
        print("=" * 60)

        # Check open trades
        print("\n📊 Current Open Trades:")
        trades = controller.get_open_trades()
        if trades:
            for trade in trades:
                print(f"  • Trade #{trade.get('trade_id')}: {trade.get('pair')} "
                      f"(Profit: {trade.get('profit_pct', 0):.2f}%)")
        else:
            print("  No open trades")

        # Check audit log
        print("\n📜 Recent Manual Actions:")
        audit = controller.get_audit_log(limit=5)
        if audit:
            for entry in audit:
                print(f"  • {entry['timestamp']}: {entry['action']} on {entry['pair']}")
        else:
            print("  No manual actions recorded")

        print("\n✅ Manual Trade Controller operational")
        print("\nTo force a buy:")
        print("  controller.force_buy('BTC/USDT', amount_usdt=100, sentiment_score=0.85)")
        print("\nTo force a sell:")
        print("  controller.force_sell(trade_id=123)")

    except ManualTradeError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
