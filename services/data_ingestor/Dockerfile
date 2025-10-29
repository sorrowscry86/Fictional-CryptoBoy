FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (ingestor-specific)
COPY services/requirements-ingestor.txt /app/services/requirements-ingestor.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/services/requirements-ingestor.txt

# Copy application code (only what this service needs)
COPY services/__init__.py /app/services/
COPY services/common/ /app/services/common/
COPY services/data_ingestor/ /app/services/data_ingestor/
COPY data/ /app/data/
COPY llm/ /app/llm/

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "services.data_ingestor.market_streamer"]
