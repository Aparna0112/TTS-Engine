#!/bin/bash

# TTS Gateway Deployment Script
# Save this as: deploy_gateway.sh
# Usage: chmod +x deploy_gateway.sh && ./deploy_gateway.sh

set -e  # Exit on any error

# Configuration
REGISTRY="ghcr.io"
USERNAME="aparna0112"
REPO="tts-engine"
IMAGE_NAME="tts-gateway"
TAG="v$(date +%Y%m%d-%H%M%S)"  # Timestamp-based tag
LATEST_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Verify required files exist
check_files() {
    log_info "Checking required files..."
    
    if [ ! -f "rp_handler.py" ]; then
        log_error "rp_handler.py not found. Please create this file first."
        exit 1
    fi
    
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile not found. Please create this file first."
        exit 1
    fi
    
    log_success "Required files found"
}

# Build the Docker image
build_image() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    log_info "Building Docker image: ${full_image_name}:${TAG}"
    
    # Build for AMD64 platform (required for RunPod)
    docker buildx build \
        --platform linux/amd64 \
        -t "${full_image_name}:${TAG}" \
        -t "${full_image_name}:${LATEST_TAG}" \
        .
    
    if [ $? -eq 0 ]; then
        log_success "Docker image built successfully"
        echo "  Tagged as: ${full_image_name}:${TAG}"
        echo "  Tagged as: ${full_image_name}:${LATEST_TAG}"
    else
        log_error "Docker build failed"
        exit 1
    fi
}

# Test the image locally
test_image() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${LATEST_TAG}"
    
    log_info "Testing the Docker image locally..."
    
    # Test with the --test flag
    docker run --rm \
        -e KOKKORO_ENDPOINT="${KOKKORO_ENDPOINT:-https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync}" \
        -e CHATTERBOX_ENDPOINT="${CHATTERBOX_ENDPOINT:-https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync}" \
        -e RUNPOD_API_KEY="${RUNPOD_API_KEY:-dummy_key_for_test}" \
        "${full_image_name}" \
        python rp_handler.py --test
    
    if [ $? -eq 0 ]; then
        log_success "Local test passed"
    else
        log_warning "Local test failed, but this might be expected without real API keys"
    fi
}

# Push the image
push_image() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    log_info "Pushing Docker image to registry..."
    
    # Check if logged in to registry
    if ! docker info | grep -q "Username"; then
        log_warning "You may need to login to the container registry"
        echo "Run: echo \$GITHUB_TOKEN | docker login ghcr.io -u ${USERNAME} --password-stdin"
    fi
    
    # Push both tags
    docker push "${full_image_name}:${TAG}"
    docker push "${full_image_name}:${LATEST_TAG}"
    
    if [ $? -eq 0 ]; then
        log_success "Docker image pushed successfully"
        echo "  Pushed: ${full_image_name}:${TAG}"
        echo "  Pushed: ${full_image_name}:${LATEST_TAG}"
    else
        log_error "Docker push failed"
        exit 1
    fi
}

# Display next steps
show_next_steps() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    echo ""
    log_success "Deployment completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Go to RunPod Console: https://www.runpod.io/console/serverless"
    echo "2. Edit your TTS Gateway endpoint or create a new one"
    echo "3. Update the Docker image to: ${full_image_name}:${TAG}"
    echo "4. Set environment variables:"
    echo "   - KOKKORO_ENDPOINT=${KOKKORO_ENDPOINT:-https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync}"
    echo "   - CHATTERBOX_ENDPOINT=${CHATTERBOX_ENDPOINT:-https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync}"
    echo "   - RUNPOD_API_KEY=your_runpod_api_key"
    echo "5. Set Min Workers to 1 for testing"
    echo "6. Deploy and test!"
    echo ""
    echo "🧪 Test your endpoint with:"
    echo "curl -X POST 'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -H 'Authorization: Bearer YOUR_API_KEY' \\"
    echo "  -d '{\"input\": {\"action\": \"health\"}}'"
    echo ""
}

# Main execution
main() {
    echo "🚀 TTS Gateway Deployment Script"
    echo "=================================="
    
    check_prerequisites
    check_files
    build_image
    test_image
    
    # Ask user if they want to push
    echo ""
    read -p "Do you want to push the image to the registry? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        push_image
        show_next_steps
    else
        log_info "Skipping push. You can manually push later with:"
        echo "  docker push ${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${TAG}"
        echo "  docker push ${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${LATEST_TAG}"
    fi
}

# Run main function
main "$@"
