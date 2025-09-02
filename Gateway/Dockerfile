# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the handler file
COPY rp_handler.py /app/

# Set environment variables for Python
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# JWT Configuration (these should be overridden in production)
ENV JWT_SECRET_KEY="your-super-secret-jwt-key-change-this-in-production"
ENV JWT_ALGORITHM="HS256"
ENV JWT_EXPIRATION_HOURS="24"

# TTS Configuration
ENV REQUEST_TIMEOUT="300"
ENV MAX_RETRIES="3"

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# CRITICAL: Start the RunPod serverless handler
CMD ["python", "-u", "rp_handler.py"]
