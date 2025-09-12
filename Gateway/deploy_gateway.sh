set -e

echo "🚀 Deploying TTS Gateway V3 to RunPod..."

# Configuration
GATEWAY_IMAGE="ghcr.io/aparna0112/tts-gateway:v3-serverless"
ENDPOINT_NAME="tts-gateway-v3"

# Check if RunPod CLI is installed
if ! command -v runpod &> /dev/null; then
    echo "❌ RunPod CLI not found. Please install it first:"
    echo "pip install runpod"
    exit 1
fi

# Check environment variables
if [ -z "$RUNPOD_API_KEY" ]; then
    echo "❌ RUNPOD_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$JWT_SECRET_KEY" ]; then
    echo "⚠️ JWT_SECRET_KEY not set. Using default (INSECURE for production!)"
    export JWT_SECRET_KEY="tts-gateway-secret-2025"
fi

echo "📋 Deployment Configuration:"
echo "   Gateway Image: $GATEWAY_IMAGE"
echo "   Endpoint Name: $ENDPOINT_NAME"
echo "   JWT Secret: ${JWT_SECRET_KEY:0:10}..."

# Deploy gateway
echo "🌐 Creating Gateway endpoint..."
runpod create endpoint \
    --name "$ENDPOINT_NAME" \
    --image "$GATEWAY_IMAGE" \
    --gpu-count 0 \
    --cpu-count 2 \
    --memory 4 \
    --container-disk 10 \
    --env JWT_SECRET_KEY="$JWT_SECRET_KEY" \
    --env KOKKORO_ENDPOINT="$KOKKORO_ENDPOINT" \
    --env CHATTERBOX_ENDPOINT="$CHATTERBOX_ENDPOINT" \
    --env RUNPOD_API_KEY="$RUNPOD_API_KEY" \
    --ports "8000/http"

echo "✅ Gateway deployment initiated!"
echo "📋 Next steps:"
echo "   1. Wait for deployment to complete"
echo "   2. Test with: curl https://your-gateway-endpoint/health"
echo "   3. Generate JWT tokens for authentication"
