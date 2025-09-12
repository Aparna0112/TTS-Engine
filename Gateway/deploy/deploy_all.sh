set -e

echo "🚀 Deploying Complete TTS V3 Serverless System..."

# Check environment variables
check_env() {
    if [ -z "$RUNPOD_API_KEY" ]; then
        echo "❌ RUNPOD_API_KEY is required"
        exit 1
    fi
    
    if [ -z "$JWT_SECRET_KEY" ]; then
        echo "🔑 Generating JWT secret..."
        export JWT_SECRET_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
        echo "Generated JWT Secret: $JWT_SECRET_KEY"
    fi
}

# Deploy models
deploy_models() {
    echo "🎭 Deploying Chatterbox serverless..."
    CHATTERBOX_ENDPOINT=$(runpod create endpoint \
        --name "chatterbox-v3-serverless" \
        --image "ghcr.io/aparna0112/tts-chatterbox:v3-real-chatterbox" \
        --gpu-count 1 \
        --gpu-type "NVIDIA GeForce RTX 4090" \
        --cpu-count 8 \
        --memory 32 \
        --container-disk 50 \
        --env JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --env REQUIRE_JWT="true" \
        --output json | jq -r '.endpoint_url')
    
    echo "🎌 Deploying Kokkoro serverless..."
    KOKKORO_ENDPOINT=$(runpod create endpoint \
        --name "kokkoro-v3-serverless" \
        --image "ghcr.io/aparna0112/tts-kokkoro:v3-real-model" \
        --gpu-count 1 \
        --gpu-type "NVIDIA GeForce RTX 4090" \
        --cpu-count 8 \
        --memory 32 \
        --container-disk 50 \
        --env JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --env REQUIRE_JWT="true" \
        --output json | jq -r '.endpoint_url')
    
    export CHATTERBOX_ENDPOINT
    export KOKKORO_ENDPOINT
    
    echo "✅ Models deployed:"
    echo "   Chatterbox: $CHATTERBOX_ENDPOINT"
    echo "   Kokkoro: $KOKKORO_ENDPOINT"
}

# Deploy gateway
deploy_gateway() {
    echo "🌐 Deploying Gateway..."
    GATEWAY_ENDPOINT=$(runpod create endpoint \
        --name "tts-gateway-v3-serverless" \
        --image "ghcr.io/aparna0112/tts-gateway:v3-serverless" \
        --gpu-count 0 \
        --cpu-count 2 \
        --memory 4 \
        --container-disk 15 \
        --env JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --env KOKKORO_ENDPOINT="$KOKKORO_ENDPOINT" \
        --env CHATTERBOX_ENDPOINT="$CHATTERBOX_ENDPOINT" \
        --env RUNPOD_API_KEY="$RUNPOD_API_KEY" \
        --output json | jq -r '.endpoint_url')
    
    export GATEWAY_ENDPOINT
    
    echo "✅ Gateway deployed: $GATEWAY_ENDPOINT"
}

# Save configuration
save_config() {
    cat > deployment_config.json << EOF
{
    "deployment_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "jwt_secret": "$JWT_SECRET_KEY",
    "endpoints": {
        "gateway": "$GATEWAY_ENDPOINT",
        "chatterbox": "$CHATTERBOX_ENDPOINT",
        "kokkoro": "$KOKKORO_ENDPOINT"
    },
    "features": [
        "serverless_architecture",
        "real_model_voices",
        "mp3_output",
        "voice_cloning",
        "japanese_support",
        "jwt_authentication"
    ]
}
EOF
    
    echo "💾 Configuration saved to deployment_config.json"
}

# Test deployment
test_deployment() {
    echo "🧪 Testing deployment..."
    
    # Wait for endpoints to be ready
    echo "⏳ Waiting for endpoints to initialize..."
    sleep 60
    
    # Test gateway health
    echo "Testing gateway health..."
    curl -s "$GATEWAY_ENDPOINT/health" | jq '.'
    
    # Generate test token
    echo "Generating test token..."
    TOKEN=$(curl -s -X POST "$GATEWAY_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d '{"input":{"action":"generate_token","user_id":"deployment_test"}}' | jq -r '.token')
    
    # Test Chatterbox
    echo "Testing Chatterbox TTS..."
    curl -s -X POST "$GATEWAY_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{\"input\":{\"jwt_token\":\"$TOKEN\",\"text\":\"Hello! Testing Chatterbox serverless.\",\"engine\":\"chatterbox\",\"format\":\"mp3\"}}" | jq '.'
    
    # Test Kokkoro
    echo "Testing Kokkoro TTS..."
    curl -s -X POST "$GATEWAY_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{\"input\":{\"jwt_token\":\"$TOKEN\",\"text\":\"こんにちは！ココロです！\",\"engine\":\"kokkoro\",\"format\":\"mp3\"}}" | jq '.'
    
    echo "✅ Basic tests completed!"
}

# Main deployment process
main() {
    echo "🎯 TTS V3 Serverless System Deployment"
    echo "======================================"
    
    check_env
    deploy_models
    deploy_gateway
    save_config
    test_deployment
    
    echo ""
    echo "🎉 DEPLOYMENT COMPLETE!"
    echo ""
    echo "📋 System Overview:"
    echo "   Gateway: $GATEWAY_ENDPOINT"
    echo "   Chatterbox: $CHATTERBOX_ENDPOINT"
    echo "   Kokkoro: $KOKKORO_ENDPOINT"
    echo ""
    echo "🔑 JWT Secret: $JWT_SECRET_KEY"
    echo ""
    echo "📱 Quick Test:"
    echo "   curl '$GATEWAY_ENDPOINT/health'"
    echo ""
    echo "📚 Full documentation in deployment_config.json"
}

main "$@"
