"""
Backtesting Script - Run and analyze strategy backtests
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BacktestRunner:
    """Manages backtesting operations"""

    def __init__(
        self,
        config_path: str = "config/backtest_config.json",
        strategy_name: str = "LLMSentimentStrategy",
        data_dir: str = "user_data/data/binance",
    ):
        """
        Initialize backtest runner

        Args:
            config_path: Path to Freqtrade config file
            strategy_name: Name of the strategy to backtest
            data_dir: Directory containing market data
        """
        self.config_path = Path(config_path)
        self.strategy_name = strategy_name
        self.data_dir = Path(data_dir)
        self.results_dir = Path("backtest/backtest_reports")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def download_data(self, pairs: list = None, timeframe: str = "1h", days: int = 365) -> bool:
        """
        Download historical data using Freqtrade

        Args:
            pairs: List of trading pairs
            timeframe: Candle timeframe
            days: Number of days to download

        Returns:
            True if successful
        """
        if pairs is None:
            pairs = ["BTC/USDT", "ETH/USDT"]

        logger.info(f"Downloading {days} days of data for {pairs}")

        try:
            cmd = (
                ["freqtrade", "download-data", "--config", str(self.config_path), "--pairs"]
                + pairs
                + ["--timeframes", timeframe, "--days", str(days), "--exchange", "binance"]
            )

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info("Data download completed")
            logger.debug(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error downloading data: {e}")
            logger.error(e.stderr)
            return False

    def run_backtest(self, timerange: Optional[str] = None, timeframe: str = "1h") -> Optional[Dict]:
        """
        Run backtest

        Args:
            timerange: Time range in format YYYYMMDD-YYYYMMDD
            timeframe: Candle timeframe

        Returns:
            Backtest results dictionary
        """
        logger.info(f"Running backtest for {self.strategy_name}")

        try:
            cmd = [
                "freqtrade",
                "backtesting",
                "--config",
                str(self.config_path),
                "--strategy",
                self.strategy_name,
                "--timeframe",
                timeframe,
                "--export",
                "trades",
            ]

            if timerange:
                cmd.extend(["--timerange", timerange])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info("Backtest completed")
            logger.info(result.stdout)

            # Parse results
            return self._parse_backtest_results()

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running backtest: {e}")
            logger.error(e.stderr)
            return None

    def _parse_backtest_results(self) -> Optional[Dict]:
        """
        Parse backtest results from JSON file

        Returns:
            Dictionary with backtest results
        """
        try:
            # Find the most recent backtest result file
            backtest_results_dir = Path("user_data/backtest_results")
            if not backtest_results_dir.exists():
                logger.warning("Backtest results directory not found")
                return None

            result_files = list(backtest_results_dir.glob("backtest-result-*.json"))
            if not result_files:
                logger.warning("No backtest result files found")
                return None

            latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Reading results from {latest_file}")

            with open(latest_file, "r") as f:
                results = json.load(f)

            return results

        except Exception as e:
            logger.error(f"Error parsing backtest results: {e}")
            return None

    def calculate_metrics(self, results: Dict) -> Dict:
        """
        Calculate performance metrics from backtest results

        Args:
            results: Backtest results dictionary

        Returns:
            Dictionary with calculated metrics
        """
        if not results or "strategy" not in results:
            logger.error("Invalid results format")
            return {}

        strategy_results = results["strategy"].get(self.strategy_name, {})

        metrics = {
            "total_trades": strategy_results.get("total_trades", 0),
            "winning_trades": strategy_results.get("wins", 0),
            "losing_trades": strategy_results.get("losses", 0),
            "draws": strategy_results.get("draws", 0),
            "win_rate": strategy_results.get("winrate", 0),
            "profit_total": strategy_results.get("profit_total", 0),
            "profit_total_pct": strategy_results.get("profit_total_abs", 0),
            "max_drawdown": strategy_results.get("max_drawdown", 0),
            "max_drawdown_pct": strategy_results.get("max_drawdown_pct", 0),
            "sharpe_ratio": self._calculate_sharpe_ratio(results),
            "sortino_ratio": self._calculate_sortino_ratio(results),
            "profit_factor": self._calculate_profit_factor(results),
            "avg_profit": strategy_results.get("profit_mean", 0),
            "best_trade": strategy_results.get("best_pair", {}).get("profit_sum", 0),
            "worst_trade": strategy_results.get("worst_pair", {}).get("profit_sum", 0),
            "duration_avg": strategy_results.get("duration_avg", "0:00:00"),
        }

        return metrics

    def _calculate_sharpe_ratio(self, results: Dict) -> float:
        """Calculate Sharpe Ratio"""
        try:
            # This is a simplified calculation
            # In production, you'd want daily/hourly returns
            strategy_results = results["strategy"].get(self.strategy_name, {})
            avg_profit = strategy_results.get("profit_mean", 0)
            std_profit = strategy_results.get("profit_std", 1)

            if std_profit == 0:
                return 0.0

            # Annualized Sharpe (assuming 365 trading days)
            sharpe = (avg_profit / std_profit) * (365**0.5)
            return round(sharpe, 2)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    def _calculate_sortino_ratio(self, results: Dict) -> float:
        """Calculate Sortino Ratio"""
        try:
            # Similar to Sharpe but only considers downside volatility
            # This is a simplified calculation
            strategy_results = results["strategy"].get(self.strategy_name, {})
            avg_profit = strategy_results.get("profit_mean", 0)

            # Approximate downside deviation
            std_profit = strategy_results.get("profit_std", 1)
            downside_dev = std_profit * 0.7  # Rough approximation

            if downside_dev == 0:
                return 0.0

            sortino = (avg_profit / downside_dev) * (365**0.5)
            return round(sortino, 2)

        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0

    def _calculate_profit_factor(self, results: Dict) -> float:
        """Calculate Profit Factor"""
        try:
            strategy_results = results["strategy"].get(self.strategy_name, {})

            wins = strategy_results.get("wins", 0)
            losses = strategy_results.get("losses", 0)
            avg_win = strategy_results.get("profit_mean_winners", 0)
            avg_loss = abs(strategy_results.get("profit_mean_losers", 0))

            gross_profit = wins * avg_win
            gross_loss = losses * avg_loss

            if gross_loss == 0:
                return 0.0

            profit_factor = gross_profit / gross_loss
            return round(profit_factor, 2)

        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return 0.0

    def validate_metrics_threshold(self, metrics: Dict) -> Dict:
        """
        Validate metrics against target thresholds

        Args:
            metrics: Calculated metrics

        Returns:
            Dictionary with validation results
        """
        thresholds = {"sharpe_ratio": 1.0, "max_drawdown_pct": 20.0, "win_rate": 50.0, "profit_factor": 1.5}

        validation = {"passed": True, "checks": {}}

        # Sharpe Ratio
        sharpe_ok = metrics.get("sharpe_ratio", 0) >= thresholds["sharpe_ratio"]
        validation["checks"]["sharpe_ratio"] = {
            "value": metrics.get("sharpe_ratio", 0),
            "threshold": thresholds["sharpe_ratio"],
            "passed": sharpe_ok,
        }
        if not sharpe_ok:
            validation["passed"] = False

        # Max Drawdown
        drawdown_ok = abs(metrics.get("max_drawdown_pct", 100)) <= thresholds["max_drawdown_pct"]
        validation["checks"]["max_drawdown"] = {
            "value": abs(metrics.get("max_drawdown_pct", 0)),
            "threshold": thresholds["max_drawdown_pct"],
            "passed": drawdown_ok,
        }
        if not drawdown_ok:
            validation["passed"] = False

        # Win Rate
        winrate_ok = metrics.get("win_rate", 0) >= thresholds["win_rate"]
        validation["checks"]["win_rate"] = {
            "value": metrics.get("win_rate", 0),
            "threshold": thresholds["win_rate"],
            "passed": winrate_ok,
        }
        if not winrate_ok:
            validation["passed"] = False

        # Profit Factor
        pf_ok = metrics.get("profit_factor", 0) >= thresholds["profit_factor"]
        validation["checks"]["profit_factor"] = {
            "value": metrics.get("profit_factor", 0),
            "threshold": thresholds["profit_factor"],
            "passed": pf_ok,
        }
        if not pf_ok:
            validation["passed"] = False

        return validation

    def generate_report(self, metrics: Dict, validation: Dict) -> str:
        """
        Generate backtest report

        Args:
            metrics: Performance metrics
            validation: Validation results

        Returns:
            Report text
        """
        report_lines = [
            "=" * 80,
            "BACKTEST REPORT",
            "=" * 80,
            f"Strategy: {self.strategy_name}",
            f"Generated: {datetime.now()}",
            "",
            "PERFORMANCE METRICS",
            "-" * 80,
            f"Total Trades: {metrics.get('total_trades', 0)}",
            f"Winning Trades: {metrics.get('winning_trades', 0)}",
            f"Losing Trades: {metrics.get('losing_trades', 0)}",
            f"Win Rate: {metrics.get('win_rate', 0):.2f}%",
            "",
            f"Total Profit: {metrics.get('profit_total', 0):.4f} {metrics.get('stake_currency', 'USDT')}",
            f"Total Profit %: {metrics.get('profit_total_pct', 0):.2f}%",
            f"Average Profit: {metrics.get('avg_profit', 0):.2f}%",
            "",
            f"Max Drawdown: {abs(metrics.get('max_drawdown_pct', 0)):.2f}%",
            f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
            f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}",
            f"Profit Factor: {metrics.get('profit_factor', 0):.2f}",
            "",
            f"Average Trade Duration: {metrics.get('duration_avg', 'N/A')}",
            "",
            "VALIDATION RESULTS",
            "-" * 80,
            f"Overall: {'PASSED' if validation.get('passed') else 'FAILED'}",
            "",
        ]

        for check_name, check_data in validation.get("checks", {}).items():
            status = "✓" if check_data["passed"] else "✗"
            report_lines.append(
                f"{status} {check_name}: {check_data['value']:.2f} " f"(threshold: {check_data['threshold']:.2f})"
            )

        report_lines.append("\n" + "=" * 80)

        report_text = "\n".join(report_lines)

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"backtest_report_{timestamp}.txt"
        with open(report_path, "w") as f:
            f.write(report_text)

        logger.info(f"Report saved to {report_path}")
        return report_text


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    runner = BacktestRunner()

    # Download data
    logger.info("Step 1: Downloading historical data...")
    if runner.download_data(days=365):
        logger.info("Data download successful")

        # Run backtest
        logger.info("\nStep 2: Running backtest...")
        results = runner.run_backtest()

        if results:
            # Calculate metrics
            logger.info("\nStep 3: Calculating metrics...")
            metrics = runner.calculate_metrics(results)

            # Validate metrics
            logger.info("\nStep 4: Validating metrics...")
            validation = runner.validate_metrics_threshold(metrics)

            # Generate report
            logger.info("\nStep 5: Generating report...")
            report = runner.generate_report(metrics, validation)

            print("\n" + report)

            if validation["passed"]:
                print("\n✓ Strategy passed all validation thresholds!")
            else:
                print("\n✗ Strategy failed validation. Review metrics and adjust parameters.")
        else:
            logger.error("Backtest failed")
    else:
        logger.error("Data download failed")
