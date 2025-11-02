# CryptoBoy Testing Guide
**VoidCat RDC - Comprehensive Testing Infrastructure**

This guide covers all testing approaches for the CryptoBoy trading bot system.

## 🎯 Quick Start

### Run All Tests (Native)
```bash
make test
# or
scripts/run_tests.sh all native
```

### Run Tests in Docker
```bash
make test-docker
# or
scripts/run_tests.sh all docker
```

## 📋 Test Structure

```
tests/
├── unit/                  # Isolated component tests (mocked dependencies)
│   ├── test_rabbitmq_client.py
│   ├── test_redis_client.py
│   └── test_signal_processor.py
├── integration/           # Tests with real services (RabbitMQ, Redis)
│   ├── test_rabbitmq_integration.py
│   ├── test_redis_integration.py
│   └── test_sentiment_integration.py
├── e2e/                   # Full system workflow tests
│   ├── test_full_system.py
│   └── test_docker_deployment.py
├── stress_tests/          # Performance and load tests
│   ├── rabbitmq_load_test.py
│   ├── redis_stress_test.py
│   └── sentiment_load_test.py
└── monitoring/            # System health checks
    ├── latency_monitor.py
    └── system_health_check.py
```

## 🧪 Test Categories

### Unit Tests
Test individual components in isolation using mocks.

**Run:**
```bash
make test-unit
# or
pytest tests/unit/ -v
```

**Coverage:**
- ✅ RabbitMQ client (connect, publish, consume, close)
- ✅ Redis client (set, get, delete, keys)
- ✅ Signal processor (rolling sentiment, aggregation, smoothing)

**Requirements:** None (uses mocks)

### Integration Tests
Test microservices with actual external dependencies.

**Run:**
```bash
make test-integration
# or
pytest tests/integration/ -v -m integration
```

**Coverage:**
- ✅ RabbitMQ message flow (pub/sub, queues, durability)
- ✅ Redis caching (sentiment storage, staleness checks)
- ✅ Sentiment processing pipeline (FinBERT/Ollama)

**Requirements:** RabbitMQ and Redis running (auto-started if using make)

### E2E Tests
Test complete system workflows from news to trading signals.

**Run:**
```bash
make test-e2e
# or
pytest tests/e2e/ -v -m e2e
```

**Coverage:**
- ✅ News → Sentiment → Cache workflow
- ✅ Multi-pair processing
- ✅ System health checks
- ✅ Performance under load

**Requirements:** Full system running (docker-compose -f docker-compose.production.yml up)

## 🐳 Docker-Based Testing

### Test Runner Container
Runs tests in isolated container with all dependencies.

```bash
# Build and run tests
docker-compose -f docker-compose.test.yml up --build

# Run specific test type
docker-compose -f docker-compose.test.yml run test-runner pytest tests/unit/ -v
```

### Advantages
- ✅ Consistent environment
- ✅ Isolated from host
- ✅ Matches CI/CD exactly
- ✅ No local Python setup needed

## ⚙️ Configuration

### pytest.ini Options (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Coverage (.coveragerc)
```ini
[run]
source = .
omit = */tests/*, */venv/*, */user_data/*

[report]
precision = 2
show_missing = True
```

## 📊 Test Markers

Run tests by category:

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"
```

## 🔧 Makefile Targets

| Command | Description |
|---------|-------------|
| `make test` | Run all tests natively |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests (starts services if needed) |
| `make test-e2e` | Run E2E tests (requires full system) |
| `make test-docker` | Run all tests in Docker |
| `make test-coverage` | Generate HTML coverage report |

## 🚀 CI/CD Integration

GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
jobs:
  unit-tests:        # Fast isolated tests
  integration-tests: # Tests with RabbitMQ/Redis services
  docker-build:      # Multi-stage Docker builds with caching
  e2e-tests:         # Full system tests (main/develop only)
  security-scan:     # Trivy vulnerability scanning
```

### Optimizations
- ✅ Multi-stage Docker builds (60% smaller images)
- ✅ GitHub Actions caching (faster builds)
- ✅ Parallel test execution
- ✅ Coverage reporting to Codecov

## 🔍 Writing Tests

### Unit Test Example
```python
import unittest
from unittest.mock import MagicMock, patch

class TestMyComponent(unittest.TestCase):
    @patch('module.dependency')
    def test_functionality(self, mock_dep):
        mock_dep.return_value = 'expected'
        result = my_function()
        assert result == 'expected'
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
def test_with_real_service():
    client = RabbitMQClient(host='localhost')
    client.connect()
    assert client.connection is not None
```

### E2E Test Example
```python
@pytest.mark.e2e
def test_full_workflow(system_config):
    # Publish news
    publish_news_article(test_article)
    
    # Wait for processing
    time.sleep(5)
    
    # Verify sentiment cached
    sentiment = redis.get_sentiment('BTC/USDT')
    assert sentiment is not None
```

## 🐛 Debugging Failed Tests

### View Detailed Output
```bash
pytest tests/ -v --tb=long
```

### Run Specific Test
```bash
pytest tests/unit/test_rabbitmq_client.py::TestRabbitMQClient::test_connect -v
```

### Check Coverage
```bash
pytest tests/unit/ --cov=services --cov-report=html
# Open htmlcov/index.html
```

### Debug in Container
```bash
docker-compose -f docker-compose.test.yml run test-runner bash
# Then run: pytest tests/ -v --pdb
```

## 📈 Performance Tests

### Stress Tests
```bash
# Run all stress tests
bash tests/run_all_stress_tests.sh

# Individual tests
python tests/stress_tests/rabbitmq_load_test.py
python tests/stress_tests/redis_stress_test.py
python tests/stress_tests/sentiment_load_test.py
```

### Monitoring Tests
```bash
# System health check
python tests/monitoring/system_health_check.py

# Latency monitoring
python tests/monitoring/latency_monitor.py
```

## 🎓 Best Practices

1. **Run unit tests frequently** - Fast feedback during development
2. **Run integration tests before committing** - Catch service issues
3. **Run E2E tests before PR** - Ensure full system works
4. **Check coverage** - Aim for >80% on new code
5. **Use appropriate markers** - Organize tests by type
6. **Mock external services in unit tests** - Keep them fast
7. **Test both success and failure paths** - Edge cases matter
8. **Keep tests independent** - No shared state between tests

## 🔐 Security Testing

### Dependency Scanning
```bash
# Check for known vulnerabilities
safety check --file requirements.txt
safety check --file services/requirements.txt
```

### Container Scanning
```bash
# Scan Docker images
trivy image cryptoboy-trading-bot:latest
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Docker Testing Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [CI/CD with GitHub Actions](https://docs.github.com/en/actions)

## 🤝 Contributing

When adding new features:

1. Write unit tests first (TDD approach)
2. Add integration tests for service interactions
3. Update E2E tests if workflow changes
4. Run full test suite before PR
5. Ensure coverage doesn't decrease

---

**VoidCat RDC** - Excellence in Every Line of Code
