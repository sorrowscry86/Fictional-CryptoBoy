FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/requirements.txt /app/services/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/services/requirements.txt

# Copy application code
COPY services/ /app/services/
COPY data/ /app/data/
COPY llm/ /app/llm/

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "services.data_ingestor.market_streamer"]
