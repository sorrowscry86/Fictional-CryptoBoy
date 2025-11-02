"""
Redis Stress Testing Script
Tests cache performance under rapid sentiment updates
Simulates high-frequency trading scenario
"""

import json
import os
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.common.logging_config import setup_logging  # noqa: E402
from services.common.redis_client import RedisClient  # noqa: E402

logger = setup_logging("redis-stress-test")


class RedisStressTest:
    """Stress testing suite for Redis cache"""

    TRADING_PAIRS = [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "SOL/USDT",
        "ADA/USDT",
        "DOT/USDT",
        "MATIC/USDT",
        "AVAX/USDT",
        "LINK/USDT",
        "UNI/USDT",
    ]

    def __init__(self):
        """Initialize stress tester"""
        self.redis = RedisClient()
        self.results = {
            "write": [],
            "read": [],
            "total_operations": 0,
            "failed_operations": 0,
            "start_time": None,
            "end_time": None,
        }

    def setup(self):
        """Setup test environment"""
        logger.info("Setting up Redis stress test...")
        # Clear any existing test data
        test_keys = self.redis.keys("test:sentiment:*")
        if test_keys:
            self.redis.delete(*test_keys)
            logger.info(f"Cleared {len(test_keys)} test keys")
        logger.info("Redis stress test ready")

    def teardown(self):
        """Cleanup test environment"""
        logger.info("Cleaning up test environment...")
        test_keys = self.redis.keys("test:sentiment:*")
        if test_keys:
            deleted = self.redis.delete(*test_keys)
            logger.info(f"Deleted {deleted} test keys")
        self.redis.close()

    def generate_sentiment_data(self, pair: str) -> Dict[str, Any]:
        """
        Generate random sentiment data

        Args:
            pair: Trading pair

        Returns:
            Sentiment data dictionary
        """
        score = random.uniform(-1.0, 1.0)
        labels = ["very_bearish", "bearish", "neutral", "bullish", "very_bullish"]
        label = labels[int((score + 1) * 2.5)]

        return {
            "score": score,
            "label": label,
            "timestamp": datetime.utcnow().isoformat(),
            "headline": f"Test headline for {pair}",
            "source": "stress_test",
            "article_id": f"test_{int(time.time() * 1000)}",
        }

    def write_sentiment(self, pair: str, use_test_prefix: bool = True) -> Dict[str, Any]:
        """
        Write sentiment to Redis and measure latency

        Args:
            pair: Trading pair
            use_test_prefix: Use 'test:' prefix for keys

        Returns:
            Performance metrics
        """
        start = time.time()
        try:
            key = f"{'test:' if use_test_prefix else ''}sentiment:{pair}"
            data = self.generate_sentiment_data(pair)

            self.redis.hset_json(key, data)

            latency = (time.time() - start) * 1000  # ms
            return {"success": True, "latency_ms": latency, "operation": "write", "pair": pair}

        except Exception as e:
            logger.error(f"Failed to write sentiment for {pair}: {e}")
            return {"success": False, "error": str(e), "operation": "write", "pair": pair}

    def read_sentiment(self, pair: str, use_test_prefix: bool = True) -> Dict[str, Any]:
        """
        Read sentiment from Redis and measure latency

        Args:
            pair: Trading pair
            use_test_prefix: Use 'test:' prefix for keys

        Returns:
            Performance metrics
        """
        start = time.time()
        try:
            key = f"{'test:' if use_test_prefix else ''}sentiment:{pair}"
            data = self.redis.hgetall_json(key)

            latency = (time.time() - start) * 1000  # ms
            return {"success": True, "latency_ms": latency, "operation": "read", "pair": pair, "data_found": bool(data)}

        except Exception as e:
            logger.error(f"Failed to read sentiment for {pair}: {e}")
            return {"success": False, "error": str(e), "operation": "read", "pair": pair}

    def test_rapid_updates(self, iterations: int = 10000, pairs: List[str] = None):
        """
        Test rapid sequential updates

        Args:
            iterations: Number of update iterations
            pairs: Trading pairs to test (uses all if None)
        """
        if pairs is None:
            pairs = self.TRADING_PAIRS

        logger.info(f"Starting rapid updates test: {iterations} iterations across {len(pairs)} pairs")
        self.results["start_time"] = time.time()

        success_count = 0
        for i in range(iterations):
            pair = random.choice(pairs)
            result = self.write_sentiment(pair)

            if result["success"]:
                self.results["write"].append(result["latency_ms"])
                success_count += 1
            else:
                self.results["failed_operations"] += 1

            if (i + 1) % 1000 == 0:
                avg_latency = statistics.mean(self.results["write"][-1000:])
                ops_per_sec = 1000 / (time.time() - self.results["start_time"]) * (i + 1) / iterations
                logger.info(
                    f"Progress: {i+1}/{iterations}, " f"avg latency: {avg_latency:.2f}ms, " f"~{ops_per_sec:.0f} ops/s"
                )

        self.results["end_time"] = time.time()
        self.results["total_operations"] = success_count
        logger.info(f"Rapid updates complete: {success_count} successful, {self.results['failed_operations']} failed")

    def test_parallel_updates(self, iterations: int = 10000, workers: int = 20, pairs: List[str] = None):
        """
        Test parallel updates from multiple workers

        Args:
            iterations: Total number of operations
            workers: Number of parallel workers
            pairs: Trading pairs to test
        """
        if pairs is None:
            pairs = self.TRADING_PAIRS

        logger.info(
            f"Starting parallel updates test: {iterations} operations, {workers} workers, {len(pairs)} pairs"
        )
        self.results["start_time"] = time.time()

        def worker_task(task_id):
            pair = random.choice(pairs)
            return self.write_sentiment(pair)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(worker_task, i): i for i in range(iterations)}

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                if result["success"]:
                    self.results["write"].append(result["latency_ms"])
                    self.results["total_operations"] += 1
                else:
                    self.results["failed_operations"] += 1

                completed += 1
                if completed % 1000 == 0:
                    logger.info(f"Progress: {completed}/{iterations} operations")

        self.results["end_time"] = time.time()
        logger.info(
            f"Parallel updates complete: "
            f"{self.results['total_operations']} successful, "
            f"{self.results['failed_operations']} failed"
        )

    def test_mixed_workload(self, iterations: int = 10000, read_ratio: float = 0.7, pairs: List[str] = None):
        """
        Test mixed read/write workload

        Args:
            iterations: Total operations
            read_ratio: Ratio of reads to total operations (0.0-1.0)
            pairs: Trading pairs to test
        """
        if pairs is None:
            pairs = self.TRADING_PAIRS

        logger.info(
            f"Starting mixed workload test: {iterations} operations, "
            f"{read_ratio*100:.0f}% reads, {(1-read_ratio)*100:.0f}% writes"
        )
        self.results["start_time"] = time.time()

        # Pre-populate some data for reads
        logger.info("Pre-populating data...")
        for pair in pairs:
            self.write_sentiment(pair)

        success_count = 0
        for i in range(iterations):
            pair = random.choice(pairs)

            # Decide read or write based on ratio
            if random.random() < read_ratio:
                result = self.read_sentiment(pair)
                if result["success"]:
                    self.results["read"].append(result["latency_ms"])
            else:
                result = self.write_sentiment(pair)
                if result["success"]:
                    self.results["write"].append(result["latency_ms"])

            if result["success"]:
                success_count += 1
            else:
                self.results["failed_operations"] += 1

            if (i + 1) % 1000 == 0:
                logger.info(f"Progress: {i+1}/{iterations} operations")

        self.results["end_time"] = time.time()
        self.results["total_operations"] = success_count
        logger.info(f"Mixed workload complete: {success_count} successful operations")

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate performance report

        Returns:
            Performance metrics dictionary
        """
        duration = self.results["end_time"] - self.results["start_time"]
        throughput = self.results["total_operations"] / duration if duration > 0 else 0

        write_latencies = self.results["write"]
        read_latencies = self.results["read"]

        report = {
            "summary": {
                "total_operations": self.results["total_operations"],
                "failed_operations": self.results["failed_operations"],
                "write_operations": len(write_latencies),
                "read_operations": len(read_latencies),
                "duration_seconds": round(duration, 2),
                "throughput_ops_per_sec": round(throughput, 2),
                "success_rate": (
                    round(
                        self.results["total_operations"]
                        / (self.results["total_operations"] + self.results["failed_operations"])
                        * 100,
                        2,
                    )
                    if (self.results["total_operations"] + self.results["failed_operations"]) > 0
                    else 0
                ),
            },
            "write_latency_ms": (
                {
                    "min": round(min(write_latencies), 2) if write_latencies else 0,
                    "max": round(max(write_latencies), 2) if write_latencies else 0,
                    "mean": round(statistics.mean(write_latencies), 2) if write_latencies else 0,
                    "median": round(statistics.median(write_latencies), 2) if write_latencies else 0,
                    "p95": (
                        round(statistics.quantiles(write_latencies, n=20)[18], 2) if len(write_latencies) > 20 else 0
                    ),
                    "p99": (
                        round(statistics.quantiles(write_latencies, n=100)[98], 2) if len(write_latencies) > 100 else 0
                    ),
                }
                if write_latencies
                else None
            ),
            "read_latency_ms": (
                {
                    "min": round(min(read_latencies), 2) if read_latencies else 0,
                    "max": round(max(read_latencies), 2) if read_latencies else 0,
                    "mean": round(statistics.mean(read_latencies), 2) if read_latencies else 0,
                    "median": round(statistics.median(read_latencies), 2) if read_latencies else 0,
                    "p95": round(statistics.quantiles(read_latencies, n=20)[18], 2) if len(read_latencies) > 20 else 0,
                    "p99": (
                        round(statistics.quantiles(read_latencies, n=100)[98], 2) if len(read_latencies) > 100 else 0
                    ),
                }
                if read_latencies
                else None
            ),
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("REDIS STRESS TEST REPORT")
        print("=" * 80)
        print("\nSUMMARY:")
        print(f"  Total Operations:   {report['summary']['total_operations']:,}")
        print(f"  Write Operations:   {report['summary']['write_operations']:,}")
        print(f"  Read Operations:    {report['summary']['read_operations']:,}")
        print(f"  Failed Operations:  {report['summary']['failed_operations']:,}")
        print(f"  Duration:           {report['summary']['duration_seconds']:.2f}s")
        print(f"  Throughput:         {report['summary']['throughput_ops_per_sec']:.2f} ops/s")
        print(f"  Success Rate:       {report['summary']['success_rate']:.2f}%")

        if report["write_latency_ms"]:
            print("\nWRITE LATENCY (ms):")
            print(f"  Min:                {report['write_latency_ms']['min']:.2f}")
            print(f"  Mean:               {report['write_latency_ms']['mean']:.2f}")
            print(f"  Median:             {report['write_latency_ms']['median']:.2f}")
            print(f"  P95:                {report['write_latency_ms']['p95']:.2f}")
            print(f"  P99:                {report['write_latency_ms']['p99']:.2f}")
            print(f"  Max:                {report['write_latency_ms']['max']:.2f}")

        if report["read_latency_ms"]:
            print("\nREAD LATENCY (ms):")
            print(f"  Min:                {report['read_latency_ms']['min']:.2f}")
            print(f"  Mean:               {report['read_latency_ms']['mean']:.2f}")
            print(f"  Median:             {report['read_latency_ms']['median']:.2f}")
            print(f"  P95:                {report['read_latency_ms']['p95']:.2f}")
            print(f"  P99:                {report['read_latency_ms']['p99']:.2f}")
            print(f"  Max:                {report['read_latency_ms']['max']:.2f}")

        print("\n" + "=" * 80)

    def save_report(self, report: Dict[str, Any], filename: str = "redis_stress_test_report.json"):
        """
        Save report to file

        Args:
            report: Report dictionary
            filename: Output filename
        """
        filepath = os.path.join("tests", "stress_tests", filename)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {filepath}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Redis Stress Testing")
    parser.add_argument("--operations", type=int, default=10000, help="Number of operations")
    parser.add_argument("--workers", type=int, default=20, help="Number of parallel workers")
    parser.add_argument("--mode", choices=["rapid", "parallel", "mixed"], default="parallel", help="Test mode")
    parser.add_argument("--read-ratio", type=float, default=0.7, help="Read ratio for mixed mode (0.0-1.0)")

    args = parser.parse_args()

    tester = RedisStressTest()

    try:
        tester.setup()

        # Run test based on mode
        if args.mode == "rapid":
            tester.test_rapid_updates(iterations=args.operations)
        elif args.mode == "parallel":
            tester.test_parallel_updates(iterations=args.operations, workers=args.workers)
        else:  # mixed
            tester.test_mixed_workload(iterations=args.operations, read_ratio=args.read_ratio)

        # Generate and display report
        report = tester.generate_report()
        tester.print_report(report)
        tester.save_report(report)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        tester.teardown()


if __name__ == "__main__":
    main()
