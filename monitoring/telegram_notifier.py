"""
Telegram Notifier - Sends trading alerts via Telegram
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to Telegram"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram notifier initialized")

    def send_message(self, message: str, parse_mode: str = "Markdown", disable_notification: bool = False) -> bool:
        """
        Send a message to Telegram

        Args:
            message: Message text
            parse_mode: Parse mode (Markdown or HTML)
            disable_notification: Send silently

        Returns:
            True if successful
        """
        if not self.enabled:
            logger.debug(f"Telegram disabled. Would send: {message}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification,
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.debug("Telegram message sent successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_trade_notification(
        self,
        action: str,
        pair: str,
        price: float,
        amount: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        sentiment_score: Optional[float] = None,
    ) -> bool:
        """
        Send trade notification

        Args:
            action: Trade action (BUY/SELL)
            pair: Trading pair
            price: Entry/exit price
            amount: Trade amount
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            sentiment_score: Sentiment score (optional)

        Returns:
            True if successful
        """
        emoji = "📈" if action.upper() == "BUY" else "📉"

        message = f"{emoji} *{action.upper()}* {pair}\n\n"
        message += f"💰 Price: ${price:,.2f}\n"
        message += f"📊 Amount: {amount:.6f}\n"
        message += f"💵 Value: ${price * amount:,.2f}\n"

        if stop_loss:
            loss_pct = ((stop_loss - price) / price) * 100
            message += f"🛑 Stop Loss: ${stop_loss:,.2f} ({loss_pct:.1f}%)\n"

        if take_profit:
            profit_pct = ((take_profit - price) / price) * 100
            message += f"🎯 Take Profit: ${take_profit:,.2f} ({profit_pct:.1f}%)\n"

        if sentiment_score is not None:
            sentiment_emoji = "😊" if sentiment_score > 0.3 else "😐" if sentiment_score > -0.3 else "😟"
            message += f"\n{sentiment_emoji} Sentiment: {sentiment_score:+.2f}\n"

        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message)

    def send_position_close(
        self,
        pair: str,
        entry_price: float,
        exit_price: float,
        amount: float,
        profit_pct: float,
        profit_amount: float,
        duration: str,
    ) -> bool:
        """
        Send position close notification

        Args:
            pair: Trading pair
            entry_price: Entry price
            exit_price: Exit price
            amount: Position amount
            profit_pct: Profit percentage
            profit_amount: Profit amount
            duration: Trade duration

        Returns:
            True if successful
        """
        emoji = "✅" if profit_pct > 0 else "❌"

        message = f"{emoji} *Position Closed* {pair}\n\n"
        message += f"📥 Entry: ${entry_price:,.2f}\n"
        message += f"📤 Exit: ${exit_price:,.2f}\n"
        message += f"📊 Amount: {amount:.6f}\n"
        message += f"⏱ Duration: {duration}\n\n"
        message += f"{'💰' if profit_pct > 0 else '💸'} P&L: {profit_pct:+.2f}% (${profit_amount:+,.2f})\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message)

    def send_portfolio_update(
        self, total_value: float, daily_pnl: float, daily_pnl_pct: float, open_positions: int, today_trades: int
    ) -> bool:
        """
        Send portfolio summary

        Args:
            total_value: Total portfolio value
            daily_pnl: Daily profit/loss
            daily_pnl_pct: Daily profit/loss percentage
            open_positions: Number of open positions
            today_trades: Number of trades today

        Returns:
            True if successful
        """
        emoji = "📊"
        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"

        message = f"{emoji} *Portfolio Summary*\n\n"
        message += f"💰 Total Value: ${total_value:,.2f}\n"
        message += f"{pnl_emoji} Daily P&L: {daily_pnl_pct:+.2f}% (${daily_pnl:+,.2f})\n"
        message += f"📍 Open Positions: {open_positions}\n"
        message += f"📝 Today's Trades: {today_trades}\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message, disable_notification=True)

    def send_risk_alert(self, alert_type: str, message_text: str, severity: str = "warning") -> bool:
        """
        Send risk management alert

        Args:
            alert_type: Type of alert
            message_text: Alert message
            severity: Severity level (info/warning/critical)

        Returns:
            True if successful
        """
        emoji_map = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}

        emoji = emoji_map.get(severity.lower(), "⚠️")

        message = f"{emoji} *Risk Alert: {alert_type}*\n\n"
        message += message_text
        message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Don't disable notifications for critical alerts
        disable_notif = severity.lower() != "critical"

        return self.send_message(message, disable_notification=disable_notif)

    def send_error_alert(self, error_type: str, error_message: str) -> bool:
        """
        Send error notification

        Args:
            error_type: Type of error
            error_message: Error message

        Returns:
            True if successful
        """
        message = f"🚨 *Error: {error_type}*\n\n"
        message += f"```\n{error_message}\n```\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message)

    def send_system_status(self, status: str, details: Optional[Dict] = None) -> bool:
        """
        Send system status update

        Args:
            status: Status message
            details: Additional details (optional)

        Returns:
            True if successful
        """
        emoji = "🤖"

        message = f"{emoji} *System Status*\n\n"
        message += f"{status}\n"

        if details:
            message += "\n*Details:*\n"
            for key, value in details.items():
                message += f"• {key}: {value}\n"

        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message, disable_notification=True)

    def test_connection(self) -> bool:
        """
        Test Telegram connection

        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("Telegram is not enabled")
            return False

        test_message = (
            "🧪 Testing Telegram connection...\n\n" "If you receive this message, the bot is configured correctly!"
        )

        if self.send_message(test_message):
            logger.info("Telegram connection test successful")
            return True
        else:
            logger.error("Telegram connection test failed")
            return False


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    notifier = TelegramNotifier()

    if notifier.enabled:
        # Test connection
        if notifier.test_connection():
            print("✓ Telegram notifier is working!")

            # Test trade notification
            print("\nSending test trade notification...")
            notifier.send_trade_notification(
                action="BUY",
                pair="BTC/USDT",
                price=50000.0,
                amount=0.002,
                stop_loss=48500.0,
                take_profit=52500.0,
                sentiment_score=0.75,
            )

            # Test portfolio update
            print("Sending test portfolio update...")
            notifier.send_portfolio_update(
                total_value=10500.0, daily_pnl=500.0, daily_pnl_pct=5.0, open_positions=2, today_trades=3
            )

            # Test risk alert
            print("Sending test risk alert...")
            notifier.send_risk_alert(
                alert_type="Daily Loss Limit",
                message_text="Daily loss approaching 5% limit. Current: 4.2%",
                severity="warning",
            )

            print("\n✓ All test notifications sent!")
        else:
            print("✗ Telegram connection failed")
    else:
        print("✗ Telegram credentials not configured")
        print("\nTo configure Telegram:")
        print("1. Create a bot via @BotFather on Telegram")
        print("2. Get your chat ID via @userinfobot")
        print("3. Set environment variables:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        print("   TELEGRAM_CHAT_ID=your_chat_id_here")
