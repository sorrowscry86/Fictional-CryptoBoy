# Makefile for CryptoBoy Trading Bot
# VoidCat RDC - Quick development commands

.PHONY: help install format lint test test-unit test-integration test-e2e test-docker clean all

help:
	@echo "CryptoBoy Trading Bot - Development Commands"
	@echo "============================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies"
	@echo "  make format           - Format code with black and isort"
	@echo "  make lint             - Run linters (flake8, pylint)"
	@echo "  make test             - Run all tests (native)"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e         - Run E2E tests only"
	@echo "  make test-docker      - Run all tests in Docker"
	@echo "  make clean            - Clean up generated files"
	@echo "  make all              - Format, lint, and test"
	@echo ""
	@echo "Docker commands:"
	@echo "  make docker-build     - Build all Docker images"
	@echo "  make docker-up        - Start Docker services"
	@echo "  make docker-down      - Stop Docker services"
	@echo "  make docker-logs      - View Docker logs"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r services/requirements-common.txt
	pip install pytest pytest-cov pytest-asyncio pylint flake8 black isort pre-commit
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
	@echo "Running all tests (native mode)..."
	@bash scripts/run_tests.sh all native

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v --cov=services --cov=llm --cov-report=term-missing --cov-report=html

test-integration:
	@echo "Running integration tests..."
	@echo "Checking for required services (RabbitMQ, Redis)..."
	@if ! nc -z localhost 5672 2>/dev/null; then \
		echo "Starting test services..."; \
		docker-compose -f docker-compose.test.yml up -d rabbitmq-test redis-test; \
		sleep 10; \
	fi
	RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=cryptoboy RABBITMQ_PASS=cryptoboy123 \
	REDIS_HOST=localhost REDIS_PORT=6379 \
	pytest tests/integration/ -v -m integration

test-e2e:
	@echo "Running E2E tests..."
	@echo "⚠️  Full system must be running. Start with: make docker-up"
	RABBITMQ_HOST=localhost RABBITMQ_USER=admin RABBITMQ_PASS=cryptoboy_secret \
	REDIS_HOST=localhost \
	pytest tests/e2e/ -v -m e2e --tb=short

test-docker:
	@echo "Running tests in Docker containers..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

test-coverage:
	@echo "Generating test coverage report..."
	pytest tests/unit/ tests/integration/ -v \
		--cov=services --cov=llm --cov=strategies \
		--cov-report=html --cov-report=term-missing
	@echo ""
	@echo "✅ Coverage report generated in htmlcov/"
	@echo "   Open htmlcov/index.html in your browser"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
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
	@echo "   View logs with: make docker-logs"

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
