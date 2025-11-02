#!/usr/bin/env python3
"""
VoidCat RDC - CryptoBoy Trading System
API Key Verification Script
Author: Wykeve Freeman (Sorrow Eternal)
Organization: VoidCat RDC

This script validates API credentials and configuration without exposing sensitive data.
"""

import os
import sys
from pathlib import Path

import ccxt
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Initialize colorama for colored console output
init(autoreset=True)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(text):
    """Print formatted header"""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(80)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def print_success(text):
    """Print success message"""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text):
    """Print error message"""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_warning(text):
    """Print warning message"""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")


def print_info(text):
    """Print info message"""
    print(f"{Fore.BLUE}ℹ {text}{Style.RESET_ALL}")


def mask_key(key, visible_chars=4):
    """Mask API key for secure display"""
    if not key or len(key) <= visible_chars * 2:
        return "***INVALID***"
    return f"{key[:visible_chars]}...{key[-visible_chars:]}"


def verify_env_file():
    """Verify .env file exists and is loaded"""
    print_header("VoidCat RDC - API Key Verification")

    env_path = project_root / ".env"

    if not env_path.exists():
        print_error(f".env file not found at: {env_path}")
        print_info("Please copy .env.example to .env and configure your API keys")
        return False

    print_success(f".env file found at: {env_path}")

    # Load environment variables
    load_dotenv(env_path)
    print_success("Environment variables loaded")

    return True


def verify_binance_credentials():
    """Verify Binance API credentials"""
    print_header("Binance API Credentials")

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    # Check if credentials exist
    if not api_key or api_key == "your_binance_api_key_here":
        print_error("BINANCE_API_KEY not configured")
        return False

    if not api_secret or api_secret == "your_binance_api_secret_here":
        print_error("BINANCE_API_SECRET not configured")
        return False

    print_success(f"API Key: {mask_key(api_key)}")
    print_success(f"API Secret: {mask_key(api_secret)}")

    # Test connection
    print_info("Testing Binance API connection...")

    try:
        exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )

        # Test API by fetching account info
        balance = exchange.fetch_balance()

        print_success("Successfully connected to Binance API")
        print_info(f"Account type: {balance.get('info', {}).get('accountType', 'Unknown')}")

        # Check if account can trade
        if balance.get("info", {}).get("canTrade", False):
            print_success("Account has trading permissions")
        else:
            print_warning("Account does NOT have trading permissions")

        # Display available balances (non-zero only)
        print_info("\nNon-zero balances:")
        for currency, amounts in balance.items():
            if currency not in ["info", "free", "used", "total"]:
                continue
            if isinstance(amounts, dict):
                for coin, amount in amounts.items():
                    if amount > 0:
                        print(f"  {coin}: {amount}")

        return True

    except ccxt.AuthenticationError as e:
        print_error(f"Authentication failed: {e}")
        print_warning("Please verify your API key and secret are correct")
        return False
    except ccxt.NetworkError as e:
        print_error(f"Network error: {e}")
        print_warning("Please check your internet connection")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def verify_telegram_config():
    """Verify Telegram bot configuration"""
    print_header("Telegram Bot Configuration")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or bot_token == "your_telegram_bot_token_here":
        print_warning("TELEGRAM_BOT_TOKEN not configured (optional)")
        print_info("Telegram notifications will be disabled")
        return False

    if not chat_id or chat_id == "your_telegram_chat_id_here":
        print_warning("TELEGRAM_CHAT_ID not configured (optional)")
        print_info("Telegram notifications will be disabled")
        return False

    print_success(f"Bot Token: {mask_key(bot_token)}")
    print_success(f"Chat ID: {chat_id}")

    # Test Telegram connection
    print_info("Testing Telegram bot connection...")

    try:
        import requests

        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                print_success(f"Telegram bot connected: @{bot_info['result']['username']}")
                return True
            else:
                print_error("Telegram bot authentication failed")
                return False
        else:
            print_error(f"Telegram API error: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Telegram connection error: {e}")
        return False


def verify_ollama_config():
    """Verify Ollama LLM configuration"""
    print_header("Ollama LLM Configuration")

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral:7b")

    print_success(f"Ollama Host: {ollama_host}")
    print_success(f"Ollama Model: {ollama_model}")

    # Test Ollama connection
    print_info("Testing Ollama connection...")

    try:
        import requests

        # Check if Ollama is running
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get("models", [])
            print_success("Ollama service is running")

            # Check if specified model is available
            model_names = [m["name"] for m in models]
            if ollama_model in model_names:
                print_success(f"Model '{ollama_model}' is available")
                return True
            else:
                print_warning(f"Model '{ollama_model}' not found")
                print_info(f"Available models: {', '.join(model_names)}")
                print_info(f"Run: docker exec -it trading-bot-ollama ollama pull {ollama_model}")
                return False
        else:
            print_error(f"Ollama API error: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to Ollama service")
        print_info("Start Ollama with: docker-compose up -d ollama")
        return False
    except Exception as e:
        print_error(f"Ollama connection error: {e}")
        return False


def verify_trading_config():
    """Verify trading configuration"""
    print_header("Trading Configuration")

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    stake_currency = os.getenv("STAKE_CURRENCY", "USDT")
    stake_amount = os.getenv("STAKE_AMOUNT", "50")
    max_open_trades = os.getenv("MAX_OPEN_TRADES", "3")

    if dry_run:
        print_warning("DRY_RUN mode is ENABLED (paper trading)")
        print_info("No real trades will be executed")
    else:
        print_error("DRY_RUN mode is DISABLED - LIVE TRADING ENABLED")
        print_warning("⚠⚠⚠ REAL MONEY AT RISK ⚠⚠⚠")

    print_success(f"Stake Currency: {stake_currency}")
    print_success(f"Stake Amount: {stake_amount} {stake_currency}")
    print_success(f"Max Open Trades: {max_open_trades}")

    # Risk management
    stop_loss = os.getenv("STOP_LOSS_PERCENTAGE", "3.0")
    take_profit = os.getenv("TAKE_PROFIT_PERCENTAGE", "5.0")
    risk_per_trade = os.getenv("RISK_PER_TRADE_PERCENTAGE", "1.0")

    print_success(f"Stop Loss: {stop_loss}%")
    print_success(f"Take Profit: {take_profit}%")
    print_success(f"Risk Per Trade: {risk_per_trade}%")

    return True


def verify_directory_structure():
    """Verify required directories exist"""
    print_header("Directory Structure")

    required_dirs = [
        "data",
        "logs",
        "backtest/backtest_reports",
        "data/cache",
        "data/ohlcv_data",
        "data/news_data",
    ]

    all_exist = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print_success(f"Directory exists: {dir_path}")
        else:
            print_warning(f"Creating directory: {dir_path}")
            full_path.mkdir(parents=True, exist_ok=True)
            print_success(f"Created: {dir_path}")

    return all_exist


def main():
    """Main verification routine"""
    print(f"{Fore.MAGENTA}")
    print(
        r"""
    ╦  ╦┌─┐┬┌┬┐╔═╗┌─┐┌┬┐  ╦═╗╔╦╗╔═╗
    ╚╗╔╝│ │││ ││  ╠═╣ │   ╠╦╝ ║║║
     ╚╝ └─┘┴─┴┘╚═╝╩ ╩ ┴   ╩╚══╩╝╚═╝
    """
    )
    print(f"{Style.RESET_ALL}")
    print(f"{Fore.CYAN}CryptoBoy Trading System - API Key Verification{Style.RESET_ALL}")
    print(f"{Fore.CYAN}VoidCat RDC - Wykeve Freeman (Sorrow Eternal){Style.RESET_ALL}\n")

    # Verification steps
    results = {
        "Environment File": verify_env_file(),
        "Directory Structure": verify_directory_structure(),
        "Binance API": False,
        "Telegram Bot": False,
        "Ollama LLM": False,
        "Trading Config": False,
    }

    if results["Environment File"]:
        results["Binance API"] = verify_binance_credentials()
        results["Telegram Bot"] = verify_telegram_config()
        results["Ollama LLM"] = verify_ollama_config()
        results["Trading Config"] = verify_trading_config()

    # Summary
    print_header("Verification Summary")

    for component, status in results.items():
        if status:
            print_success(f"{component}: PASSED")
        else:
            if component in ["Telegram Bot", "Ollama LLM"]:
                print_warning(f"{component}: OPTIONAL (not configured)")
            else:
                print_error(f"{component}: FAILED")

    # Overall status
    critical_components = ["Environment File", "Binance API", "Trading Config"]
    critical_passed = all(results[c] for c in critical_components)

    print()
    if critical_passed:
        print_success("✓ All critical components verified successfully")
        print_info("You can proceed with trading setup")

        if not results["Telegram Bot"]:
            print_warning("Consider configuring Telegram for trade notifications")

        if not results["Ollama LLM"]:
            print_warning("Ollama LLM required for sentiment analysis")
            print_info("Start Ollama: docker-compose up -d ollama")

        return 0
    else:
        print_error("✗ Critical components failed verification")
        print_info("Please fix the errors above before proceeding")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Verification cancelled by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
