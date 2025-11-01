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

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "services.signal_cacher.signal_cacher"]
