# Multi-stage build for CryptoBoy Trading Bot
# VoidCat RDC - Optimized for fast builds and small image size

# Stage 1: Build TA-Lib
FROM python:3.10-slim AS talib-builder

RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build and install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Stage 2: Python dependencies
FROM python:3.10-slim AS python-deps

WORKDIR /app

# Copy TA-Lib from builder
COPY --from=talib-builder /usr/lib/libta_lib.* /usr/lib/
COPY --from=talib-builder /usr/include/ta-lib/ /usr/include/ta-lib/

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Final runtime image
FROM python:3.10-slim

WORKDIR /app

# Copy TA-Lib libraries
COPY --from=talib-builder /usr/lib/libta_lib.* /usr/lib/
COPY --from=talib-builder /usr/include/ta-lib/ /usr/include/ta-lib/

# Copy Python packages
COPY --from=python-deps /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy application code (use .dockerignore to exclude unnecessary files)
COPY strategies/ ./strategies/
COPY llm/ ./llm/
COPY monitoring/ ./monitoring/
COPY risk/ ./risk/
COPY backtest/ ./backtest/
COPY data/ ./data/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create necessary directories with proper permissions
RUN mkdir -p data/ohlcv_data data/news_data logs backtest/backtest_reports user_data \
    && chmod -R 755 data logs backtest

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app

# Health check - verify Freqtrade API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/ping || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "freqtrade", "trade", "--config", "config/live_config.json"]
