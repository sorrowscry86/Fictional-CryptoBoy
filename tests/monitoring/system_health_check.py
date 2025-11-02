"""
System Health Check and Monitoring Dashboard
Provides real-time status of all microservices and infrastructure
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

import requests

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.common.logging_config import setup_logging  # noqa: E402
from services.common.rabbitmq_client import RabbitMQClient  # noqa: E402
from services.common.redis_client import RedisClient  # noqa: E402

logger = setup_logging("health-check")


class SystemHealthCheck:
    """Comprehensive system health monitoring"""

    def __init__(self):
        """Initialize health checker"""
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")

        self.health_status = {
            "timestamp": None,
            "overall_status": "unknown",
            "services": {},
            "queues": {},
            "cache": {},
            "alerts": [],
        }

    def check_rabbitmq(self) -> Dict[str, Any]:
        """Check RabbitMQ health and queue status"""
        logger.info("Checking RabbitMQ...")

        status = {"name": "RabbitMQ", "status": "unknown", "connection": False, "queues": {}}

        try:
            # Test connection
            client = RabbitMQClient()
            client.connect()

            status["connection"] = True

            # Check queue depths
            queues_to_check = ["raw_market_data", "raw_news_data", "sentiment_signals_queue"]

            for queue_name in queues_to_check:
                try:
                    method = client.channel.queue_declare(queue=queue_name, passive=True)
                    status["queues"][queue_name] = {
                        "message_count": method.method.message_count,
                        "consumer_count": method.method.consumer_count,
                        "status": "healthy" if method.method.consumer_count > 0 else "warning",
                    }

                    # Alert if queue is backing up
                    if method.method.message_count > 1000:
                        self.health_status["alerts"].append(
                            {
                                "severity": "warning",
                                "service": "RabbitMQ",
                                "message": f"Queue '{queue_name}' has {method.method.message_count} messages",
                            }
                        )

                    # Alert if no consumers
                    if method.method.consumer_count == 0:
                        self.health_status["alerts"].append(
                            {
                                "severity": "critical",
                                "service": "RabbitMQ",
                                "message": f"Queue '{queue_name}' has no consumers",
                            }
                        )

                except Exception as e:
                    status["queues"][queue_name] = {"status": "error", "error": str(e)}

            client.close()

            status["status"] = "healthy"

        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)
            self.health_status["alerts"].append(
                {"severity": "critical", "service": "RabbitMQ", "message": f"Connection failed: {e}"}
            )

        return status

    def check_redis(self) -> Dict[str, Any]:
        """Check Redis health and cache status"""
        logger.info("Checking Redis...")

        status = {"name": "Redis", "status": "unknown", "connection": False, "cache_stats": {}}

        try:
            # Test connection
            client = RedisClient()
            client.client.ping()

            status["connection"] = True

            # Get cache statistics
            sentiment_keys = client.keys("sentiment:*")
            status["cache_stats"] = {"total_sentiment_keys": len(sentiment_keys), "pairs_cached": len(sentiment_keys)}

            # Check individual pairs
            pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
            status["cache_stats"]["pairs"] = {}

            for pair in pairs:
                key = f"sentiment:{pair}"
                data = client.hgetall_json(key)

                if data:
                    # Check freshness
                    timestamp = data.get("timestamp", None)
                    if timestamp:
                        from datetime import datetime

                        cached_time = datetime.fromisoformat(timestamp)
                        age_hours = (datetime.utcnow() - cached_time).total_seconds() / 3600

                        status["cache_stats"]["pairs"][pair] = {
                            "cached": True,
                            "score": data.get("score"),
                            "age_hours": round(age_hours, 2),
                            "fresh": age_hours < 4,
                        }

                        # Alert if stale
                        if age_hours > 4:
                            self.health_status["alerts"].append(
                                {
                                    "severity": "warning",
                                    "service": "Redis",
                                    "message": f"Sentiment for {pair} is {age_hours:.1f} hours old",
                                }
                            )
                    else:
                        status["cache_stats"]["pairs"][pair] = {"cached": True, "no_timestamp": True}
                else:
                    status["cache_stats"]["pairs"][pair] = {"cached": False}

            client.close()

            status["status"] = "healthy"

        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)
            self.health_status["alerts"].append(
                {"severity": "critical", "service": "Redis", "message": f"Connection failed: {e}"}
            )

        return status

    def check_ollama(self) -> Dict[str, Any]:
        """Check Ollama LLM service health"""
        logger.info("Checking Ollama...")

        status = {"name": "Ollama", "status": "unknown", "connection": False, "models": []}

        try:
            # Test connection
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            response.raise_for_status()

            status["connection"] = True

            # Get available models
            data = response.json()
            models = data.get("models", [])
            status["models"] = [m.get("name") for m in models]

            # Check if required model is available
            required_model = os.getenv("OLLAMA_MODEL", "mistral:7b")
            model_names = [m.get("name") for m in models]

            if required_model in model_names:
                status["required_model"] = {"name": required_model, "available": True}
            else:
                status["required_model"] = {"name": required_model, "available": False}
                self.health_status["alerts"].append(
                    {
                        "severity": "critical",
                        "service": "Ollama",
                        "message": f"Required model '{required_model}' not found",
                    }
                )

            status["status"] = "healthy"

        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)
            self.health_status["alerts"].append(
                {"severity": "critical", "service": "Ollama", "message": f"Connection failed: {e}"}
            )

        return status

    def run_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check

        Returns:
            Complete health status
        """
        logger.info("Running system health check...")

        self.health_status["timestamp"] = datetime.utcnow().isoformat()
        self.health_status["alerts"] = []  # Reset alerts

        # Check all services
        self.health_status["services"] = {
            "rabbitmq": self.check_rabbitmq(),
            "redis": self.check_redis(),
            "ollama": self.check_ollama(),
        }

        # Determine overall status
        service_statuses = [s["status"] for s in self.health_status["services"].values()]

        if all(s == "healthy" for s in service_statuses):
            self.health_status["overall_status"] = "healthy"
        elif any(s == "unhealthy" for s in service_statuses):
            self.health_status["overall_status"] = "unhealthy"
        else:
            self.health_status["overall_status"] = "degraded"

        logger.info(f"Health check complete: {self.health_status['overall_status']}")

        return self.health_status

    def print_dashboard(self, health_status: Dict[str, Any] = None):
        """Print formatted health dashboard"""
        if health_status is None:
            health_status = self.health_status

        # Status emoji
        status_emoji = {"healthy": "✓", "unhealthy": "✗", "degraded": "⚠", "warning": "⚠", "unknown": "?"}

        print("\n" + "=" * 80)
        print("CRYPTOBOY SYSTEM HEALTH DASHBOARD")
        print("=" * 80)
        print(f"Timestamp: {health_status['timestamp']}")
        print(
            f"Overall Status: {status_emoji.get(health_status['overall_status'], '?')} "
            f"{health_status['overall_status'].upper()}"
        )
        print("")

        # Services
        print("SERVICES:")
        for service_name, service_data in health_status["services"].items():
            status = service_data.get("status", "unknown")
            emoji = status_emoji.get(status, "?")
            print(f"  {emoji} {service_data['name']}: {status.upper()}")

            if service_name == "rabbitmq" and "queues" in service_data:
                print("     Queues:")
                for queue_name, queue_data in service_data["queues"].items():
                    if "message_count" in queue_data:
                        queue_status = queue_data.get("status", "unknown")
                        queue_emoji = status_emoji.get(queue_status, "?")
                        print(
                            f"       {queue_emoji} {queue_name}: "
                            f"{queue_data['message_count']} messages, "
                            f"{queue_data['consumer_count']} consumers"
                        )

            if service_name == "redis" and "cache_stats" in service_data:
                print(f"     Cached Pairs: {service_data['cache_stats']['total_sentiment_keys']}")
                if "pairs" in service_data["cache_stats"]:
                    for pair, pair_data in service_data["cache_stats"]["pairs"].items():
                        if pair_data.get("cached"):
                            age = pair_data.get("age_hours", "N/A")
                            fresh_emoji = "✓" if pair_data.get("fresh", False) else "⚠"
                            print(
                                f"       {fresh_emoji} {pair}: "
                                f"score={pair_data.get('score', 'N/A'):.2f}, "
                                f"age={age}h"
                                if isinstance(age, (int, float))
                                else f"age={age}"
                            )
                        else:
                            print(f"       ✗ {pair}: Not cached")

            if service_name == "ollama" and "models" in service_data:
                print(f"     Models: {', '.join(service_data['models'])}")

            if "error" in service_data:
                print(f"     Error: {service_data['error']}")

        # Alerts
        if health_status["alerts"]:
            print("\nALERTS:")
            for alert in health_status["alerts"]:
                severity = alert.get("severity", "info")
                severity_emoji = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "ℹ️"
                print(f"  {severity_emoji} [{severity.upper()}] {alert['service']}: {alert['message']}")

        print("\n" + "=" * 80 + "\n")

    def save_health_report(self, health_status: Dict[str, Any] = None, filename: str = "health_report.json"):
        """
        Save health report to file

        Args:
            health_status: Health status data
            filename: Output filename
        """
        if health_status is None:
            health_status = self.health_status

        filepath = os.path.join("tests", "monitoring", filename)
        with open(filepath, "w") as f:
            json.dump(health_status, f, indent=2)
        logger.info(f"Health report saved to {filepath}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="System Health Check")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds")
    parser.add_argument("--save", action="store_true", help="Save report to file")

    args = parser.parse_args()

    checker = SystemHealthCheck()

    try:
        if args.watch:
            logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
            print("Press Ctrl+C to stop")

            while True:
                health_status = checker.run_health_check()
                checker.print_dashboard(health_status)

                if args.save:
                    checker.save_health_report(health_status)

                time.sleep(args.interval)

        else:
            # Single check
            health_status = checker.run_health_check()
            checker.print_dashboard(health_status)

            if args.save:
                checker.save_health_report(health_status)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
