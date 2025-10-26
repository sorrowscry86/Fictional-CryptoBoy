#!/bin/bash
# Complete Pipeline - Run all setup steps sequentially

set -e

echo "================================================"
echo "LLM Crypto Trading Bot - Complete Pipeline"
echo "================================================"
echo ""
echo "This will run the complete setup and deployment pipeline"
echo "Estimated time: 30-60 minutes"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Phase 1: Environment Setup
echo ""
echo "===== PHASE 1: Environment Setup ====="
./scripts/setup_environment.sh

# Phase 2: Data Pipeline
echo ""
echo "===== PHASE 2: Data Pipeline ====="
./scripts/initialize_data_pipeline.sh

# Phase 3: Backtesting
echo ""
echo "===== PHASE 3: Backtesting ====="
echo "Running backtesting to validate strategy..."
source venv/bin/activate
python backtest/run_backtest.py

echo ""
echo "================================================"
echo "Review backtest results above."
echo ""
read -p "Results look good? Continue to deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Pipeline stopped. Review results and run deployment manually when ready."
    exit 0
fi

# Phase 4: Deployment
echo ""
echo "===== PHASE 4: Deployment ====="
echo ""
echo "Deployment options:"
echo "1. Paper trading (dry run)"
echo "2. Live trading (REAL MONEY)"
echo ""
read -p "Select mode (1 or 2): " -n 1 -r
echo

if [[ $REPLY == "1" ]]; then
    echo "Starting in PAPER TRADING mode..."
    export DRY_RUN=true
    docker-compose -f docker-compose.production.yml up -d
elif [[ $REPLY == "2" ]]; then
    echo ""
    echo "⚠️  WARNING: You are about to start LIVE TRADING with REAL MONEY"
    echo "Please confirm you have:"
    echo "  - Reviewed and approved backtest results"
    echo "  - Set up proper API keys in .env"
    echo "  - Configured Telegram alerts"
    echo "  - Set appropriate risk limits"
    echo ""
    read -p "I understand the risks and want to proceed (type 'YES' to confirm): " confirm
    if [[ $confirm == "YES" ]]; then
        export DRY_RUN=false
        docker-compose -f docker-compose.production.yml up -d
    else
        echo "Live trading cancelled."
        exit 0
    fi
else
    echo "Invalid selection"
    exit 1
fi

echo ""
echo "================================================"
echo "Deployment complete!"
echo "================================================"
echo ""
echo "Monitor your bot:"
echo "  - Logs: docker-compose -f docker-compose.production.yml logs -f"
echo "  - Status: docker-compose -f docker-compose.production.yml ps"
echo "  - API: http://localhost:8080"
echo ""
echo "Telegram alerts are enabled (check your Telegram)"
echo ""
