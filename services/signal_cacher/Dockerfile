FROM python:3.10-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ /app/services/

ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "services.signal_cacher.signal_cacher"]
