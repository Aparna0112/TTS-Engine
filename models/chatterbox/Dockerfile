FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY handler.py .
COPY app.py .

# Create directories for audio prompts and models
RUN mkdir -p /app/audio_prompts /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Pre-download the Chatterbox model for faster cold starts
# This downloads ~2GB but significantly reduces first-request latency
RUN python -c "from chatterbox.tts import ChatterboxTTS; ChatterboxTTS.from_pretrained(device='cpu')" || echo "Model download will happen at runtime"

# Health check to verify GPU and model availability
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import torch; print('GPU available:', torch.cuda.is_available())"

# Expose port (matching your existing setup)
EXPOSE 8000

# Run the handler
CMD ["python", "handler.py"]
