#!/usr/bin/env python3
"""
VoidCat RDC - CryptoBoy Trading System
Quick Configuration Reference
Author: Wykeve Freeman (Sorrow Eternal)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def mask_key(key, visible=4):
    """Mask sensitive keys"""
    if not key or len(key) <= visible * 2:
        return "***NOT_SET***"
    return f"{key[:visible]}...{key[-visible:]}"


def print_config():
    """Print current configuration"""

    print(
        """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VoidCat RDC - CryptoBoy Configuration                     ║
║                      Quick Reference Card - v1.0.0                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    )

    # Exchange Configuration
    print("📊 EXCHANGE CONFIGURATION")
    print("─" * 80)
    print(f"  API Key:     {mask_key(os.getenv('BINANCE_API_KEY'))}")
    print(f"  API Secret:  {mask_key(os.getenv('BINANCE_API_SECRET'))}")
    print(f"  Use Testnet: {os.getenv('USE_TESTNET', 'false')}")
    print()

    # LLM Configuration
    print("🤖 LLM CONFIGURATION")
    print("─" * 80)
    print(f"  Ollama Host:  {os.getenv('OLLAMA_HOST', 'http://localhost:11434')}")
    print(f"  Ollama Model: {os.getenv('OLLAMA_MODEL', 'mistral:7b')}")
    print()

    # Trading Configuration
    print("💹 TRADING CONFIGURATION")
    print("─" * 80)
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    mode = "🟢 PAPER TRADING (Safe)" if dry_run else "🔴 LIVE TRADING (Real Money!)"
    print(f"  Trading Mode:     {mode}")
    print(f"  Stake Currency:   {os.getenv('STAKE_CURRENCY', 'USDT')}")
    print(f"  Stake Amount:     {os.getenv('STAKE_AMOUNT', '50')} {os.getenv('STAKE_CURRENCY', 'USDT')}")
    print(f"  Max Open Trades:  {os.getenv('MAX_OPEN_TRADES', '3')}")
    print(f"  Timeframe:        {os.getenv('TIMEFRAME', '1h')}")
    print()

    # Risk Management
    print("🛡️  RISK MANAGEMENT")
    print("─" * 80)
    print(f"  Stop Loss:        {os.getenv('STOP_LOSS_PERCENTAGE', '3.0')}%")
    print(f"  Take Profit:      {os.getenv('TAKE_PROFIT_PERCENTAGE', '5.0')}%")
    print(f"  Risk Per Trade:   {os.getenv('RISK_PER_TRADE_PERCENTAGE', '1.0')}%")
    print(f"  Max Daily Trades: {os.getenv('MAX_DAILY_TRADES', '10')}")
    print()

    # Telegram
    print("📱 TELEGRAM NOTIFICATIONS")
    print("─" * 80)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if bot_token and bot_token != "your_telegram_bot_token_here":
        print(f"  Bot Token: {mask_key(bot_token, 8)}")
        print(f"  Chat ID:   {chat_id}")
        print("  Status:    ✅ Configured")
    else:
        print("  Status:    ⚠️  Not configured (notifications disabled)")
    print()

    # Quick Commands
    print("⚡ QUICK COMMANDS")
    print("─" * 80)
    print("  Verify API Keys:          python scripts/verify_api_keys.py")
    print("  Initialize Data:          ./scripts/initialize_data_pipeline.sh")
    print("  Run Backtest:             python backtest/run_backtest.py")
    print("  Start Paper Trading:      docker-compose -f docker-compose.production.yml up -d")
    print("  View Logs:                docker-compose -f docker-compose.production.yml logs -f")
    print("  Stop Trading:             docker-compose -f docker-compose.production.yml down")
    print()

    # Status
    print("📊 SYSTEM STATUS")
    print("─" * 80)

    # Check if .env exists
    if env_path.exists():
        print("  ✅ .env file found")
    else:
        print("  ❌ .env file missing")

    # Check API keys
    if os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_KEY") != "your_binance_api_key_here":
        print("  ✅ Binance API keys configured")
    else:
        print("  ❌ Binance API keys not configured")

    # Check trading mode
    if dry_run:
        print("  ✅ Safe mode enabled (DRY_RUN=true)")
    else:
        print("  ⚠️  LIVE TRADING ENABLED - REAL MONEY AT RISK!")

    print()

    # Warnings
    if not dry_run:
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║  ⚠️  WARNING: LIVE TRADING MODE ACTIVE                                       ║")
        print("║  Real money is at risk. Ensure you have tested thoroughly.                  ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print()

    # Footer
    print("─" * 80)
    print("VoidCat RDC - Wykeve Freeman (Sorrow Eternal)")
    print("Contact: SorrowsCry86@voidcat.org | Support: CashApp $WykeveTF")
    print("─" * 80)
    print()


if __name__ == "__main__":
    print_config()
