# 🎵 Modular TTS System

A scalable, microservices-based Text-to-Speech system with multiple TTS engines, deployed on RunPod serverless infrastructure.

## 🏗️ Architecture

- **Gateway Service**: Central API router and load balancer
- **Kokkoro TTS**: High-quality TTS using Google TTS
- **Chatterbox TTS**: Fast and efficient TTS alternative
- **Web Client**: HTML5 audio player for testing
- **CI/CD Pipeline**: Automated building and deployment

## 🚀 Quick Start

### 1. Deploy to RunPod

1. **Fork this repository**
2. **GitHub Actions will automatically build containers**
3. **Create 3 RunPod endpoints:**
   - Gateway: `ghcr.io/your-username/repo-name/tts-gateway:latest`
   - Kokkoro: `ghcr.io/your-username/repo-name/tts-kokkoro:latest`
   - Chatterbox: `ghcr.io/your-username/repo-name/tts-chatterbox:latest`

### 2. Configure Gateway

Set environment variables in Gateway endpoint:
