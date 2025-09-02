# gateway/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Environment variables
ENV JWT_SECRET_KEY=your-super-secret-key-change-in-production
ENV KOKKORO_URL=http://kokkoro-service:8001
ENV CHATTERBOX_URL=http://chatterbox-service:8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# docker-compose.yml (Updated with authentication)
version: '3.8'

services:
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET_KEY=your-super-secret-key-change-in-production-make-it-long-and-random
      - KOKKORO_URL=http://kokkoro-service:8001
      - CHATTERBOX_URL=http://chatterbox-service:8002
    depends_on:
      - kokkoro-service
      - chatterbox-service
    networks:
      - tts-network

  kokkoro-service:
    build: ./models/kokkoro
    ports:
      - "8001:8001"
    networks:
      - tts-network

  chatterbox-service:
    build: ./models/chatterbox
    ports:
      - "8002:8002"
    networks:
      - tts-network

networks:
  tts-network:
    driver: bridge
