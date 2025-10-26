"""
Risk Management Framework - Controls trading risk
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk parameters and limits"""

    def __init__(
        self,
        config_path: str = "risk/risk_parameters.json",
        log_dir: str = "logs"
    ):
        """
        Initialize risk manager

        Args:
            config_path: Path to risk parameters config
            log_dir: Directory for risk event logs
        """
        self.config_path = Path(config_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.risk_events_file = self.log_dir / "risk_events.json"

        # Load or create default config
        self.config = self._load_config()

        # Track daily trading activity
        self.daily_trades = []
        self.current_positions = {}

    def _load_config(self) -> Dict:
        """Load risk parameters from config file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded risk config from {self.config_path}")
                return config
        else:
            # Default risk parameters
            config = {
                "stop_loss_percentage": 3.0,
                "take_profit_percentage": 5.0,
                "trailing_stop_percentage": 1.0,
                "risk_per_trade_percentage": 1.0,
                "max_portfolio_risk_percentage": 5.0,
                "max_daily_trades": 10,
                "max_open_positions": 3,
                "max_position_size_percentage": 30.0,
                "min_correlation_threshold": 0.7,
                "max_drawdown_limit": 15.0,
                "daily_loss_limit": 5.0
            }

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created default risk config at {self.config_path}")
            return config

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk parameters

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price
            risk_per_trade: Risk per trade percentage (optional)

        Returns:
            Position size in base currency
        """
        if risk_per_trade is None:
            risk_per_trade = self.config['risk_per_trade_percentage']

        # Calculate risk amount in portfolio currency
        risk_amount = portfolio_value * (risk_per_trade / 100)

        # Calculate price difference
        price_diff = abs(entry_price - stop_loss_price)

        if price_diff == 0:
            logger.warning("Stop loss price equals entry price")
            return 0.0

        # Calculate position size
        position_size = risk_amount / price_diff

        # Apply max position size limit
        max_position_value = portfolio_value * (self.config['max_position_size_percentage'] / 100)
        max_position_size = max_position_value / entry_price

        position_size = min(position_size, max_position_size)

        logger.debug(f"Calculated position size: {position_size:.4f} at ${entry_price:.2f}")
        return position_size

    def validate_risk_parameters(
        self,
        pair: str,
        entry_price: float,
        position_size: float,
        portfolio_value: float
    ) -> Dict:
        """
        Validate if a trade meets risk parameters

        Args:
            pair: Trading pair
            entry_price: Entry price
            position_size: Position size
            portfolio_value: Total portfolio value

        Returns:
            Dictionary with validation results
        """
        validation = {
            'approved': True,
            'warnings': [],
            'rejections': []
        }

        # Check max open positions
        if len(self.current_positions) >= self.config['max_open_positions']:
            validation['approved'] = False
            validation['rejections'].append(
                f"Max open positions ({self.config['max_open_positions']}) reached"
            )

        # Check daily trade limit
        today = datetime.now().date()
        today_trades = [t for t in self.daily_trades if t['date'].date() == today]
        if len(today_trades) >= self.config['max_daily_trades']:
            validation['approved'] = False
            validation['rejections'].append(
                f"Daily trade limit ({self.config['max_daily_trades']}) reached"
            )

        # Check position size
        position_value = entry_price * position_size
        position_pct = (position_value / portfolio_value) * 100
        if position_pct > self.config['max_position_size_percentage']:
            validation['approved'] = False
            validation['rejections'].append(
                f"Position size {position_pct:.1f}% exceeds limit "
                f"({self.config['max_position_size_percentage']}%)"
            )

        # Check correlation (if we have multiple positions)
        if len(self.current_positions) > 0:
            correlation_warning = self._check_correlation(pair)
            if correlation_warning:
                validation['warnings'].append(correlation_warning)

        return validation

    def _check_correlation(self, new_pair: str) -> Optional[str]:
        """
        Check correlation between new pair and existing positions

        Args:
            new_pair: New trading pair to check

        Returns:
            Warning message if highly correlated, None otherwise
        """
        # Simplified correlation check
        # In production, you'd calculate actual price correlations

        existing_pairs = list(self.current_positions.keys())

        # Check if trading same base or quote currency
        new_base = new_pair.split('/')[0]
        new_quote = new_pair.split('/')[1]

        highly_correlated = []
        for existing_pair in existing_pairs:
            existing_base = existing_pair.split('/')[0]
            existing_quote = existing_pair.split('/')[1]

            if (new_base == existing_base or
                new_quote == existing_quote and new_base != existing_base):
                highly_correlated.append(existing_pair)

        if highly_correlated:
            return (f"High correlation detected between {new_pair} and "
                   f"{', '.join(highly_correlated)}")

        return None

    def enforce_stop_loss(
        self,
        pair: str,
        entry_price: float,
        current_price: float,
        position_size: float
    ) -> Dict:
        """
        Check if stop loss should be triggered

        Args:
            pair: Trading pair
            entry_price: Entry price
            current_price: Current price
            position_size: Position size

        Returns:
            Dictionary with stop loss decision
        """
        loss_pct = ((current_price - entry_price) / entry_price) * 100
        stop_loss_pct = -self.config['stop_loss_percentage']

        result = {
            'trigger': False,
            'loss_pct': loss_pct,
            'stop_loss_pct': stop_loss_pct,
            'reason': None
        }

        if loss_pct <= stop_loss_pct:
            result['trigger'] = True
            result['reason'] = f"Stop loss triggered: {loss_pct:.2f}% loss"
            logger.warning(f"Stop loss triggered for {pair}: {loss_pct:.2f}%")

            # Log risk event
            self._log_risk_event({
                'type': 'stop_loss',
                'pair': pair,
                'entry_price': entry_price,
                'exit_price': current_price,
                'loss_pct': loss_pct,
                'timestamp': datetime.now().isoformat()
            })

        return result

    def check_daily_loss_limit(
        self,
        daily_pnl: float,
        portfolio_value: float
    ) -> Dict:
        """
        Check if daily loss limit is breached

        Args:
            daily_pnl: Daily profit/loss
            portfolio_value: Portfolio value

        Returns:
            Dictionary with limit check results
        """
        daily_loss_pct = (daily_pnl / portfolio_value) * 100
        limit_pct = -self.config['daily_loss_limit']

        result = {
            'limit_breached': False,
            'daily_loss_pct': daily_loss_pct,
            'limit_pct': limit_pct,
            'action': None
        }

        if daily_loss_pct <= limit_pct:
            result['limit_breached'] = True
            result['action'] = 'STOP_TRADING'
            logger.critical(
                f"Daily loss limit breached: {daily_loss_pct:.2f}% "
                f"(limit: {limit_pct:.2f}%)"
            )

            # Log risk event
            self._log_risk_event({
                'type': 'daily_loss_limit',
                'daily_pnl': daily_pnl,
                'daily_loss_pct': daily_loss_pct,
                'limit_pct': limit_pct,
                'timestamp': datetime.now().isoformat()
            })

        return result

    def track_trade(
        self,
        pair: str,
        entry_price: float,
        position_size: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Track a new trade

        Args:
            pair: Trading pair
            entry_price: Entry price
            position_size: Position size
            timestamp: Trade timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        trade = {
            'pair': pair,
            'entry_price': entry_price,
            'position_size': position_size,
            'date': timestamp
        }

        self.daily_trades.append(trade)
        self.current_positions[pair] = trade

        logger.info(f"Tracking new trade: {pair} @ {entry_price}")

    def close_position(self, pair: str, exit_price: float):
        """
        Close a tracked position

        Args:
            pair: Trading pair
            exit_price: Exit price
        """
        if pair in self.current_positions:
            position = self.current_positions[pair]
            pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100

            logger.info(f"Closing position: {pair} @ {exit_price} ({pnl_pct:+.2f}%)")

            del self.current_positions[pair]
        else:
            logger.warning(f"Attempted to close unknown position: {pair}")

    def _log_risk_event(self, event: Dict):
        """
        Log a risk management event

        Args:
            event: Event dictionary
        """
        events = []
        if self.risk_events_file.exists():
            with open(self.risk_events_file, 'r') as f:
                events = json.load(f)

        events.append(event)

        with open(self.risk_events_file, 'w') as f:
            json.dump(events, f, indent=2)

        logger.info(f"Logged risk event: {event['type']}")

    def get_risk_summary(self) -> Dict:
        """
        Get current risk summary

        Returns:
            Dictionary with risk summary
        """
        today = datetime.now().date()
        today_trades = [t for t in self.daily_trades if t['date'].date() == today]

        summary = {
            'open_positions': len(self.current_positions),
            'max_open_positions': self.config['max_open_positions'],
            'daily_trades': len(today_trades),
            'max_daily_trades': self.config['max_daily_trades'],
            'stop_loss_percentage': self.config['stop_loss_percentage'],
            'risk_per_trade_percentage': self.config['risk_per_trade_percentage'],
            'positions': list(self.current_positions.keys())
        }

        return summary


if __name__ == "__main__":
    # Example usage
    risk_manager = RiskManager()

    # Get risk summary
    summary = risk_manager.get_risk_summary()
    print("Risk Summary:")
    print(json.dumps(summary, indent=2))

    # Example: Calculate position size
    portfolio_value = 10000  # $10,000
    entry_price = 50000  # $50,000 BTC
    stop_loss_price = 48500  # $48,500 (3% stop loss)

    position_size = risk_manager.calculate_position_size(
        portfolio_value,
        entry_price,
        stop_loss_price
    )

    print(f"\nPosition size for BTC/USDT: {position_size:.6f} BTC")
    print(f"Position value: ${position_size * entry_price:.2f}")

    # Validate the trade
    validation = risk_manager.validate_risk_parameters(
        'BTC/USDT',
        entry_price,
        position_size,
        portfolio_value
    )

    print(f"\nTrade validation: {'APPROVED' if validation['approved'] else 'REJECTED'}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    if validation['rejections']:
        print(f"Rejections: {validation['rejections']}")
