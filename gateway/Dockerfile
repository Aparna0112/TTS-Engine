FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    runpod \
    requests \
    uvicorn \
    fastapi

# Copy the handler script
COPY gateway_handler.py /app/
COPY requirements.txt /app/ 2>/dev/null || echo "runpod\nrequests\nuvicorn\nfastapi" > /app/requirements.txt

# Install any additional requirements
RUN pip install --no-cache-dir -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from gateway_handler import health; print(health())" || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (optional, RunPod handles this)
EXPOSE 8000

# Run the handler
CMD ["python", "-u", "gateway_handler.py"]
