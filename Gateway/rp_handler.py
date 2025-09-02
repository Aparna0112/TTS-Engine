#!/usr/bin/env python3
"""
TTS Gateway RunPod Handler with JWT Authentication
Save this file as: gateway/rp_handler.py

This file includes JWT token validation before processing TTS requests.
"""

import runpod
import requests
import os
import time
import logging
import json
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

# Request settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token and return payload if valid
    
    Args:
        token: JWT token string
        
    Returns:
        Dict with 'valid' boolean and either 'payload' or 'error'
    """
    if not token:
        return {
            'valid': False,
            'error': 'JWT token is required'
        }
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode and validate the token
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Check if token has expired (additional validation)
        exp_timestamp = payload.get('exp')
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
            return {
                'valid': False,
                'error': 'JWT token has expired'
            }
        
        logger.info(f"✅ JWT token validated successfully for user: {payload.get('user_id', 'unknown')}")
        return {
            'valid': True,
            'payload': payload
        }
        
    except jwt.ExpiredSignatureError:
        return {
            'valid': False,
            'error': 'JWT token has expired'
        }
    except jwt.InvalidTokenError as e:
        return {
            'valid': False,
            'error': f'Invalid JWT token: {str(e)}'
        }
    except Exception as e:
        logger.error(f"JWT validation error: {str(e)}")
        return {
            'valid': False,
            'error': f'JWT validation failed: {str(e)}'
        }

def generate_jwt_token(user_id: str, user_data: Optional[Dict] = None) -> str:
    """
    Generate a JWT token (for testing purposes)
    
    Args:
        user_id: Unique user identifier
        user_data: Optional additional user data
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    
    if user_data:
        payload.update(user_data)
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod handler function with JWT authentication
    
    Args:
        job: RunPod job object containing 'input' and 'id'
        
    Returns:
        Dictionary response that gets sent back to the client
    """
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        # Log that we're processing a request
        logger.info(f"🎯 TTS Gateway: Processing job {job_id}")
        
        # Get the input from the job
        job_input = job.get('input', {})
        logger.info(f"📝 Job input keys: {list(job_input.keys())}")
        
        # Handle health check requests (no auth required)
        if job_input.get('action') == 'health':
            logger.info(f"💊 Health check requested for job {job_id}")
            return {
                "status": "healthy",
                "gateway_version": "1.1.0",
                "available_engines": ["kokkoro", "chatterbox"],
                "endpoints": {
                    "kokkoro": KOKKORO_ENDPOINT,
                    "chatterbox": CHATTERBOX_ENDPOINT
                },
                "jwt_auth_enabled": True,
                "timestamp": time.time(),
                "job_id": job_id,
                "message": "TTS Gateway is running with JWT authentication!"
            }
        
        # Handle token generation requests (for testing)
        if job_input.get('action') == 'generate_token':
            user_id = job_input.get('user_id', 'test_user')
            user_data = job_input.get('user_data', {})
            
            token = generate_jwt_token(user_id, user_data)
            
            logger.info(f"🔑 Generated JWT token for user: {user_id}")
            return {
                "success": True,
                "token": token,
                "user_id": user_id,
                "expires_in_hours": JWT_EXPIRATION_HOURS,
                "message": "JWT token generated successfully",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # For all TTS requests, validate JWT token
        jwt_token = job_input.get('jwt_token') or job_input.get('token') or job_input.get('authorization')
        
        if not jwt_token:
            logger.warning(f"🔒 Job {job_id}: No JWT token provided")
            return {
                "error": "Authentication required: Please provide a valid JWT token",
                "message": "Include 'jwt_token' in your request input",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "help": "Generate a token using: {'action': 'generate_token', 'user_id': 'your_id'}"
            }
        
        # Validate the JWT token
        token_validation = validate_jwt_token(jwt_token)
        
        if not token_validation['valid']:
            logger.error(f"🔒 Job {job_id}: Invalid JWT token - {token_validation['error']}")
            return {
                "error": f"Authentication failed: {token_validation['error']}",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "help": "Generate a new token using: {'action': 'generate_token', 'user_id': 'your_id'}"
            }
        
        # Token is valid, extract user info
        token_payload = token_validation['payload']
        user_id = token_payload.get('user_id', 'unknown')
        logger.info(f"🔓 Job {job_id}: Authenticated user: {user_id}")
        
        # Validate input for TTS requests
        if not job_input.get('text'):
            logger.error(f"❌ Job {job_id}: Missing 'text' parameter")
            return {
                "error": "Missing required parameter: 'text'",
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        text = job_input['text']
        engine = job_input.get('engine', 'kokkoro').lower()
        
        # Validate engine
        if engine not in ['kokkoro', 'chatterbox']:
            logger.error(f"❌ Job {job_id}: Invalid engine '{engine}'")
            return {
                "error": f"Invalid engine '{engine}'. Available: kokkoro, chatterbox",
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"🎵 Job {job_id}: Processing TTS for user {user_id} with {engine} engine")
        logger.info(f"📄 Job {job_id}: Text length: {len(text)} characters")
        
        # Prepare the TTS request
        tts_payload = {
            'text': text,
            'voice': job_input.get('voice', 'default'),
            'speed': job_input.get('speed', 1.0)
        }
        
        # Add engine-specific parameters
        if engine == 'kokkoro':
            tts_payload.update({
                'language': job_input.get('language', 'en'),
                'speaker_id': job_input.get('speaker_id', 0)
            })
        elif engine == 'chatterbox':
            tts_payload.update({
                'model': job_input.get('model', 'default'),
                'format': job_input.get('format', 'wav')
            })
        
        # Select the appropriate endpoint
        endpoint_url = KOKKORO_ENDPOINT if engine == 'kokkoro' else CHATTERBOX_ENDPOINT
        
        # Call the TTS endpoint
        result = call_tts_endpoint(endpoint_url, tts_payload, job_id, user_id)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info(f"✅ Job {job_id}: Completed successfully for user {user_id} in {processing_time:.2f}s")
            return {
                "success": True,
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "text_length": len(text),
                "processing_time": processing_time,
                "result": result['data'],
                "endpoint_used": endpoint_url,
                "authenticated": True
            }
        else:
            logger.error(f"❌ Job {job_id}: TTS processing failed for user {user_id}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "processing_time": processing_time,
                "endpoint_used": endpoint_url
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Internal gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time
        }

def call_tts_endpoint(endpoint_url: str, payload: Dict[str, Any], job_id: str, user_id: str) -> Dict[str, Any]:
    """
    Call the TTS endpoint with retry logic
    """
    if not RUNPOD_API_KEY:
        logger.warning(f"⚠️ Job {job_id}: RUNPOD_API_KEY not set, using dummy response")
        return {
            "success": True,
            "data": {
                "message": f"TTS Gateway is working for user {user_id}! (API key not configured for actual TTS)",
                "payload_sent": payload,
                "endpoint": endpoint_url,
                "user_id": user_id
            }
        }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {RUNPOD_API_KEY}'
    }
    
    request_payload = {"input": payload}
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 Job {job_id}: Calling {endpoint_url} for user {user_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.post(
                endpoint_url,
                json=request_payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Job {job_id}: TTS endpoint responded successfully for user {user_id}")
                return {
                    "success": True,
                    "data": result
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.error(f"❌ Job {job_id}: {error_msg}")
                
                if attempt == MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Job {job_id}: Timeout on attempt {attempt + 1}")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": f"Request timeout after {REQUEST_TIMEOUT}s"
                }
                
        except Exception as e:
            logger.error(f"💥 Job {job_id}: Error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Wait before retry
        if attempt < MAX_RETRIES - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.info(f"⏳ Job {job_id}: Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return {
        "success": False,
        "error": "Max retries exceeded"
    }

def test_handler():
    """Test function for local development with JWT authentication"""
    print("🧪 Testing TTS Gateway Handler with JWT Authentication...")
    
    # Test health check (no auth required)
    health_job = {
        "id": "test_health",
        "input": {"action": "health"}
    }
    
    print("\n=== Testing Health Check (No Auth Required) ===")
    result = handler(health_job)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test token generation
    token_job = {
        "id": "test_token",
        "input": {
            "action": "generate_token",
            "user_id": "test_user_123",
            "user_data": {"role": "admin", "plan": "premium"}
        }
    }
    
    print("\n=== Testing Token Generation ===")
    token_result = handler(token_job)
    print(f"Result: {json.dumps(token_result, indent=2)}")
    
    # Extract token for next test
    jwt_token = token_result.get('token', '')
    
    # Test TTS request without token
    tts_job_no_auth = {
        "id": "test_tts_no_auth",
        "input": {
            "text": "Hello, this is a test without authentication.",
            "engine": "kokkoro"
        }
    }
    
    print("\n=== Testing TTS Request (No Token) ===")
    result = handler(tts_job_no_auth)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test TTS request with valid token
    if jwt_token:
        tts_job_with_auth = {
            "id": "test_tts_with_auth",
            "input": {
                "text": "Hello, this is a test with valid JWT authentication.",
                "engine": "kokkoro",
                "jwt_token": jwt_token
            }
        }
        
        print("\n=== Testing TTS Request (With Valid Token) ===")
        result = handler(tts_job_with_auth)
        print(f"Result: {json.dumps(result, indent=2)}")

# This is the CRITICAL section that starts the RunPod serverless worker
if __name__ == "__main__":
    import sys
    
    # Check if running in test mode
    if "--test" in sys.argv:
        test_handler()
    else:
        # Start the RunPod serverless worker
        logger.info("🚀 Starting TTS Gateway RunPod Serverless Worker with JWT Authentication")
        logger.info(f"🔧 Configuration:")
        logger.info(f"   - Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"   - Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        logger.info(f"   - API key configured: {'Yes' if RUNPOD_API_KEY else 'No'}")
        logger.info(f"   - JWT secret configured: {'Yes' if JWT_SECRET_KEY != 'your-super-secret-jwt-key-change-this-in-production' else 'No (using default)'}")
        logger.info(f"   - JWT expiration: {JWT_EXPIRATION_HOURS} hours")
        logger.info(f"   - Request timeout: {REQUEST_TIMEOUT}s")
        logger.info(f"   - Max retries: {MAX_RETRIES}")
        
        # This line starts the RunPod serverless worker - CRITICAL!
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
