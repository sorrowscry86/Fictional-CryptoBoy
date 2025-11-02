"""
End-to-End Latency Monitor
Measures complete pipeline latency: RSS → Sentiment Analysis → Redis
Target: < 5 seconds end-to-end
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.common.logging_config import setup_logging  # noqa: E402
from services.common.rabbitmq_client import RabbitMQClient  # noqa: E402
from services.common.redis_client import RedisClient  # noqa: E402

logger = setup_logging("latency-monitor")


class LatencyMonitor:
    """
    End-to-end latency monitoring for sentiment pipeline
    Tracks message flow from ingestion to cache
    """

    def __init__(self):
        """Initialize latency monitor"""
        self.rabbitmq = RabbitMQClient()
        self.redis = RedisClient()

        self.measurements = []
        self.target_latency_seconds = 5.0

    def setup(self):
        """Setup monitoring"""
        logger.info("Setting up latency monitor...")
        self.rabbitmq.connect()
        logger.info("Latency monitor ready")

    def teardown(self):
        """Cleanup"""
        logger.info("Shutting down latency monitor...")
        self.rabbitmq.close()
        self.redis.close()

    def inject_test_article(self, pair: str = "BTC/USDT") -> Dict[str, Any]:
        """
        Inject a test news article into the pipeline

        Args:
            pair: Trading pair to target

        Returns:
            Test article data with injection timestamp
        """
        timestamp = datetime.utcnow()
        article_id = hashlib.md5(f"{timestamp.isoformat()}_{pair}".encode()).hexdigest()

        article = {
            "type": "news_article",
            "article_id": article_id,
            "source": "latency_test",
            "title": f"Test article for {pair} latency measurement",
            "link": f"https://test.com/article/{article_id}",
            "summary": "Bitcoin shows strong momentum as institutional adoption continues.",
            "content": "Bitcoin price reaches new highs amid increasing institutional interest. "
            "Major corporations announce cryptocurrency investment plans.",
            "published": timestamp.isoformat(),
            "fetched_at": timestamp.isoformat(),
            "latency_test": True,
            "injection_timestamp": timestamp.isoformat(),
        }

        # Publish to raw_news_data queue
        self.rabbitmq.publish("raw_news_data", article, persistent=True)

        logger.info(f"Injected test article {article_id} for {pair}")

        return {"article_id": article_id, "pair": pair, "injection_time": timestamp, "article": article}

    def wait_for_redis_update(
        self, pair: str, article_id: str, timeout_seconds: int = 10, poll_interval: float = 0.1
    ) -> Dict[str, Any]:
        """
        Wait for sentiment to appear in Redis cache

        Args:
            pair: Trading pair
            article_id: Article ID to wait for
            timeout_seconds: Maximum wait time
            poll_interval: Time between polls

        Returns:
            Timing data or None if timeout
        """
        start = time.time()
        key = f"sentiment:{pair}"

        while (time.time() - start) < timeout_seconds:
            try:
                data = self.redis.hgetall_json(key)

                if data and data.get("article_id") == article_id:
                    cache_time = datetime.utcnow()
                    return {
                        "found": True,
                        "cache_time": cache_time,
                        "wait_duration": time.time() - start,
                        "sentiment_data": data,
                    }

            except Exception as e:
                logger.warning(f"Error checking Redis: {e}")

            time.sleep(poll_interval)

        return {"found": False, "wait_duration": time.time() - start}

    def measure_single_latency(self, pair: str = "BTC/USDT") -> Dict[str, Any]:
        """
        Measure end-to-end latency for a single article

        Args:
            pair: Trading pair to test

        Returns:
            Latency measurement data
        """
        logger.info(f"Starting latency measurement for {pair}")

        # Step 1: Inject test article
        injection_data = self.inject_test_article(pair)
        injection_time = injection_data["injection_time"]
        article_id = injection_data["article_id"]

        # Step 2: Wait for sentiment in Redis
        wait_result = self.wait_for_redis_update(pair, article_id, timeout_seconds=15)

        if not wait_result["found"]:
            logger.warning(f"Timeout waiting for sentiment for {pair}")
            return {
                "success": False,
                "pair": pair,
                "article_id": article_id,
                "injection_time": injection_time.isoformat(),
                "timeout": True,
                "wait_duration": wait_result["wait_duration"],
            }

        # Step 3: Calculate end-to-end latency
        cache_time = wait_result["cache_time"]
        end_to_end_latency = (cache_time - injection_time).total_seconds()

        # Extract timestamps from sentiment data
        sentiment_data = wait_result["sentiment_data"]
        analyzed_at = datetime.fromisoformat(sentiment_data.get("timestamp", cache_time.isoformat()))

        # Calculate stage latencies
        processing_latency = (analyzed_at - injection_time).total_seconds()
        caching_latency = (cache_time - analyzed_at).total_seconds()

        result = {
            "success": True,
            "pair": pair,
            "article_id": article_id,
            "injection_time": injection_time.isoformat(),
            "analysis_time": analyzed_at.isoformat(),
            "cache_time": cache_time.isoformat(),
            "latency": {
                "end_to_end_seconds": round(end_to_end_latency, 3),
                "processing_seconds": round(processing_latency, 3),
                "caching_seconds": round(caching_latency, 3),
            },
            "meets_target": end_to_end_latency < self.target_latency_seconds,
            "sentiment": {"score": sentiment_data.get("score"), "label": sentiment_data.get("label")},
        }

        logger.info(
            f"Latency measurement complete: {end_to_end_latency:.3f}s end-to-end "
            f"({'✓ PASS' if result['meets_target'] else '✗ FAIL'} < {self.target_latency_seconds}s)"
        )

        return result

    def measure_sustained_latency(
        self, num_measurements: int = 20, interval_seconds: int = 15, pairs: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Measure latency over multiple iterations

        Args:
            num_measurements: Number of measurements to take
            interval_seconds: Time between measurements
            pairs: Trading pairs to test (cycles through them)

        Returns:
            List of measurement results
        """
        if pairs is None:
            pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]

        logger.info(
            f"Starting sustained latency measurement: " f"{num_measurements} measurements, {interval_seconds}s interval"
        )

        results = []
        for i in range(num_measurements):
            pair = pairs[i % len(pairs)]

            logger.info(f"\nMeasurement {i+1}/{num_measurements} for {pair}")

            try:
                result = self.measure_single_latency(pair)
                results.append(result)

                if result["success"]:
                    self.measurements.append(result["latency"]["end_to_end_seconds"])

            except Exception as e:
                logger.error(f"Measurement failed: {e}", exc_info=True)
                results.append({"success": False, "pair": pair, "error": str(e), "measurement_index": i})

            # Wait before next measurement (except for last one)
            if i < num_measurements - 1:
                logger.info(f"Waiting {interval_seconds}s before next measurement...")
                time.sleep(interval_seconds)

        return results

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze measurement results

        Args:
            results: List of measurement results

        Returns:
            Analysis summary
        """
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]

        if not successful:
            return {
                "total_measurements": len(results),
                "successful": 0,
                "failed": len(failed),
                "success_rate": 0.0,
                "error": "No successful measurements",
            }

        latencies = [r["latency"]["end_to_end_seconds"] for r in successful]
        processing_latencies = [r["latency"]["processing_seconds"] for r in successful]
        caching_latencies = [r["latency"]["caching_seconds"] for r in successful]
        meets_target = [r for r in successful if r["meets_target"]]

        import statistics

        analysis = {
            "total_measurements": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": round(len(successful) / len(results) * 100, 2),
            "target_latency_seconds": self.target_latency_seconds,
            "target_met_count": len(meets_target),
            "target_met_rate": round(len(meets_target) / len(successful) * 100, 2),
            "end_to_end_latency": {
                "min": round(min(latencies), 3),
                "max": round(max(latencies), 3),
                "mean": round(statistics.mean(latencies), 3),
                "median": round(statistics.median(latencies), 3),
                "p95": round(statistics.quantiles(latencies, n=20)[18], 3) if len(latencies) > 20 else None,
                "p99": round(statistics.quantiles(latencies, n=100)[98], 3) if len(latencies) > 100 else None,
            },
            "processing_latency": {
                "min": round(min(processing_latencies), 3),
                "max": round(max(processing_latencies), 3),
                "mean": round(statistics.mean(processing_latencies), 3),
                "median": round(statistics.median(processing_latencies), 3),
            },
            "caching_latency": {
                "min": round(min(caching_latencies), 3),
                "max": round(max(caching_latencies), 3),
                "mean": round(statistics.mean(caching_latencies), 3),
                "median": round(statistics.median(caching_latencies), 3),
            },
        }

        return analysis

    def print_analysis(self, analysis: Dict[str, Any]):
        """Print formatted analysis"""
        print("\n" + "=" * 80)
        print("END-TO-END LATENCY ANALYSIS")
        print("=" * 80)
        print("\nSUMMARY:")
        print(f"  Total Measurements:       {analysis['total_measurements']}")
        print(f"  Successful:               {analysis['successful']}")
        print(f"  Failed:                   {analysis['failed']}")
        print(f"  Success Rate:             {analysis['success_rate']:.2f}%")
        print(f"\nTARGET: {analysis['target_latency_seconds']}s")
        print(f"  Met Target:               {analysis['target_met_count']}/{analysis['successful']}")
        print(f"  Target Met Rate:          {analysis['target_met_rate']:.2f}%")

        print("\nEND-TO-END LATENCY (seconds):")
        print(f"  Min:                      {analysis['end_to_end_latency']['min']:.3f}")
        print(f"  Mean:                     {analysis['end_to_end_latency']['mean']:.3f}")
        print(f"  Median:                   {analysis['end_to_end_latency']['median']:.3f}")
        if analysis["end_to_end_latency"]["p95"]:
            print(f"  P95:                      {analysis['end_to_end_latency']['p95']:.3f}")
        if analysis["end_to_end_latency"]["p99"]:
            print(f"  P99:                      {analysis['end_to_end_latency']['p99']:.3f}")
        print(f"  Max:                      {analysis['end_to_end_latency']['max']:.3f}")

        print("\nPROCESSING LATENCY (seconds):")
        print("  (News ingestion → Sentiment analysis)")
        print(f"  Mean:                     {analysis['processing_latency']['mean']:.3f}")
        print(f"  Median:                   {analysis['processing_latency']['median']:.3f}")
        print(
            f"  Range:                    [{analysis['processing_latency']['min']:.3f}, "
            f"{analysis['processing_latency']['max']:.3f}]"
        )

        print("\nCACHING LATENCY (seconds):")
        print("  (Sentiment analysis → Redis cache)")
        print(f"  Mean:                     {analysis['caching_latency']['mean']:.3f}")
        print(f"  Median:                   {analysis['caching_latency']['median']:.3f}")
        print(
            f"  Range:                    [{analysis['caching_latency']['min']:.3f}, "
            f"{analysis['caching_latency']['max']:.3f}]"
        )

        print("\n" + "=" * 80)

        # Identify bottleneck
        if analysis["processing_latency"]["mean"] > analysis["caching_latency"]["mean"] * 5:
            print("⚠️  BOTTLENECK: Sentiment analysis (processing latency)")
        elif analysis["caching_latency"]["mean"] > analysis["processing_latency"]["mean"] * 2:
            print("⚠️  BOTTLENECK: Redis caching")
        else:
            print("✓ Balanced latency distribution")

        print("=" * 80 + "\n")

    def save_results(
        self, results: List[Dict[str, Any]], analysis: Dict[str, Any], filename: str = "latency_measurement.json"
    ):
        """
        Save results to file

        Args:
            results: List of measurement results
            analysis: Analysis summary
            filename: Output filename
        """
        output = {"timestamp": datetime.utcnow().isoformat(), "analysis": analysis, "measurements": results}

        filepath = os.path.join("tests", "monitoring", filename)
        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)
        logger.info(f"Results saved to {filepath}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="End-to-End Latency Monitoring")
    parser.add_argument("--measurements", type=int, default=20, help="Number of measurements")
    parser.add_argument("--interval", type=int, default=15, help="Seconds between measurements")
    parser.add_argument("--target", type=float, default=5.0, help="Target latency in seconds")

    args = parser.parse_args()

    monitor = LatencyMonitor()
    monitor.target_latency_seconds = args.target

    try:
        monitor.setup()

        # Run measurements
        results = monitor.measure_sustained_latency(num_measurements=args.measurements, interval_seconds=args.interval)

        # Analyze and display results
        analysis = monitor.analyze_results(results)
        monitor.print_analysis(analysis)
        monitor.save_results(results, analysis)

    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}", exc_info=True)
    finally:
        monitor.teardown()


if __name__ == "__main__":
    main()
