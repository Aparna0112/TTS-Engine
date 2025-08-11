#!/bin/bash

echo "Building and deploying TTS system to RunPod..."

# Build images
echo "Building Gateway..."
docker build -t your-registry/tts-gateway:latest ./gateway

echo "Building Kokkoro..."
docker build -t your-registry/tts-kokkoro:latest ./models/kokkoro

echo "Building Chatterbox..."
docker build -t your-registry/tts-chatterbox:latest ./models/chatterbox

# Push to registry
echo "Pushing images..."
docker push your-registry/tts-gateway:latest
docker push your-registry/tts-kokkoro:latest
docker push your-registry/tts-chatterbox:latest

echo "Deploy complete! Create RunPod endpoints using these images."
