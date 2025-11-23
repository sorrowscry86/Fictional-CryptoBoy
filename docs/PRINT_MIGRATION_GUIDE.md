# Print Statement Migration Guide
# VoidCat RDC - CryptoBoy Trading System

## Overview
This document tracks the migration from print() statements to structured logging across the CryptoBoy codebase.

**Status:** 429 print() statements identified  
**Priority:** HIGH (Phase 4 - Efficiency & Flow)  
**Impact:** Performance, monitoring, debugging, log aggregation

## Why Migrate?

### Problems with print():
1. **No log levels** - Cannot filter by severity (DEBUG, INFO, WARNING, ERROR)
2. **No timestamps** - Cannot correlate events in time
3. **No context** - Missing process ID, thread ID, module name
4. **Performance** - Unbuffered I/O blocks execution
5. **No redirection** - Cannot send to monitoring systems (Prometheus, ELK)
6. **Testing** - Difficult to capture and verify in unit tests

### Benefits of logging:
1. **Structured output** - JSON format for parsing
2. **Filterable** - Control verbosity with log levels
3. **Contextual** - Automatic metadata (timestamp, module, line number)
4. **Redirectable** - File, syslog, network, monitoring systems
5. **Performant** - Buffered, asynchronous options
6. **Testable** - Easy to mock and assert in tests

## Migration Pattern

### Before (Profane):
```python
print(f"Loading model: {model_path}")
print(f"ERROR: Failed to connect: {error}")
```

### After (Harmonized):
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Loading model: {model_path}", extra={'model': model_path})
logger.error(f"Failed to connect: {error}", exc_info=True)
```

## File-by-File Migration Plan

### Priority 1: Core Services (High Impact)
- [ ] `services/sentiment_analyzer/sentiment_processor.py` (31 occurrences)
- [ ] `services/data_ingestor/news_poller.py` (18 occurrences)
- [ ] `services/signal_cacher/signal_cacher.py` (12 occurrences)
- [ ] `llm/huggingface_sentiment.py` (56 occurrences)
- [ ] `llm/sentiment_analyzer.py` (24 occurrences)

### Priority 2: Scripts (Medium Impact)
- [ ] `scripts/monitor_trading.py` (48 occurrences)
- [ ] `scripts/run_data_pipeline.py` (35 occurrences)
- [ ] `scripts/verify_api_keys.py` (21 occurrences)
- [ ] `data/news_aggregator.py` (23 occurrences)
- [ ] `data/market_data_collector.py` (19 occurrences)

### Priority 3: Utilities (Lower Impact)
- [ ] Remaining scripts and utilities (153 occurrences)

## Standard Logging Configuration

Add to each file:

```python
import logging

# Module-level logger
logger = logging.getLogger(__name__)

# For scripts, configure logging:
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()  # Also print to console
        ]
    )
```

## Log Level Guidelines

- **DEBUG**: Detailed diagnostic information (model weights, full messages)
- **INFO**: Normal operation events (model loaded, connection established)
- **WARNING**: Unexpected but handled situations (retry after failure)
- **ERROR**: Errors that affect functionality (connection failed, invalid data)
- **CRITICAL**: System-threatening errors (out of memory, config missing)

## Structured Logging Example

```python
# Rich context with extra fields
logger.info(
    "Processing sentiment for pair",
    extra={
        'pair': 'BTC/USDT',
        'headline': headline,
        'score': sentiment_score,
        'latency_ms': latency
    }
)

# Exception logging
try:
    result = process_data()
except Exception as e:
    logger.error(
        "Failed to process data",
        exc_info=True,  # Includes full traceback
        extra={'input_size': len(data)}
    )
```

## Testing Considerations

### Before (Hard to Test):
```python
print("Processing complete")
```

### After (Testable):
```python
logger.info("Processing complete")

# In tests:
def test_processing(caplog):
    with caplog.at_level(logging.INFO):
        process()
    assert "Processing complete" in caplog.text
```

## Progress Tracker

**Total:** 429 print() statements  
**Migrated:** 0 (0%)  
**Remaining:** 429 (100%)

**Updated:** 2025-11-20  
**Owner:** The High Evolutionary
