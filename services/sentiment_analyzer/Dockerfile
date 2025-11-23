# Multi-stage build for Sentiment Analyzer Service
# VoidCat RDC - CryptoBoy Trading Bot

# Stage 1: Python dependencies (including PyTorch and Transformers)
FROM python:3.10-slim AS python-deps

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY services/requirements.txt /app/services/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/services/requirements.txt

# Stage 2: Runtime image
FROM python:3.10-slim

WORKDIR /app

# Copy Python packages from builder (includes PyTorch/Transformers)
COPY --from=python-deps /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy only necessary application code
COPY services/__init__.py /app/services/
COPY services/common/ /app/services/common/
COPY services/sentiment_analyzer/ /app/services/sentiment_analyzer/
COPY llm/ /app/llm/

# Set Python path
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# Create cache directory
RUN mkdir -p /app/.cache/huggingface

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "-m", "services.sentiment_analyzer.sentiment_processor"]
