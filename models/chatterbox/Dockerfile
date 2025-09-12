FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /app

# Install system dependencies including FFmpeg (same as your repo needs)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the serverless handler
COPY handler.py .

# Create directories for voice storage (serverless compatible)
RUN mkdir -p /tmp/voices /tmp/audio

# Pre-download the Chatterbox model (same as your repo approach)
RUN python -c "from chatterbox.src.chatterbox.tts import ChatterboxTTS; ChatterboxTTS.from_pretrained(device='cpu')" || \
    python -c "from chatterbox.tts import ChatterboxTTS; ChatterboxTTS.from_pretrained(device='cpu')" || \
    echo "Model will download at runtime"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import torch; print('GPU:', torch.cuda.is_available())" && \
      ffmpeg -version > /dev/null

CMD ["python", "handler.py"]
