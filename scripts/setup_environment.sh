#!/bin/bash
# Setup Script - Phase 1: Environment & Infrastructure Setup

set -e

echo "================================================"
echo "LLM Crypto Trading Bot - Environment Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running in project directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Checking system requirements...${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo "Docker: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo "Docker Compose: $(docker-compose --version)"

echo -e "${GREEN}✓ System requirements met${NC}"
echo ""

echo -e "${YELLOW}Step 2: Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo "Virtual environment already exists"
fi
echo ""

echo -e "${YELLOW}Step 3: Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${YELLOW}Step 4: Upgrading pip...${NC}"
pip install --upgrade pip
echo ""

echo -e "${YELLOW}Step 5: Installing Python dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 6: Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file from template${NC}"
    echo -e "${YELLOW}⚠ Please edit .env file with your API keys${NC}"
else
    echo ".env file already exists"
fi
echo ""

echo -e "${YELLOW}Step 7: Creating data directories...${NC}"
mkdir -p data/ohlcv_data
mkdir -p data/news_data
mkdir -p logs
mkdir -p backtest/backtest_reports
mkdir -p user_data
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

echo -e "${YELLOW}Step 8: Starting Ollama Docker container...${NC}"
docker-compose up -d ollama
echo "Waiting for Ollama to start..."
sleep 10

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
else
    echo -e "${YELLOW}⚠ Ollama may not be running. Check with: docker-compose logs ollama${NC}"
fi
echo ""

echo -e "${YELLOW}Step 9: Downloading LLM model...${NC}"
echo "This may take several minutes..."
python llm/model_manager.py
echo ""

echo "================================================"
echo -e "${GREEN}Environment setup complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: source venv/bin/activate"
echo "3. Run: ./scripts/initialize_data_pipeline.sh"
echo ""
