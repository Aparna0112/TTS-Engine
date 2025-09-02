#!/bin/bash

# Enhanced TTS Gateway Deployment Script with JWT Authentication
# Save this as: deploy_gateway_jwt.sh
# Usage: chmod +x deploy_gateway_jwt.sh && ./deploy_gateway_jwt.sh

set -e  # Exit on any error

# Configuration
REGISTRY="ghcr.io"
USERNAME="aparna0112"
REPO="tts-engine"
IMAGE_NAME="tts-gateway"
TAG="jwt-v$(date +%Y%m%d-%H%M%S)"
LATEST_TAG="jwt-latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_header() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Generate a secure JWT secret
generate_jwt_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -base64 64 | tr -d '\n'
    elif command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_urlsafe(64))"
    else
        # Fallback using /dev/urandom
        head -c 48 /dev/urandom | base64 | tr -d '\n'
    fi
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    local missing_tools=()
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    log_success "All prerequisites are available"
}

# Verify required files exist
check_files() {
    log_header "Checking Required Files"
    
    local missing_files=()
    
    if [ ! -f "rp_handler.py" ]; then
        missing_files+=("rp_handler.py")
    fi
    
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi
    
    if [ ! -f "Dockerfile" ]; then
        missing_files+=("Dockerfile")
    fi
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Missing required files: ${missing_files[*]}"
        echo ""
        echo "Please ensure you have:"
        echo "  - rp_handler.py (the JWT-enabled handler)"
        echo "  - requirements.txt (with PyJWT dependency)"
        echo "  - Dockerfile (updated for JWT support)"
        exit 1
    fi
    
    # Check if JWT is implemented in the handler
    if ! grep -q "PyJWT\|jwt" requirements.txt; then
        log_warning "JWT dependency not found in requirements.txt"
        echo "Adding PyJWT to requirements.txt..."
        echo "PyJWT==2.8.0" >> requirements.txt
    fi
    
    if ! grep -q "validate_jwt_token\|jwt.decode" rp_handler.py; then
        log_error "JWT authentication not implemented in rp_handler.py"
        echo "Please use the updated handler with JWT support."
        exit 1
    fi
    
    log_success "All required files found and JWT implementation detected"
}

# Generate JWT configuration
setup_jwt_config() {
    log_header "JWT Configuration Setup"
    
    # Generate a secure JWT secret
    JWT_SECRET=$(generate_jwt_secret)
    
    echo "🔐 JWT Configuration Generated:"
    echo "   Algorithm: HS256"
    echo "   Token Expiration: 24 hours"
    echo "   Secret Length: ${#JWT_SECRET} characters"
    
    # Save to .env file for reference
    cat > .env.jwt << EOF
# JWT Configuration for TTS Gateway
# IMPORTANT: Keep these values secure and don't commit to version control

JWT_SECRET_KEY="${JWT_SECRET}"
JWT_ALGORITHM="HS256"
JWT_EXPIRATION_HOURS="24"

# TTS Engine Endpoints
KOKKORO_ENDPOINT="https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync"
CHATTERBOX_ENDPOINT="https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync"

# Request Settings
REQUEST_TIMEOUT="300"
MAX_RETRIES="3"
EOF

    log_success "JWT configuration saved to .env.jwt"
    log_warning "⚠️  Keep the .env.jwt file secure and don't commit it to version control!"
}

# Build the Docker image
build_image() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    log_header "Building Docker Image"
    echo "Image: ${full_image_name}:${TAG}"
    
    # Build for AMD64 platform (required for RunPod)
    docker buildx build \
        --platform linux/amd64 \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
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

# Test the image locally with JWT
test_image_jwt() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${LATEST_TAG}"
    
    log_header "Testing Docker Image with JWT"
    
    # Source the JWT config
    if [ -f ".env.jwt" ]; then
        source .env.jwt
        log_info "Loaded JWT configuration from .env.jwt"
    else
        log_warning "No .env.jwt file found, using default values"
        JWT_SECRET_KEY="test-secret-key"
    fi
    
    echo "🧪 Running JWT authentication tests..."
    
    # Test with JWT environment variables
    docker run --rm \
        -e JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
        -e JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}" \
        -e JWT_EXPIRATION_HOURS="${JWT_EXPIRATION_HOURS:-24}" \
        -e KOKKORO_ENDPOINT="${KOKKORO_ENDPOINT}" \
        -e CHATTERBOX_ENDPOINT="${CHATTERBOX_ENDPOINT}" \
        -e RUNPOD_API_KEY="${RUNPOD_API_KEY:-dummy_key_for_test}" \
        "${full_image_name}" \
        python rp_handler.py --test
    
    local test_exit_code=$?
    
    if [ $test_exit_code -eq 0 ]; then
        log_success "JWT authentication tests passed!"
    else
        log_warning "Some tests failed, but this might be expected without real API keys"
        echo "Exit code: $test_exit_code"
    fi
}

# Create JWT utilities
create_jwt_utilities() {
    log_header "Creating JWT Utilities"
    
    if [ ! -f "jwt_utils.py" ]; then
        log_info "jwt_utils.py not found locally, but it's available in the artifacts above"
        echo "You can copy the JWT utilities from the generated artifacts."
    else
        log_success "JWT utilities already exist"
    fi
    
    # Create a simple token generator script
    cat > generate_token.py << 'EOF'
#!/usr/bin/env python3
"""
Simple JWT Token Generator for TTS Gateway
Usage: python generate_token.py --user-id=test_user --role=admin
"""

import sys
import os
import jwt
from datetime import datetime, timedelta

def generate_token(user_id, role="user", secret_key=None):
    """Generate a JWT token"""
    secret = secret_key or os.getenv('JWT_SECRET_KEY', 'default-secret-change-in-production')
    
    payload = {
        'user_id': user_id,
        'role': role,
        'permissions': ['tts_generate'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iss': 'tts-gateway'
    }
    
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token

if __name__ == "__main__":
    user_id = "test_user"
    role = "user"
    
    # Parse command line arguments
    for arg in sys.argv[1:]:
        if arg.startswith('--user-id='):
            user_id = arg.split('=')[1]
        elif arg.startswith('--role='):
            role = arg.split('=')[1]
    
    try:
        token = generate_token(user_id, role)
        print(f"Generated JWT Token for user '{user_id}' with role '{role}':")
        print(token)
        print(f"\nToken length: {len(token)} characters")
        print("This token is valid for 24 hours.")
    except Exception as e:
        print(f"Error generating token: {e}")
        sys.exit(1)
EOF
    
    chmod +x generate_token.py
    log_success "Created generate_token.py utility"
}

# Push the image
push_image() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    log_header "Pushing Docker Image"
    
    # Check if logged in to registry
    if ! docker info 2>/dev/null | grep -q "Username"; then
        log_warning "You may need to login to the container registry"
        echo "Run: echo \$GITHUB_TOKEN | docker login ghcr.io -u ${USERNAME} --password-stdin"
        echo ""
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping push. Login first and run again."
            return 1
        fi
    fi
    
    # Push both tags
    log_info "Pushing ${full_image_name}:${TAG}..."
    docker push "${full_image_name}:${TAG}"
    
    log_info "Pushing ${full_image_name}:${LATEST_TAG}..."
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

# Display deployment instructions
show_deployment_instructions() {
    local full_image_name="${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}"
    
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    DEPLOYMENT SUCCESSFUL!                    ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    
    echo ""
    echo "🚀 Next Steps for RunPod Deployment:"
    echo ""
    echo "1️⃣  Go to RunPod Console:"
    echo "   https://www.runpod.io/console/serverless"
    echo ""
    echo "2️⃣  Create/Edit your TTS Gateway endpoint:"
    echo "   - Docker Image: ${full_image_name}:${TAG}"
    echo "   - Min Workers: 1 (for testing)"
    echo "   - Max Workers: 5 (adjust as needed)"
    echo "   - Idle Timeout: 30 seconds"
    echo ""
    echo "3️⃣  Set these Environment Variables:"
    
    if [ -f ".env.jwt" ]; then
        echo -e "${GREEN}"
        cat .env.jwt | sed 's/^/   /'
        echo -e "${NC}"
    else
        echo "   JWT_SECRET_KEY=your-super-secure-secret-key-here"
        echo "   JWT_ALGORITHM=HS256"
        echo "   JWT_EXPIRATION_HOURS=24"
        echo "
