import runpod
import os
import jwt
from datetime import datetime, timedelta

# JWT setup
JWT_SECRET = os.getenv('JWT_SECRET')
REQUIRE_JWT = os.getenv('REQUIRE_JWT', 'false').lower() == 'true'

def handler(job):
    job_input = job.get('input', {})
    
    # Skip JWT for health check
    if job_input.get('action') == 'health':
        return {"status": "healthy", "jwt_required": REQUIRE_JWT}
    
    # JWT check - BLOCKS REQUESTS WITHOUT TOKEN
    if REQUIRE_JWT:
        token = job_input.get('auth_token')
        if not token:
            return {"error": "JWT token required"}
        
        try:
            jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except:
            return {"error": "Invalid JWT token"}
    
    # Your existing TTS code here
    text = job_input.get('text', 'Hello world')
    
    # Simple TTS response (replace with your actual TTS logic)
    return {
        "success": True,
        "text": text,
        "message": "TTS processed with JWT authentication"
    }

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
