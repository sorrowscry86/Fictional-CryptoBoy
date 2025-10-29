#!/usr/bin/env python3
"""
VoidCat RDC - CryptoBoy Trading System
Paper Trading Launch Script

Launches the trading system in safe paper trading mode with all safety checks.
Author: Wykeve Freeman (Sorrow Eternal)
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


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


def check_dry_run_mode():
    """Verify DRY_RUN is enabled"""
    dry_run = os.getenv('DRY_RUN', 'true').lower()
    
    if dry_run != 'true':
        print_error("DRY_RUN is not enabled!")
        print_warning("For safety, paper trading mode requires DRY_RUN=true")
        print_info("Updating .env file...")
        
        # Update .env file
        env_content = env_path.read_text()
        if 'DRY_RUN=false' in env_content:
            env_content = env_content.replace('DRY_RUN=false', 'DRY_RUN=true')
            env_path.write_text(env_content)
            print_success("Updated DRY_RUN=true in .env")
            # Reload
            load_dotenv(env_path, override=True)
        else:
            print_error("Could not update .env file automatically")
            print_info("Please manually set DRY_RUN=true in .env")
            return False
    
    print_success("DRY_RUN mode is ENABLED (paper trading)")
    return True


def check_api_keys():
    """Verify API keys are configured"""
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or api_key == 'your_binance_api_key_here':
        print_warning("Binance API key not configured")
        return False
    
    if not api_secret or api_secret == 'your_binance_api_secret_here':
        print_warning("Binance API secret not configured")
        return False
    
    print_success("API keys configured")
    return True


def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=3)
        if response.status_code == 200:
            print_success("Ollama service is running")
            return True
    except:
        pass
    
    print_warning("Ollama service not running")
    print_info("Starting Ollama via Docker Compose...")
    return False


def start_ollama():
    """Start Ollama service"""
    try:
        result = subprocess.run(
            ['docker-compose', 'up', '-d', 'ollama'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Ollama service started")
            # Wait for it to be ready
            print_info("Waiting for Ollama to initialize...")
            import time
            time.sleep(5)
            return True
        else:
            print_error(f"Failed to start Ollama: {result.stderr}")
            return False
    except Exception as e:
        print_error(f"Error starting Ollama: {e}")
        return False


def check_model():
    """Check if required model is available"""
    model = os.getenv('OLLAMA_MODEL', 'mistral:7b')
    
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True
        )
        
        if model in result.stdout:
            print_success(f"Model '{model}' is available")
            return True
        else:
            print_warning(f"Model '{model}' not found")
            print_info(f"Please run: ollama pull {model}")
            return False
    except Exception as e:
        print_warning(f"Could not check Ollama models: {e}")
        return False


def display_configuration():
    """Display current trading configuration"""
    print_header("Trading Configuration")
    
    dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
    
    config = {
        'Trading Mode': '🟢 PAPER TRADING (Safe)' if dry_run else '🔴 LIVE TRADING (Real Money!)',
        'Stake Currency': os.getenv('STAKE_CURRENCY', 'USDT'),
        'Stake Amount': f"{os.getenv('STAKE_AMOUNT', '50')} {os.getenv('STAKE_CURRENCY', 'USDT')}",
        'Max Open Trades': os.getenv('MAX_OPEN_TRADES', '3'),
        'Stop Loss': f"{os.getenv('STOP_LOSS_PERCENTAGE', '3.0')}%",
        'Take Profit': f"{os.getenv('TAKE_PROFIT_PERCENTAGE', '5.0')}%",
        'Sentiment Model': os.getenv('HUGGINGFACE_MODEL', 'finbert') if os.getenv('USE_HUGGINGFACE', 'true') == 'true' else os.getenv('OLLAMA_MODEL', 'mistral:7b'),
    }
    
    for key, value in config.items():
        print(f"  {key:.<30} {value}")
    
    print()


def confirm_launch():
    """Get user confirmation to proceed"""
    print_warning("⚠️  IMPORTANT: Review the configuration above")
    print_info("This will start the trading bot in PAPER TRADING mode")
    print_info("No real money will be used - all trades are simulated")
    print()
    
    response = input(f"{Fore.YELLOW}Proceed with launch? (yes/no): {Style.RESET_ALL}")
    return response.lower() in ['yes', 'y']


def launch_system():
    """Launch the trading system"""
    print_header("Launching CryptoBoy Trading System")
    
    try:
        # Start docker-compose
        print_info("Starting Docker services...")
        
        result = subprocess.run(
            ['docker-compose', '-f', 'docker-compose.production.yml', 'up', '-d'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Docker services started successfully")
            print()
            print_info("Trading bot is now running in paper trading mode")
            print_info("Monitor logs with: docker-compose -f docker-compose.production.yml logs -f")
            print()
            print_success("🚀 CryptoBoy Trading System is LIVE (Paper Trading Mode)")
            return True
        else:
            print_error("Failed to start Docker services")
            print_error(result.stderr)
            return False
            
    except Exception as e:
        print_error(f"Error launching system: {e}")
        return False


def main():
    """Main launch routine"""
    print(f"{Fore.MAGENTA}")
    print(r"""
    ╦  ╦┌─┐┬┌┬┐╔═╗┌─┐┌┬┐  ╦═╗╔╦╗╔═╗
    ╚╗╔╝│ │││ ││  ╠═╣ │   ╠╦╝ ║║║  
     ╚╝ └─┘┴─┴┘╚═╝╩ ╩ ┴   ╩╚══╩╝╚═╝
    """)
    print(f"{Style.RESET_ALL}")
    print(f"{Fore.CYAN}CryptoBoy Trading System - Paper Trading Launch{Style.RESET_ALL}")
    print(f"{Fore.CYAN}VoidCat RDC - Wykeve Freeman (Sorrow Eternal){Style.RESET_ALL}\n")
    
    # Pre-flight checks
    print_header("Pre-Flight Safety Checks")
    
    checks = [
        ("DRY_RUN Mode", check_dry_run_mode()),
        ("API Keys", check_api_keys()),
        ("Ollama Service", check_ollama()),
        ("Model Available", check_model()),
    ]
    
    # If Ollama not running, try to start it
    if not checks[2][1]:
        if start_ollama():
            checks[2] = ("Ollama Service", True)
            checks[3] = ("Model Available", check_model())
    
    # Display check results
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print_success(f"{check_name}: PASSED")
        else:
            print_error(f"{check_name}: FAILED")
            all_passed = False
    
    print()
    
    if not all_passed:
        print_warning("Some pre-flight checks failed")
        print_info("Fix the issues above before launching")
        return 1
    
    # Display configuration
    display_configuration()
    
    # Get confirmation
    if not confirm_launch():
        print_info("Launch cancelled by user")
        return 0
    
    # Launch
    if launch_system():
        print()
        print_header("Post-Launch Information")
        print_info("Services running:")
        print("  • Ollama LLM: http://localhost:11434")
        print("  • Trading Bot API: http://localhost:8080")
        print()
        print_info("Useful commands:")
        print("  • View logs: docker-compose -f docker-compose.production.yml logs -f")
        print("  • Stop system: docker-compose -f docker-compose.production.yml down")
        print("  • Check status: docker-compose -f docker-compose.production.yml ps")
        print()
        print_warning("Remember: This is PAPER TRADING mode - no real money at risk")
        print()
        return 0
    else:
        print_error("Failed to launch system")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Launch cancelled by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
