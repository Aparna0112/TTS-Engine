FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /app

# Install system dependencies including FFmpeg for MP3 conversion
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY handler.py .
COPY app.py .

# Create directories for models and audio
RUN mkdir -p /app/models /app/audio_prompts /app/output

# Download/copy your Kokkoro model files
# COPY models/ /app/models/  # Copy your Kokkoro model files
# RUN python -c "import kokkoro_tts; kokkoro_tts.download_models()"  # Or download script

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import torch; print('GPU:', torch.cuda.is_available())" && \
      ffmpeg -version > /dev/null

EXPOSE 8001
CMD ["python", "handler.py"]
