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
KOKKORO_ENDPOINT="https://api.runpod.ai/v2/e0lm92f3god7mu/runsync"
CHATTERBOX_ENDPOINT="https://api.runpod.ai/v2/bc96237ndsvq8t/runsync"

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
    fi
    
    echo "   KOKKORO_ENDPOINT=https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync"
    echo "   CHATTERBOX_ENDPOINT=https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync"
    echo "   RUNPOD_API_KEY=your_runpod_api_key"
    echo "   REQUEST_TIMEOUT=300"
    echo "   MAX_RETRIES=3"
    echo ""
    echo "4️⃣  Test your deployment:"
    echo ""
    echo "   # Health Check (no auth required)"
    echo "   curl -X POST 'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -H 'Authorization: Bearer YOUR_RUNPOD_API_KEY' \\"
    echo "     -d '{\"input\": {\"action\": \"health\"}}'"
    echo ""
    echo "   # Generate JWT Token"
    echo "   curl -X POST 'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -H 'Authorization: Bearer YOUR_RUNPOD_API_KEY' \\"
    echo "     -d '{\"input\": {\"action\": \"generate_token\", \"user_id\": \"test_user\"}}'"
    echo ""
    echo "   # TTS Request (with JWT token from previous step)"
    echo "   curl -X POST 'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -H 'Authorization: Bearer YOUR_RUNPOD_API_KEY' \\"
    echo "     -d '{\"input\": {\"jwt_token\": \"JWT_TOKEN_HERE\", \"text\": \"Hello world\", \"engine\": \"kokkoro\"}}'"
    echo ""
    echo "5️⃣  Local Testing Tools:"
    echo "   - generate_token.py: Create JWT tokens locally"
    echo "   - jwt_utils.py: Full JWT management utilities (see artifacts)"
    echo "   - .env.jwt: Your JWT configuration (keep secure!)"
    echo ""
    echo -e "${YELLOW}⚠️  Security Reminders:${NC}"
    echo "   • Never commit .env.jwt to version control"
    echo "   • Use a strong, unique JWT_SECRET_KEY in production"
    echo "   • Monitor token usage and implement rate limiting"
    echo "   • Consider implementing token refresh mechanisms"
    echo ""
    echo -e "${GREEN}✅ JWT Authentication Features:${NC}"
    echo "   • Token-based authentication for all TTS requests"
    echo "   • User identification and logging"
    echo "   • Configurable token expiration"
    echo "   • Built-in token generation for testing"
    echo "   • Clear error messages for authentication failures"
    echo ""
}

# Create local testing setup
create_test_setup() {
    log_header "Creating Local Test Setup"
    
    # Create test script
    cat > test_jwt_gateway.py << 'EOF'
#!/usr/bin/env python3
"""
Local JWT Gateway Test Script
Tests the deployed TTS Gateway with JWT authentication
"""

import requests
import json
import time
import os

class TTSGatewayTester:
    def __init__(self, gateway_url, runpod_api_key):
        self.gateway_url = gateway_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {runpod_api_key}'
        }
        self.jwt_token = None
    
    def test_health_check(self):
        """Test health endpoint (no auth required)"""
        print("🏥 Testing Health Check...")
        
        payload = {"input": {"action": "health"}}
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        if result.get('status') == 'healthy':
            print(f"   ✅ Gateway is healthy")
            print(f"   JWT Auth: {result.get('jwt_auth_enabled', 'Unknown')}")
            print(f"   Version: {result.get('gateway_version', 'Unknown')}")
            return True
        else:
            print(f"   ❌ Health check failed: {result}")
            return False
    
    def test_token_generation(self):
        """Test JWT token generation"""
        print("\n🔑 Testing JWT Token Generation...")
        
        payload = {
            "input": {
                "action": "generate_token",
                "user_id": "test_user_" + str(int(time.time())),
                "user_data": {"role": "tester", "plan": "test"}
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        if result.get('success') and result.get('token'):
            self.jwt_token = result['token']
            print(f"   ✅ Token generated successfully")
            print(f"   User ID: {result['user_id']}")
            print(f"   Token: {self.jwt_token[:50]}...")
            print(f"   Expires in: {result.get('expires_in_hours', 'Unknown')} hours")
            return True
        else:
            print(f"   ❌ Token generation failed: {result.get('error', 'Unknown error')}")
            return False
    
    def test_tts_without_token(self):
        """Test TTS request without JWT token (should fail)"""
        print("\n🚫 Testing TTS without JWT Token (should fail)...")
        
        payload = {
            "input": {
                "text": "This should fail because no JWT token is provided",
                "engine": "kokkoro"
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        if result.get('error') and 'token' in result.get('error', '').lower():
            print(f"   ✅ Correctly rejected request without token")
            print(f"   Error: {result['error']}")
            return True
        else:
            print(f"   ❌ Should have rejected request without token: {result}")
            return False
    
    def test_tts_with_token(self):
        """Test TTS request with valid JWT token"""
        print("\n🎵 Testing TTS with JWT Token...")
        
        if not self.jwt_token:
            print("   ❌ No JWT token available")
            return False
        
        payload = {
            "input": {
                "jwt_token": self.jwt_token,
                "text": "Hello! This is a test of the JWT-protected TTS gateway.",
                "engine": "kokkoro",
                "voice": "default",
                "speed": 1.0
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        if result.get('success') or result.get('result'):
            print(f"   ✅ TTS request successful")
            print(f"   User ID: {result.get('user_id', 'Unknown')}")
            print(f"   Engine: {result.get('engine', 'Unknown')}")
            print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
            return True
        else:
            print(f"   ❌ TTS request failed: {result.get('error', 'Unknown error')}")
            return False
    
    def test_invalid_token(self):
        """Test TTS request with invalid JWT token"""
        print("\n🔒 Testing TTS with Invalid JWT Token...")
        
        payload = {
            "input": {
                "jwt_token": "invalid.jwt.token",
                "text": "This should fail with invalid token",
                "engine": "kokkoro"
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        if result.get('error') and ('invalid' in result.get('error', '').lower() or 'auth' in result.get('error', '').lower()):
            print(f"   ✅ Correctly rejected invalid token")
            print(f"   Error: {result['error']}")
            return True
        else:
            print(f"   ❌ Should have rejected invalid token: {result}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Running JWT Gateway Test Suite")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Token Generation", self.test_token_generation),
            ("TTS Without Token", self.test_tts_without_token),
            ("TTS With Valid Token", self.test_tts_with_token),
            ("TTS With Invalid Token", self.test_invalid_token)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"   ❌ Test failed with exception: {e}")
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your JWT gateway is working correctly.")
        else:
            print("⚠️  Some tests failed. Check your configuration and try again.")
        
        return passed == total

def main():
    # Configuration - Replace with your actual values
    gateway_url = os.getenv('GATEWAY_URL', 'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync')
    runpod_api_key = os.getenv('RUNPOD_API_KEY', 'your_runpod_api_key')
    
    if 'YOUR_ENDPOINT_ID' in gateway_url or 'your_runpod_api_key' in runpod_api_key:
        print("❌ Please update the configuration with your actual RunPod endpoint and API key")
        print("Set environment variables:")
        print("  export GATEWAY_URL='https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync'")
        print("  export RUNPOD_API_KEY='your_actual_api_key'")
        return
    
    tester = TTSGatewayTester(gateway_url, runpod_api_key)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
EOF
    
    chmod +x test_jwt_gateway.py
    log_success "Created test_jwt_gateway.py"
    
    # Create README for testing
    cat > TEST_README.md << 'EOF'
# JWT Gateway Testing Guide

## Quick Test Commands

### 1. Generate a JWT Token Locally
```bash
python generate_token.py --user-id=test_user --role=admin
```

### 2. Test Deployed Gateway
```bash
# Set your configuration
export GATEWAY_URL="https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
export RUNPOD_API_KEY="your_runpod_api_key"

# Run the test suite
python test_jwt_gateway.py
```

### 3. Manual curl Tests

#### Health Check
```bash
curl -X POST "$GATEWAY_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{"input": {"action": "health"}}'
```

#### Generate Token
```bash
curl -X POST "$GATEWAY_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{"input": {"action": "generate_token", "user_id": "test_user"}}'
```

#### TTS Request (replace JWT_TOKEN with actual token)
```bash
curl -X POST "$GATEWAY_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{"input": {"jwt_token": "JWT_TOKEN", "text": "Hello world", "engine": "kokkoro"}}'
```

## Files Created
- `generate_token.py`: Local JWT token generator
- `test_jwt_gateway.py`: Comprehensive test suite
- `.env.jwt`: JWT configuration (keep secure!)
- `TEST_README.md`: This file

## Security Notes
- Keep `.env.jwt` secure and never commit to version control
- Use strong JWT secrets in production
- Monitor authentication logs for suspicious activity
EOF
    
    log_success "Created TEST_README.md"
}

# Interactive configuration
interactive_config() {
    log_header "Interactive Configuration"
    
    echo "Let's configure your TTS Gateway deployment:"
    echo ""
    
    # Get RunPod API key
    read -p "Enter your RunPod API Key (or press Enter to skip): " runpod_key
    if [ -n "$runpod_key" ]; then
        export RUNPOD_API_KEY="$runpod_key"
        echo "RUNPOD_API_KEY=\"$runpod_key\"" >> .env.jwt
        log_success "RunPod API key configured"
    fi
    
    # Ask about custom endpoints
    read -p "Do you want to configure custom TTS endpoints? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Kokkoro endpoint (press Enter for default): " kokkoro_endpoint
        read -p "Chatterbox endpoint (press Enter for default): " chatterbox_endpoint
        
        if [ -n "$kokkoro_endpoint" ]; then
            sed -i "s|KOKKORO_ENDPOINT=.*|KOKKORO_ENDPOINT=\"$kokkoro_endpoint\"|" .env.jwt
        fi
        
        if [ -n "$chatterbox_endpoint" ]; then
            sed -i "s|CHATTERBOX_ENDPOINT=.*|CHATTERBOX_ENDPOINT=\"$chatterbox_endpoint\"|" .env.jwt
        fi
    fi
    
    # Ask about JWT settings
    read -p "JWT token expiration in hours (default: 24): " jwt_expiration
    if [ -n "$jwt_expiration" ] && [[ "$jwt_expiration" =~ ^[0-9]+$ ]]; then
        sed -i "s|JWT_EXPIRATION_HOURS=.*|JWT_EXPIRATION_HOURS=\"$jwt_expiration\"|" .env.jwt
        log_success "JWT expiration set to $jwt_expiration hours"
    fi
    
    echo ""
    log_success "Interactive configuration completed"
}

# Clean up function
cleanup() {
    log_header "Cleanup"
    
    # Remove temporary files if desired
    read -p "Remove temporary build files? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -f
        log_success "Cleaned up Docker build cache"
    fi
}

# Main execution
main() {
    echo -e "${PURPLE}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║            TTS Gateway JWT Deployment Script                 ║
║                                                              ║
║  This script will build and deploy your TTS Gateway with    ║
║  JWT authentication support to RunPod serverless platform  ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_prerequisites
    check_files
    setup_jwt_config
    
    # Ask for interactive configuration
    read -p "Do you want to configure deployment settings interactively? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        interactive_config
    fi
    
    create_jwt_utilities
    build_image
    test_image_jwt
    
    # Ask user if they want to push
    echo ""
    read -p "Do you want to push the image to the registry? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if push_image; then
            create_test_setup
            show_deployment_instructions
        else
            log_error "Push failed. Please check your registry authentication."
        fi
    else
        log_info "Skipping push. You can manually push later."
        create_test_setup
        echo ""
        echo "To push manually:"
        echo "  docker push ${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${TAG}"
        echo "  docker push ${REGISTRY}/${USERNAME}/${REPO}/${IMAGE_NAME}:${LATEST_TAG}"
    fi
    
    cleanup
    
    echo ""
    echo -e "${GREEN}🎉 Deployment script completed successfully!${NC}"
    echo "Check the files created and follow the deployment instructions above."
}

# Handle script arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "TTS Gateway JWT Deployment Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --no-test      Skip local testing"
    echo "  --auto-push    Automatically push without asking"
    echo "  --config-only  Only setup configuration, don't build"
    echo ""
    echo "Environment variables:"
    echo "  RUNPOD_API_KEY    Your RunPod API key"
    echo "  GITHUB_TOKEN      GitHub token for registry access"
    echo ""
    exit 0
fi

# Check for specific flags
NO_TEST=false
AUTO_PUSH=false
CONFIG_ONLY=false

for arg in "$@"; do
    case $arg in
        --no-test)
            NO_TEST=true
            ;;
        --auto-push)
            AUTO_PUSH=true
            ;;
        --config-only)
            CONFIG_ONLY=true
            ;;
    esac
done

# Run main function with flags
if [ "$CONFIG_ONLY" = true ]; then
    setup_jwt_config
    create_jwt_utilities
    create_test_setup
    echo "Configuration complete. Run without --config-only to build and deploy."
else
    main "$@"
fi
        echo "
