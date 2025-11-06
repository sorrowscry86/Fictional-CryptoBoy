#!/bin/bash
# VoidCat RDC - CryptoBoy Testing Script
# Run tests natively or in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is open (portable)
check_port() {
    local host=$1
    local port=$2
    
    # Try multiple methods for portability
    if command_exists nc; then
        nc -z "$host" "$port" 2>/dev/null
    elif command_exists timeout; then
        timeout 1 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null
    else
        # Fallback: try to connect with Python
        python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('$host', $port)); s.close()" 2>/dev/null
    fi
}

# Function to run unit tests
run_unit_tests() {
    local mode=$1
    
    print_info "Running unit tests in $mode mode..."
    
    if [ "$mode" = "native" ]; then
        pytest tests/unit/ -v --cov=services --cov=llm --cov-report=term-missing
    elif [ "$mode" = "docker" ]; then
        docker run --rm \
            -v $(pwd):/app \
            -w /app \
            python:3.10-slim \
            bash -c "pip install -q pytest pytest-cov && pytest tests/unit/ -v"
    fi
}

# Function to run integration tests
run_integration_tests() {
    local mode=$1
    
    print_info "Running integration tests in $mode mode..."
    
    if [ "$mode" = "native" ]; then
        # Check if services are running
        if ! check_port localhost 5672; then
            print_warning "RabbitMQ not detected on localhost:5672"
            print_info "Starting services with docker-compose..."
            docker-compose up -d rabbitmq redis
            sleep 10
        fi
        
        export RABBITMQ_HOST=localhost
        export RABBITMQ_PORT=5672
        export RABBITMQ_USER=cryptoboy
        export RABBITMQ_PASS=cryptoboy123
        export REDIS_HOST=localhost
        export REDIS_PORT=6379
        
        pytest tests/integration/ -v -m integration
    elif [ "$mode" = "docker" ]; then
        # Use docker-compose for integration tests
        docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
    fi
}

# Function to run E2E tests
run_e2e_tests() {
    local mode=$1
    
    print_info "Running E2E tests in $mode mode..."
    
    if [ "$mode" = "native" ]; then
        # Check if full system is running
        if ! check_port localhost 5672; then
            print_error "Full system must be running for E2E tests"
            print_info "Start with: docker-compose -f docker-compose.production.yml up -d"
            exit 1
        fi
        
        export RABBITMQ_HOST=localhost
        export RABBITMQ_USER=admin
        export RABBITMQ_PASS=cryptoboy_secret
        export REDIS_HOST=localhost
        
        pytest tests/e2e/ -v -m e2e --tb=short
    elif [ "$mode" = "docker" ]; then
        # Run E2E tests against docker deployment
        docker-compose -f docker-compose.production.yml up -d
        sleep 20
        
        docker run --rm \
            --network cryptoboy_trading-network \
            -v $(pwd):/app \
            -w /app \
            -e RABBITMQ_HOST=rabbitmq \
            -e RABBITMQ_USER=admin \
            -e RABBITMQ_PASS=cryptoboy_secret \
            -e REDIS_HOST=redis \
            python:3.10-slim \
            bash -c "pip install -q pytest && pytest tests/e2e/ -v -m e2e"
        
        docker-compose -f docker-compose.production.yml down
    fi
}

# Function to run all tests
run_all_tests() {
    local mode=$1
    
    print_info "Running all tests in $mode mode..."
    
    run_unit_tests "$mode"
    run_integration_tests "$mode"
    run_e2e_tests "$mode"
    
    print_info "✓ All tests completed!"
}

# Main script
main() {
    local test_type="${1:-all}"
    local mode="${2:-native}"
    
    # Validate mode
    if [ "$mode" != "native" ] && [ "$mode" != "docker" ]; then
        print_error "Invalid mode: $mode (must be 'native' or 'docker')"
        exit 1
    fi
    
    # Check for required tools
    if [ "$mode" = "native" ]; then
        if ! command_exists pytest; then
            print_error "pytest not found. Install with: pip install pytest pytest-cov pytest-asyncio"
            exit 1
        fi
    else
        if ! command_exists docker; then
            print_error "docker not found. Please install Docker."
            exit 1
        fi
    fi
    
    # Run tests based on type
    case "$test_type" in
        unit)
            run_unit_tests "$mode"
            ;;
        integration)
            run_integration_tests "$mode"
            ;;
        e2e)
            run_e2e_tests "$mode"
            ;;
        all)
            run_all_tests "$mode"
            ;;
        *)
            print_error "Invalid test type: $test_type"
            echo "Usage: $0 [unit|integration|e2e|all] [native|docker]"
            echo ""
            echo "Examples:"
            echo "  $0 unit native          # Run unit tests natively"
            echo "  $0 integration docker   # Run integration tests in Docker"
            echo "  $0 all native          # Run all tests natively"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
