FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (common)
COPY services/requirements-common.txt /app/services/requirements-common.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/services/requirements-common.txt

# Copy application code (only what this service needs)
COPY services/__init__.py /app/services/
COPY services/common/ /app/services/common/
COPY services/sentiment_analyzer/ /app/services/sentiment_analyzer/
COPY llm/ /app/llm/

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "services.sentiment_analyzer.sentiment_processor"]
