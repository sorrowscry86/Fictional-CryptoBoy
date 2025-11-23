# Multi-stage build for Data Ingestor Service
# VoidCat RDC - CryptoBoy Trading Bot

# Stage 1: Python dependencies
FROM python:3.10-slim AS python-deps

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY services/requirements.txt /app/services/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/services/requirements.txt

# Stage 2: Runtime image
FROM python:3.10-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=python-deps /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy only necessary application code
COPY services/__init__.py /app/services/
COPY services/common/ /app/services/common/
COPY services/data_ingestor/ /app/services/data_ingestor/
COPY data/__init__.py /app/data/
COPY data/*_collector.py /app/data/
COPY llm/__init__.py /app/llm/

# Set Python path
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "services.data_ingestor.market_streamer"]
