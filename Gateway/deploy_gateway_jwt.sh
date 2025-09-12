set -e

echo "🔐 Deploying TTS Gateway V3 with JWT Authentication..."

# Enhanced configuration
GATEWAY_IMAGE="ghcr.io/aparna0112/tts-gateway:v3-serverless"
ENDPOINT_NAME="tts-gateway-v3-jwt"
JWT_EXPIRATION_HOURS=${JWT_EXPIRATION_HOURS:-24}

# Function to generate random JWT secret
generate_jwt_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Check dependencies
check_dependencies() {
    local deps=("runpod" "openssl" "curl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            echo "❌ Required dependency '$dep' not found"
            exit 1
        fi
    done
}

# Validate environment
validate_environment() {
    if [ -z "$RUNPOD_API_KEY" ]; then
        echo "❌ RUNPOD_API_KEY environment variable is required"
        echo "   Get your API key from: https://www.runpod.io/console/user/settings"
        exit 1
    fi

    if [ -z "$JWT_SECRET_KEY" ]; then
        echo "🔑 Generating secure JWT secret key..."
        JWT_SECRET_KEY=$(generate_jwt_secret)
        echo "Generated JWT Secret: $JWT_SECRET_KEY"
        echo "⚠️ IMPORTANT: Save this JWT secret key securely!"
    fi

    if [ -z "$KOKKORO_ENDPOINT" ]; then
        echo "⚠️ KOKKORO_ENDPOINT not set. You'll need to set this after creating Kokkoro serverless endpoint"
    fi

    if [ -z "$CHATTERBOX_ENDPOINT" ]; then
        echo "⚠️ CHATTERBOX_ENDPOINT not set. You'll need to set this after creating Chatterbox serverless endpoint"
    fi
}

# Deploy with JWT configuration
deploy_gateway_jwt() {
    echo "📋 JWT Deployment Configuration:"
    echo "   Gateway Image: $GATEWAY_IMAGE"
    echo "   Endpoint Name: $ENDPOINT_NAME"
    echo "   JWT Secret: ${JWT_SECRET_KEY:0:10}...${JWT_SECRET_KEY: -5}"
    echo "   JWT Expiration: $JWT_EXPIRATION_HOURS hours"
    echo "   Kokkoro Endpoint: ${KOKKORO_ENDPOINT:-'(not set)'}"
    echo "   Chatterbox Endpoint: ${CHATTERBOX_ENDPOINT:-'(not set)'}"

    echo "🌐 Creating JWT-enabled Gateway endpoint..."
    runpod create endpoint \
        --name "$ENDPOINT_NAME" \
        --image "$GATEWAY_IMAGE" \
        --gpu-count 0 \
        --cpu-count 2 \
        --memory 4 \
        --container-disk 15 \
        --env JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --env JWT_EXPIRATION_HOURS="$JWT_EXPIRATION_HOURS" \
        --env KOKKORO_ENDPOINT="$KOKKORO_ENDPOINT" \
        --env CHATTERBOX_ENDPOINT="$CHATTERBOX_ENDPOINT" \
        --env RUNPOD_API_KEY="$RUNPOD_API_KEY" \
        --env REQUIRE_JWT="true" \
        --ports "8000/http" \
        --volume-size 5

    echo "✅ JWT-enabled Gateway deployment initiated!"
    
    # Save configuration
    cat > gateway_config.json << EOF
{
    "endpoint_name": "$ENDPOINT_NAME",
    "jwt_secret": "$JWT_SECRET_KEY",
    "jwt_expiration_hours": $JWT_EXPIRATION_HOURS,
    "kokkoro_endpoint": "$KOKKORO_ENDPOINT",
    "chatterbox_endpoint": "$CHATTERBOX_ENDPOINT",
    "deployment_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    
    echo "💾 Configuration saved to: gateway_config.json"
    echo ""
    echo "🔐 JWT AUTHENTICATION SETUP:"
    echo "   Secret Key: $JWT_SECRET_KEY"
    echo "   Token Expiration: $JWT_EXPIRATION_HOURS hours"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Wait for deployment to complete"
    echo "   2. Test health: curl https://your-gateway-endpoint/health"
    echo "   3. Generate token: curl -X POST https://your-gateway-endpoint -d '{\"input\":{\"action\":\"generate_token\",\"user_id\":\"test\"}}'"
    echo "   4. Deploy Kokkoro and Chatterbox serverless endpoints"
    echo "   5. Update KOKKORO_ENDPOINT and CHATTERBOX_ENDPOINT environment variables"
}

# Main execution
main() {
    check_dependencies
    validate_environment
    deploy_gateway_jwt
}

main "$@"
