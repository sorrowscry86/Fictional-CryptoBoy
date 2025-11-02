# Code Quality and Standards

**VoidCat RDC - CryptoBoy Trading Bot**

This document outlines the code quality standards and tools used in the CryptoBoy project.

## Current Status

✅ **Zero flake8 violations** (as of November 2025)  
✅ **PEP 8 compliant** (with 120 character line length)  
✅ **Automated formatting** with black and isort  
✅ **Pre-commit hooks** configured  
✅ **CI/CD pipeline** for continuous quality checks

## Code Quality Tools

### 1. Formatting

#### Black (Code Formatter)
```bash
# Format all Python files
black --line-length 120 .

# Check formatting without changes
black --check --line-length 120 .
```

**Configuration**: See `pyproject.toml` [tool.black] section

#### isort (Import Sorter)
```bash
# Sort imports
isort --profile black --line-length 120 .

# Check import sorting
isort --check-only --profile black .
```

**Configuration**: See `pyproject.toml` [tool.isort] section

### 2. Linting

#### Flake8 (Style Guide Enforcement)
```bash
# Run flake8
flake8 .

# Detailed output
flake8 --count --statistics .
```

**Configuration**: See `.flake8` file

**Standards**:
- Max line length: 120 characters
- Ignores: E501 (line too long - handled by black), W503 (line break before binary operator)

#### Pylint (Comprehensive Static Analysis)
```bash
# Run pylint on all modules
pylint llm/ strategies/ services/ scripts/ monitoring/ risk/ backtest/ data/

# Generate report
pylint --rcfile=.pylintrc . > pylint_report.txt
```

**Configuration**: See `.pylintrc` file

### 3. Security Scanning

#### Bandit (Security Linter)
```bash
# Scan for security issues
bandit -r . -ll -i -x tests/,data/,logs/
```

Critical for financial applications - scans for:
- SQL injection vulnerabilities
- Hard-coded credentials
- Unsafe cryptography usage
- Shell injection risks

### 4. Testing

#### Pytest (Test Framework)
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

**Configuration**: See `pyproject.toml` [tool.pytest.ini_options] section

## Quick Commands (Makefile)

We provide a Makefile for common development tasks:

```bash
# Show available commands
make help

# Install dependencies
make install

# Format code (black + isort)
make format

# Run linters (flake8)
make lint

# Run tests
make test

# Clean up build artifacts
make clean

# Run all checks (format + lint + test)
make all

# Check code quality score
make quality
```

## Pre-commit Hooks

Install pre-commit hooks to automatically check code before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

**Configuration**: See `.pre-commit-config.yaml`

The hooks will automatically:
- Remove trailing whitespace
- Fix end-of-file formatting
- Validate YAML and JSON files
- Format code with black
- Sort imports with isort
- Lint with flake8
- Scan for security issues with bandit

## Continuous Integration

GitHub Actions workflows automatically run on every push and pull request:

**Workflow**: `.github/workflows/code-quality.yml`

Checks performed:
1. **Formatting**: Verify black and isort compliance
2. **Linting**: Run flake8 and pylint
3. **Security**: Scan with bandit
4. **Testing**: Execute pytest suite

## Code Quality Metrics

### Before Improvements (Initial State)
- **600 flake8 violations**
- Issues included:
  - 466 blank lines with whitespace
  - 26 trailing whitespace
  - 17 unused imports
  - 14 f-strings missing placeholders
  - Various indentation and formatting issues

### After Improvements (Current State)
- **0 flake8 violations** ✅
- **Automated formatting** in place
- **Pre-commit hooks** configured
- **CI/CD pipeline** active

## Best Practices

### Import Organization
```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import pandas as pd
import numpy as np

# Local application imports
from llm.sentiment_analyzer import SentimentAnalyzer
```

### Code Formatting
```python
# Good: 120 character line limit
result = some_function(
    parameter1="value1",
    parameter2="value2",
    parameter3="value3"
)

# Good: Trailing comma in multi-line structures
my_list = [
    "item1",
    "item2",
    "item3",
]
```

### Error Handling
```python
# Good: Specific exception handling
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Value error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")

# Bad: Bare except clause
try:
    risky_operation()
except:  # Don't do this!
    pass
```

### f-strings
```python
# Good: f-string with placeholders
message = f"Processing {count} items at {rate:.2f} items/sec"

# Bad: f-string without placeholders
message = f"Processing complete"  # Use regular string instead
message = "Processing complete"  # Better
```

## Maintaining Quality

### Before Committing
1. Run `make format` to auto-format code
2. Run `make lint` to check for issues
3. Run `make test` to verify functionality
4. Fix any issues found

### During Development
- Use an IDE with flake8/pylint integration
- Enable auto-formatting on save (black)
- Run pre-commit hooks before pushing

### Code Reviews
- Check that CI/CD pipeline passes
- Review code quality metrics
- Ensure no new warnings introduced

## Configuration Files Reference

- **`.flake8`**: Flake8 linter configuration
- **`.pylintrc`**: Pylint static analyzer configuration
- **`pyproject.toml`**: Black, isort, and pytest configuration
- **`.pre-commit-config.yaml`**: Pre-commit hooks configuration
- **`Makefile`**: Quick development commands
- **`.github/workflows/code-quality.yml`**: CI/CD pipeline

## Troubleshooting

### "Black would reformat X files"
```bash
# Just run black to fix it
make format
```

### "Import X could not be resolved"
```bash
# Ensure all dependencies are installed
make install
```

### "ModuleNotFoundError in tests"
```bash
# Check Python path in test files
# Tests use: sys.path.append(...)
# See tests/stress_tests/ for examples
```

## Resources

- [PEP 8 Style Guide](https://pep8.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

**VoidCat RDC** - Excellence in Every Line of Code  
**Wykeve Freeman (Sorrow Eternal)** - SorrowsCry86@voidcat.org
