# Use Python 3.10 slim image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
# Install runpod first as it's the most critical
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    runpod>=1.5.0 \
    requests>=2.31.0 \
    urllib3>=1.26.0

# Copy the handler file
# IMPORTANT: This must be named rp_handler.py for RunPod
COPY rp_handler.py /app/

# Set environment variables for Python
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Add health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Create a non-root user for security (optional)
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Default command to start the RunPod handler
# CRITICAL: This must call the rp_handler.py file
CMD ["python", "-u", "rp_handler.py"]
