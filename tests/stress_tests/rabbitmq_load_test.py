"""
RabbitMQ Load Testing Script
Tests message throughput and queue performance under load
Target: 10,000 messages with performance metrics
"""

import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from services.common.logging_config import setup_logging  # noqa: E402
from services.common.rabbitmq_client import RabbitMQClient  # noqa: E402

logger = setup_logging("rabbitmq-load-test")


class RabbitMQLoadTest:
    """Load testing suite for RabbitMQ message queue"""

    def __init__(self, queue_name: str = "load_test_queue"):
        """
        Initialize load tester

        Args:
            queue_name: Queue name for testing
        """
        self.queue_name = queue_name
        self.rabbitmq = RabbitMQClient()
        self.results = {
            "publish": [],
            "consume": [],
            "total_messages": 0,
            "failed_messages": 0,
            "start_time": None,
            "end_time": None,
        }

    def setup(self):
        """Setup test environment"""
        logger.info("Setting up RabbitMQ load test...")
        self.rabbitmq.connect()
        # Declare test queue with arguments for performance
        self.rabbitmq.declare_queue(
            self.queue_name,
            durable=True,
            arguments={"x-max-length": 50000, "x-message-ttl": 3600000},  # Max queue length  # 1 hour TTL
        )
        logger.info(f"Test queue '{self.queue_name}' ready")

    def teardown(self):
        """Cleanup test environment"""
        logger.info("Cleaning up test environment...")
        try:
            # Purge test queue
            self.rabbitmq.channel.queue_purge(self.queue_name)
            logger.info(f"Purged queue '{self.queue_name}'")
        except Exception as e:
            logger.error(f"Error purging queue: {e}")
        finally:
            self.rabbitmq.close()

    def generate_test_message(self, msg_id: int) -> Dict[str, Any]:
        """
        Generate a test message simulating sentiment signal

        Args:
            msg_id: Message identifier

        Returns:
            Test message dictionary
        """
        return {
            "type": "sentiment_signal",
            "message_id": msg_id,
            "pair": "BTC/USDT",
            "sentiment_score": 0.5 + (msg_id % 100) / 200,  # Vary between 0.5 and 1.0
            "sentiment_label": "bullish",
            "headline": f"Test headline {msg_id}" * 10,  # ~150 bytes
            "timestamp": datetime.utcnow().isoformat(),
            "test_data": "x" * 200,  # Add some bulk
        }

    def publish_single_message(self, msg_id: int) -> Dict[str, Any]:
        """
        Publish a single message and measure latency

        Args:
            msg_id: Message ID

        Returns:
            Performance metrics
        """
        start = time.time()
        try:
            message = self.generate_test_message(msg_id)
            self.rabbitmq.publish(self.queue_name, message, persistent=True, declare_queue=False)
            latency = (time.time() - start) * 1000  # ms
            return {"success": True, "latency_ms": latency, "msg_id": msg_id}
        except Exception as e:
            logger.error(f"Failed to publish message {msg_id}: {e}")
            return {"success": False, "error": str(e), "msg_id": msg_id}

    def test_burst_publish(self, num_messages: int = 10000, batch_size: int = 100):
        """
        Test burst publishing with batches

        Args:
            num_messages: Total messages to publish
            batch_size: Messages per batch
        """
        logger.info(f"Starting burst publish test: {num_messages} messages")
        self.results["start_time"] = time.time()

        published = 0
        failed = 0

        for batch_start in range(0, num_messages, batch_size):
            batch_end = min(batch_start + batch_size, num_messages)
            batch_start_time = time.time()

            for msg_id in range(batch_start, batch_end):
                result = self.publish_single_message(msg_id)
                if result["success"]:
                    self.results["publish"].append(result["latency_ms"])
                    published += 1
                else:
                    failed += 1

            batch_time = time.time() - batch_start_time
            msg_per_sec = batch_size / batch_time if batch_time > 0 else 0

            logger.info(
                f"Batch {batch_start}-{batch_end}: "
                f"{msg_per_sec:.0f} msg/s, "
                f"avg latency: {statistics.mean(self.results['publish'][-batch_size:]):.2f}ms"
            )

        self.results["end_time"] = time.time()
        self.results["total_messages"] = published
        self.results["failed_messages"] = failed

        logger.info(f"Burst publish complete: {published} sent, {failed} failed")

    def test_parallel_publish(self, num_messages: int = 10000, workers: int = 10):
        """
        Test parallel publishing with multiple workers

        Args:
            num_messages: Total messages to publish
            workers: Number of parallel workers
        """
        logger.info(f"Starting parallel publish test: {num_messages} messages, {workers} workers")
        self.results["start_time"] = time.time()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.publish_single_message, msg_id): msg_id for msg_id in range(num_messages)}

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                if result["success"]:
                    self.results["publish"].append(result["latency_ms"])
                    self.results["total_messages"] += 1
                else:
                    self.results["failed_messages"] += 1

                completed += 1
                if completed % 1000 == 0:
                    logger.info(f"Progress: {completed}/{num_messages} messages")

        self.results["end_time"] = time.time()
        logger.info(
            f"Parallel publish complete: "
            f"{self.results['total_messages']} sent, "
            f"{self.results['failed_messages']} failed"
        )

    def test_consume_throughput(self, expected_messages: int):
        """
        Test message consumption throughput

        Args:
            expected_messages: Expected number of messages to consume
        """
        logger.info(f"Starting consume test: expecting {expected_messages} messages")

        consumed = 0
        consume_latencies = []
        start_time = time.time()

        def consume_callback(ch, method, properties, body):
            nonlocal consumed
            consume_start = time.time()
            try:
                json.loads(body.decode("utf-8"))  # Validate JSON
                consumed += 1
                latency = (time.time() - consume_start) * 1000
                consume_latencies.append(latency)

                if consumed % 1000 == 0:
                    logger.info(f"Consumed {consumed}/{expected_messages} messages")

                ch.basic_ack(delivery_tag=method.delivery_tag)

                if consumed >= expected_messages:
                    ch.stop_consuming()

            except Exception as e:
                logger.error(f"Error consuming message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        try:
            self.rabbitmq.channel.basic_qos(prefetch_count=100)
            self.rabbitmq.channel.basic_consume(
                queue=self.queue_name, on_message_callback=consume_callback, auto_ack=False
            )

            self.rabbitmq.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Consumption interrupted")
        finally:
            end_time = time.time()
            duration = end_time - start_time

            self.results["consume"] = consume_latencies
            logger.info(
                f"Consumption complete: {consumed} messages in {duration:.2f}s " f"({consumed/duration:.0f} msg/s)"
            )

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate performance report

        Returns:
            Performance metrics dictionary
        """
        duration = self.results["end_time"] - self.results["start_time"]
        throughput = self.results["total_messages"] / duration if duration > 0 else 0

        publish_latencies = self.results["publish"]
        consume_latencies = self.results["consume"]

        report = {
            "summary": {
                "total_messages": self.results["total_messages"],
                "failed_messages": self.results["failed_messages"],
                "duration_seconds": round(duration, 2),
                "throughput_msg_per_sec": round(throughput, 2),
                "success_rate": (
                    round(
                        self.results["total_messages"]
                        / (self.results["total_messages"] + self.results["failed_messages"])
                        * 100,
                        2,
                    )
                    if (self.results["total_messages"] + self.results["failed_messages"]) > 0
                    else 0
                ),
            },
            "publish_latency_ms": {
                "min": round(min(publish_latencies), 2) if publish_latencies else 0,
                "max": round(max(publish_latencies), 2) if publish_latencies else 0,
                "mean": round(statistics.mean(publish_latencies), 2) if publish_latencies else 0,
                "median": round(statistics.median(publish_latencies), 2) if publish_latencies else 0,
                "p95": (
                    round(statistics.quantiles(publish_latencies, n=20)[18], 2) if len(publish_latencies) > 20 else 0
                ),
                "p99": (
                    round(statistics.quantiles(publish_latencies, n=100)[98], 2) if len(publish_latencies) > 100 else 0
                ),
            },
            "consume_latency_ms": (
                {
                    "min": round(min(consume_latencies), 2) if consume_latencies else 0,
                    "max": round(max(consume_latencies), 2) if consume_latencies else 0,
                    "mean": round(statistics.mean(consume_latencies), 2) if consume_latencies else 0,
                    "median": round(statistics.median(consume_latencies), 2) if consume_latencies else 0,
                }
                if consume_latencies
                else None
            ),
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("RABBITMQ LOAD TEST REPORT")
        print("=" * 80)
        print("\nSUMMARY:")
        print(f"  Total Messages:     {report['summary']['total_messages']:,}")
        print(f"  Failed Messages:    {report['summary']['failed_messages']:,}")
        print(f"  Duration:           {report['summary']['duration_seconds']:.2f}s")
        print(f"  Throughput:         {report['summary']['throughput_msg_per_sec']:.2f} msg/s")
        print(f"  Success Rate:       {report['summary']['success_rate']:.2f}%")

        print("\nPUBLISH LATENCY (ms):")
        print(f"  Min:                {report['publish_latency_ms']['min']:.2f}")
        print(f"  Mean:               {report['publish_latency_ms']['mean']:.2f}")
        print(f"  Median:             {report['publish_latency_ms']['median']:.2f}")
        print(f"  P95:                {report['publish_latency_ms']['p95']:.2f}")
        print(f"  P99:                {report['publish_latency_ms']['p99']:.2f}")
        print(f"  Max:                {report['publish_latency_ms']['max']:.2f}")

        if report["consume_latency_ms"]:
            print("\nCONSUME LATENCY (ms):")
            print(f"  Min:                {report['consume_latency_ms']['min']:.2f}")
            print(f"  Mean:               {report['consume_latency_ms']['mean']:.2f}")
            print(f"  Median:             {report['consume_latency_ms']['median']:.2f}")
            print(f"  Max:                {report['consume_latency_ms']['max']:.2f}")

        print("\n" + "=" * 80)

    def save_report(self, report: Dict[str, Any], filename: str = "rabbitmq_load_test_report.json"):
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

    parser = argparse.ArgumentParser(description="RabbitMQ Load Testing")
    parser.add_argument("--messages", type=int, default=10000, help="Number of messages to send")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--mode", choices=["burst", "parallel"], default="parallel", help="Publishing mode")
    parser.add_argument("--test-consume", action="store_true", help="Also test consumption")

    args = parser.parse_args()

    tester = RabbitMQLoadTest()

    try:
        tester.setup()

        # Publish test
        if args.mode == "burst":
            tester.test_burst_publish(num_messages=args.messages)
        else:
            tester.test_parallel_publish(num_messages=args.messages, workers=args.workers)

        # Consume test (optional)
        if args.test_consume:
            tester.test_consume_throughput(expected_messages=args.messages)

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
