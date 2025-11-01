"""
Sentiment Processing Load Test
Tests FinBERT sentiment analysis with concurrent articles
Measures throughput and latency for financial sentiment model
"""
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from llm.huggingface_sentiment import HuggingFaceFinancialSentiment
from services.common.logging_config import setup_logging

logger = setup_logging('sentiment-load-test')


class SentimentLoadTest:
    """Load testing suite for sentiment analysis"""

    # Sample test headlines representing different sentiment scenarios
    TEST_HEADLINES = [
        # Bullish
        "Bitcoin reaches new all-time high as institutional adoption accelerates",
        "Major tech company announces $1 billion Bitcoin investment",
        "Ethereum successfully completes network upgrade, gas fees drop 90%",
        "SEC approves first spot Bitcoin ETF, opening door for mainstream adoption",
        "Central bank explores blockchain integration for national currency",

        # Bearish
        "Major cryptocurrency exchange hacked, $500 million stolen",
        "Regulatory crackdown threatens crypto industry",
        "Bitcoin crashes 20% in hours amid liquidations",
        "Study reveals 90% of crypto projects fail within first year",
        "Government proposes ban on cryptocurrency mining operations",

        # Neutral
        "Cryptocurrency market sees mixed performance this week",
        "New blockchain startup raises $10 million in funding",
        "Industry conference discusses future of digital assets",
        "Trading volume remains steady across major exchanges",
        "Analysts divided on Bitcoin's near-term price direction",

        # Technical/Educational
        "Understanding consensus mechanisms in blockchain networks",
        "How to secure your cryptocurrency wallet: A guide",
        "Comparing layer-2 scaling solutions for Ethereum",
        "The evolution of smart contract platforms",
        "DeFi explained: Decentralized Finance fundamentals"
    ]

    def __init__(self, model_name: str = None):
        """
        Initialize load tester

        Args:
            model_name: FinBERT model name ('finbert', 'finbert-tone', or full HF path)
        """
        model = model_name or os.getenv('HUGGINGFACE_MODEL', 'finbert')

        self.analyzer = HuggingFaceFinancialSentiment(model_name=model)

        self.results = {
            'latencies': [],
            'scores': [],
            'total_articles': 0,
            'failed_articles': 0,
            'start_time': None,
            'end_time': None
        }

        logger.info(f"Initialized sentiment load tester with FinBERT model: {model}")

    def setup(self):
        """Setup test environment"""
        logger.info("Setting up sentiment load test...")
        # Test connection
        try:
            test_score = self.analyzer.analyze_sentiment("Test headline")
            logger.info(f"Connection test successful (score: {test_score})")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
        logger.info("Sentiment load test ready")

    def analyze_headline(self, headline: str, article_id: int) -> Dict[str, Any]:
        """
        Analyze a single headline and measure performance

        Args:
            headline: News headline
            article_id: Article identifier

        Returns:
            Performance metrics
        """
        start = time.time()
        try:
            score = self.analyzer.analyze_sentiment(headline)
            latency = (time.time() - start) * 1000  # ms

            return {
                'success': True,
                'latency_ms': latency,
                'score': score,
                'headline': headline,
                'article_id': article_id
            }

        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.error(f"Failed to analyze article {article_id}: {e}")
            return {
                'success': False,
                'latency_ms': latency,
                'error': str(e),
                'headline': headline,
                'article_id': article_id
            }

    def test_sequential_processing(self, num_articles: int = 100):
        """
        Test sequential article processing

        Args:
            num_articles: Number of articles to process
        """
        logger.info(f"Starting sequential processing test: {num_articles} articles")
        self.results['start_time'] = time.time()

        for i in range(num_articles):
            headline = self.TEST_HEADLINES[i % len(self.TEST_HEADLINES)]
            result = self.analyze_headline(headline, i)

            if result['success']:
                self.results['latencies'].append(result['latency_ms'])
                self.results['scores'].append(result['score'])
                self.results['total_articles'] += 1
            else:
                self.results['failed_articles'] += 1

            if (i + 1) % 10 == 0:
                avg_latency = statistics.mean(self.results['latencies'][-10:])
                logger.info(
                    f"Progress: {i+1}/{num_articles}, "
                    f"avg latency (last 10): {avg_latency:.0f}ms"
                )

        self.results['end_time'] = time.time()
        logger.info(
            f"Sequential processing complete: "
            f"{self.results['total_articles']} successful, "
            f"{self.results['failed_articles']} failed"
        )

    def test_parallel_processing(self, num_articles: int = 100, max_workers: int = 4):
        """
        Test parallel article processing

        Args:
            num_articles: Number of articles to process
            max_workers: Maximum parallel workers (default 4, recommended for LLM)
        """
        logger.info(
            f"Starting parallel processing test: {num_articles} articles, "
            f"{max_workers} workers"
        )
        self.results['start_time'] = time.time()

        headlines = [
            (self.TEST_HEADLINES[i % len(self.TEST_HEADLINES)], i)
            for i in range(num_articles)
        ]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.analyze_headline, headline, article_id): article_id
                for headline, article_id in headlines
            }

            completed = 0
            for future in as_completed(futures):
                result = future.result()

                if result['success']:
                    self.results['latencies'].append(result['latency_ms'])
                    self.results['scores'].append(result['score'])
                    self.results['total_articles'] += 1
                else:
                    self.results['failed_articles'] += 1

                completed += 1
                if completed % 10 == 0:
                    logger.info(f"Progress: {completed}/{num_articles} articles")

        self.results['end_time'] = time.time()
        logger.info(
            f"Parallel processing complete: "
            f"{self.results['total_articles']} successful, "
            f"{self.results['failed_articles']} failed"
        )

    def test_sustained_load(self, duration_seconds: int = 300, rate_limit: int = 10):
        """
        Test sustained processing load over time

        Args:
            duration_seconds: Test duration in seconds
            rate_limit: Target articles per minute
        """
        logger.info(
            f"Starting sustained load test: {duration_seconds}s duration, "
            f"{rate_limit} articles/min target"
        )
        self.results['start_time'] = time.time()

        article_id = 0
        interval = 60 / rate_limit  # seconds between articles

        while (time.time() - self.results['start_time']) < duration_seconds:
            headline = self.TEST_HEADLINES[article_id % len(self.TEST_HEADLINES)]
            result = self.analyze_headline(headline, article_id)

            if result['success']:
                self.results['latencies'].append(result['latency_ms'])
                self.results['scores'].append(result['score'])
                self.results['total_articles'] += 1
            else:
                self.results['failed_articles'] += 1

            article_id += 1

            # Sleep to maintain rate limit
            time.sleep(interval)

        self.results['end_time'] = time.time()
        logger.info(
            f"Sustained load test complete: "
            f"{self.results['total_articles']} articles in "
            f"{duration_seconds}s"
        )

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate performance report

        Returns:
            Performance metrics dictionary
        """
        duration = self.results['end_time'] - self.results['start_time']
        throughput = self.results['total_articles'] / duration if duration > 0 else 0

        latencies = self.results['latencies']
        scores = self.results['scores']

        report = {
            'summary': {
                'total_articles': self.results['total_articles'],
                'failed_articles': self.results['failed_articles'],
                'duration_seconds': round(duration, 2),
                'throughput_articles_per_sec': round(throughput, 2),
                'throughput_articles_per_min': round(throughput * 60, 2),
                'success_rate': round(
                    self.results['total_articles'] /
                    (self.results['total_articles'] + self.results['failed_articles']) * 100,
                    2
                ) if (self.results['total_articles'] + self.results['failed_articles']) > 0 else 0
            },
            'latency_ms': {
                'min': round(min(latencies), 2) if latencies else 0,
                'max': round(max(latencies), 2) if latencies else 0,
                'mean': round(statistics.mean(latencies), 2) if latencies else 0,
                'median': round(statistics.median(latencies), 2) if latencies else 0,
                'p95': round(
                    statistics.quantiles(latencies, n=20)[18], 2
                ) if len(latencies) > 20 else 0,
                'p99': round(
                    statistics.quantiles(latencies, n=100)[98], 2
                ) if len(latencies) > 100 else 0,
            },
            'sentiment_distribution': {
                'mean_score': round(statistics.mean(scores), 3) if scores else 0,
                'median_score': round(statistics.median(scores), 3) if scores else 0,
                'min_score': round(min(scores), 3) if scores else 0,
                'max_score': round(max(scores), 3) if scores else 0,
                'bullish_count': sum(1 for s in scores if s > 0.3),
                'bearish_count': sum(1 for s in scores if s < -0.3),
                'neutral_count': sum(1 for s in scores if -0.3 <= s <= 0.3),
            }
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("SENTIMENT ANALYSIS LOAD TEST REPORT")
        print("=" * 80)
        print("\nSUMMARY:")
        print(f"  Total Articles:     {report['summary']['total_articles']:,}")
        print(f"  Failed Articles:    {report['summary']['failed_articles']:,}")
        print(f"  Duration:           {report['summary']['duration_seconds']:.2f}s")
        print(f"  Throughput:         {report['summary']['throughput_articles_per_sec']:.2f} articles/s")
        print(f"                      {report['summary']['throughput_articles_per_min']:.2f} articles/min")
        print(f"  Success Rate:       {report['summary']['success_rate']:.2f}%")

        print("\nLATENCY (ms):")
        print(f"  Min:                {report['latency_ms']['min']:.2f}")
        print(f"  Mean:               {report['latency_ms']['mean']:.2f}")
        print(f"  Median:             {report['latency_ms']['median']:.2f}")
        print(f"  P95:                {report['latency_ms']['p95']:.2f}")
        print(f"  P99:                {report['latency_ms']['p99']:.2f}")
        print(f"  Max:                {report['latency_ms']['max']:.2f}")

        print("\nSENTIMENT DISTRIBUTION:")
        print(f"  Mean Score:         {report['sentiment_distribution']['mean_score']:+.3f}")
        print(f"  Score Range:        [{report['sentiment_distribution']['min_score']:+.3f}, "
              f"{report['sentiment_distribution']['max_score']:+.3f}]")
        print(f"  Bullish (>0.3):     {report['sentiment_distribution']['bullish_count']}")
        print(f"  Neutral:            {report['sentiment_distribution']['neutral_count']}")
        print(f"  Bearish (<-0.3):    {report['sentiment_distribution']['bearish_count']}")

        print("\n" + "=" * 80)

    def save_report(self, report: Dict[str, Any], filename: str = 'sentiment_load_test_report.json'):
        """
        Save report to file

        Args:
            report: Report dictionary
            filename: Output filename
        """
        filepath = os.path.join('tests', 'stress_tests', filename)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {filepath}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Sentiment Analysis Load Testing')
    parser.add_argument('--articles', type=int, default=100,
                        help='Number of articles to process')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of parallel workers (recommend ≤4 for LLM)')
    parser.add_argument('--mode', choices=['sequential', 'parallel', 'sustained'], default='parallel',
                        help='Test mode')
    parser.add_argument('--duration', type=int, default=300,
                        help='Duration for sustained test (seconds)')
    parser.add_argument('--rate', type=int, default=10,
                        help='Article rate for sustained test (per minute)')

    args = parser.parse_args()

    tester = SentimentLoadTest()

    try:
        tester.setup()

        # Run test based on mode
        if args.mode == 'sequential':
            tester.test_sequential_processing(num_articles=args.articles)
        elif args.mode == 'parallel':
            tester.test_parallel_processing(num_articles=args.articles, max_workers=args.workers)
        else:  # sustained
            tester.test_sustained_load(duration_seconds=args.duration, rate_limit=args.rate)

        # Generate and display report
        report = tester.generate_report()
        tester.print_report(report)
        tester.save_report(report)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        logger.info("Test complete")


if __name__ == "__main__":
    main()
