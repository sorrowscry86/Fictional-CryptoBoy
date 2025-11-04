FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal - no build tools for TA-Lib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching optimization)
COPY requirements.txt .

# Install Python dependencies (--no-cache-dir saves space)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code LAST (least frequently changing)
COPY . .

# Create necessary directories
RUN mkdir -p data/ohlcv_data data/news_data logs backtest/backtest_reports && \
    # Clean cache to reduce image size
    find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PYTHONDONTWRITEBYTECODE=1

# Health check - verify Freqtrade API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/ping || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "freqtrade", "trade", "--config", "config/live_config.json"]
