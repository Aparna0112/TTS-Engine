# TTS-Engine
Separate containers for each TTS
# Modular TTS System

A scalable Text-to-Speech system supporting multiple models with RunPod deployment.

## Features

- **Modular Architecture**: Each TTS model runs in separate containers
- **Centralized Gateway**: Single API endpoint routing to appropriate models  
- **RunPod Ready**: Built for serverless deployment on RunPod
- **Easily Extensible**: Add new models by following the template
- **Health Monitoring**: Built-in health checks and monitoring

## Quick Start

### Local Development
```bash
git clone <your-repo>
cd tts-system
docker-compose up --build
