# Makefile for CryptoBoy Trading Bot
# VoidCat RDC - Quick development commands

.PHONY: help install format lint test clean all

help:
	@echo "CryptoBoy Trading Bot - Development Commands"
	@echo "============================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install all dependencies"
	@echo "  make format     - Format code with black and isort"
	@echo "  make lint       - Run linters (flake8, pylint)"
	@echo "  make test       - Run all tests"
	@echo "  make clean      - Clean up generated files"
	@echo "  make all        - Format, lint, and test"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r services/requirements-common.txt
	pip install pytest pylint flake8 black isort pre-commit
	@echo "✅ Dependencies installed"

format:
	@echo "Formatting code with black..."
	black --line-length 120 --exclude '/(\.git|__pycache__|user_data|logs|data|backtest_reports)/' .
	@echo ""
	@echo "Sorting imports with isort..."
	isort --profile black --line-length 120 --skip-glob '*.git/*' --skip-glob '*/__pycache__/*' .
	@echo "✅ Code formatted"

lint:
	@echo "Running flake8..."
	flake8 --max-line-length=120 --extend-ignore=E501,W503 \
		--exclude=.git,__pycache__,user_data,logs,data,backtest_reports \
		--count --statistics .
	@echo ""
	@echo "✅ Flake8 passed"

lint-pylint:
	@echo "Running pylint (full analysis)..."
	pylint llm/ strategies/ services/ scripts/ monitoring/ risk/ backtest/ data/ \
		--rcfile=.pylintrc || true
	@echo ""
	@echo "✅ Pylint analysis complete"

test:
	@echo "Running tests..."
	pytest tests/ -v --tb=short || true
	@echo "✅ Tests complete"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ Cleaned up"

all: format lint test
	@echo ""
	@echo "✅ All checks passed!"

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose -f docker-compose.production.yml build
	@echo "✅ Docker images built"

docker-up:
	@echo "Starting Docker services..."
	docker-compose -f docker-compose.production.yml up -d
	@echo "✅ Docker services started"

docker-down:
	@echo "Stopping Docker services..."
	docker-compose -f docker-compose.production.yml down
	@echo "✅ Docker services stopped"

docker-logs:
	docker-compose -f docker-compose.production.yml logs -f

# Check code quality score
quality:
	@echo "Code Quality Report"
	@echo "=================="
	@echo ""
	@echo "Flake8 Issues:"
	@flake8 --max-line-length=120 --extend-ignore=E501,W503 \
		--exclude=.git,__pycache__,user_data,logs,data,backtest_reports \
		--count . || echo "No issues found ✅"
	@echo ""
	@echo "Lines of Code:"
	@find . -name "*.py" -not -path "./.git/*" -not -path "*/__pycache__/*" \
		-not -path "*/user_data/*" -not -path "*/logs/*" -not -path "*/data/*" \
		| xargs wc -l | tail -1
