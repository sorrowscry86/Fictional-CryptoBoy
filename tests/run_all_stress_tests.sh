#!/bin/bash
#
# Comprehensive Stress Test Suite Runner
# Runs all performance and reliability tests for CryptoBoy microservices
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
RESULTS_DIR="tests/stress_tests/results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CryptoBoy Stress Test Suite${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Results will be saved to: ${YELLOW}$RESULTS_DIR${NC}"
echo ""

# Function to run a test and capture results
run_test() {
    local test_name=$1
    local test_command=$2
    local log_file="$RESULTS_DIR/${test_name}.log"

    echo -e "${YELLOW}Running: $test_name${NC}"
    echo "Started at: $(date)" | tee "$log_file"

    if eval "$test_command" 2>&1 | tee -a "$log_file"; then
        echo -e "${GREEN}✓ $test_name completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        return 1
    fi
}

# Counter for test results
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${GREEN}1. RabbitMQ Load Test${NC}"
echo "   Testing message queue with 10,000 messages..."
if run_test "rabbitmq_load_test" "python tests/stress_tests/rabbitmq_load_test.py --messages 10000 --mode parallel"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi
echo ""

echo -e "${GREEN}2. Redis Stress Test${NC}"
echo "   Testing cache with rapid sentiment updates..."
if run_test "redis_stress_test" "python tests/stress_tests/redis_stress_test.py --operations 10000 --mode parallel"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi
echo ""

echo -e "${GREEN}3. Sentiment Processing Load Test${NC}"
echo "   Testing LLM with 100 concurrent articles..."
if run_test "sentiment_load_test" "python tests/stress_tests/sentiment_load_test.py --articles 100 --mode parallel --workers 4"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi
echo ""

echo -e "${GREEN}4. End-to-End Latency Test${NC}"
echo "   Measuring pipeline latency (RSS → LLM → Redis)..."
if run_test "latency_measurement" "python tests/monitoring/latency_monitor.py --measurements 20 --interval 10"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi
echo ""

# Copy JSON reports to results directory
echo "Copying test reports..."
cp -f tests/stress_tests/*.json "$RESULTS_DIR/" 2>/dev/null || true
cp -f tests/monitoring/*.json "$RESULTS_DIR/" 2>/dev/null || true

# Generate summary report
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Results Directory: ${YELLOW}$RESULTS_DIR${NC}"
echo ""

# Check if all tests passed
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All stress tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check logs in $RESULTS_DIR${NC}"
    exit 1
fi
