FROM python:3.10-slim

WORKDIR /app

# Add labels to link container to repository
LABEL org.opencontainers.image.source=https://github.com/aparna0112/TTS-Engine
LABEL org.opencontainers.image.description="TTS chatterbox serverless container with offline TTS"
LABEL org.opencontainers.image.licenses=MIT

# Install system dependencies for TTS
RUN apt-get update && apt-get install -y \
    curl \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    portaudio19-dev \
    python3-dev \
    gcc \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY handler.py ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

# Run the handler
CMD ["python", "handler.py"]
