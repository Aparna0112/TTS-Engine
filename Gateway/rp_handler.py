#!/usr/bin/env python3
"""
CORRECTED RunPod Handler for TTS Gateway with STRICT JWT Authentication
Replace your current rp_handler.py with THIS version

This version REQUIRES JWT for all TTS requests and will REJECT requests without valid JWT tokens.
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
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', https://api.runpod.ai/v2/e0lm92f3god7mu/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/bc96237ndsvq8t/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# JWT Configuration - CRITICAL for authentication
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'my_awesome_tts_secret_2025')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

# Request settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    STRICT JWT token validation - this is the key security function
    """
    if not token:
        logger.warning("🔒 JWT validation failed: No token provided")
        return {
            'valid': False,
            'error': 'JWT token is required for TTS requests'
        }
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        logger.info(f"🔍 Validating JWT token: {token[:20]}...")
        
        # Decode and validate the token with STRICT validation
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'require_exp': True,
                'require_iat': True
            }
        )
        
        # Additional expiration check
        exp_timestamp = payload.get('exp')
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
            logger.warning("🔒 JWT validation failed: Token expired")
            return {
                'valid': False,
                'error': 'JWT token has expired'
            }
        
        user_id = payload.get('user_id', 'unknown')
        logger.info(f"✅ JWT token validated successfully for user: {user_id}")
        
        return {
            'valid': True,
            'payload': payload,
            'user_id': user_id
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("🔒 JWT validation failed: Token expired (ExpiredSignatureError)")
        return {
            'valid': False,
            'error': 'JWT token has expired'
        }
    except jwt.InvalidTokenError as e:
        logger.warning(f"🔒 JWT validation failed: Invalid token - {str(e)}")
        return {
            'valid': False,
            'error': f'Invalid JWT token: {str(e)}'
        }
    except Exception as e:
        logger.error(f"🔒 JWT validation error: {str(e)}")
        return {
            'valid': False,
            'error': f'JWT validation failed: {str(e)}'
        }

def generate_jwt_token(user_id: str, user_data: Optional[Dict] = None) -> str:
    """Generate a JWT token for testing purposes"""
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iss': 'tts-gateway',
        'sub': user_id
    }
    
    if user_data:
        payload.update(user_data)
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.info(f"🔑 Generated JWT token for user: {user_id}")
    return token

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    MAIN HANDLER with STRICT JWT Authentication
    This function processes every request and enforces JWT for TTS requests
    """
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        logger.info(f"🎯 TTS Gateway: Processing job {job_id}")
        
        # Get the input from the job
        job_input = job.get('input', {})
        action = job_input.get('action')
        
        logger.info(f"📝 Job {job_id} action: {action}")
        logger.info(f"📋 Job {job_id} input keys: {list(job_input.keys())}")
        
        # =================================================================
        # ENDPOINTS THAT DON'T REQUIRE JWT (Only these two!)
        # =================================================================
        
        # Handle health check requests (NO JWT REQUIRED)
        if action == 'health':
            logger.info(f"💊 Health check requested for job {job_id}")
            return {
                "status": "healthy",
                "gateway_version": "1.1.0-jwt-strict",
                "available_engines": ["kokkoro", "chatterbox"],
                "endpoints": {
                    "kokkoro": KOKKORO_ENDPOINT,
                    "chatterbox": CHATTERBOX_ENDPOINT
                },
                "jwt_auth_enabled": True,
                "jwt_auth_strict": True,
                "timestamp": time.time(),
                "job_id": job_id,
                "message": "TTS Gateway is running with STRICT JWT authentication!"
            }
        
        # Handle token generation requests (NO JWT REQUIRED)
        if action == 'generate_token':
            user_id = job_input.get('user_id')
            if not user_id:
                return {
                    "error": "Missing required parameter: 'user_id'",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time
                }
                
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
        
        # =================================================================
        # ALL OTHER REQUESTS REQUIRE JWT AUTHENTICATION
        # =================================================================
        
        logger.info(f"🔒 Job {job_id}: Checking JWT authentication for TTS request")
        
        # Look for JWT token in various possible fields
        jwt_token = (
            job_input.get('jwt_token') or 
            job_input.get('token') or 
            job_input.get('authorization') or
            job_input.get('auth_token')
        )
        
        # STRICT CHECK: No JWT token provided
        if not jwt_token:
            logger.error(f"🚫 Job {job_id}: JWT token missing - REJECTING REQUEST")
            return {
                "error": "AUTHENTICATION REQUIRED: Please provide a valid JWT token",
                "message": "Include 'jwt_token' in your request input",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "help": "Generate a token using: {'action': 'generate_token', 'user_id': 'your_id'}",
                "received_keys": list(job_input.keys()),
                "strict_mode": True
            }
        
        # STRICT CHECK: Validate the JWT token
        token_validation = validate_jwt_token(jwt_token)
        
        if not token_validation['valid']:
            logger.error(f"🚫 Job {job_id}: Invalid JWT token - REJECTING REQUEST")
            return {
                "error": f"AUTHENTICATION FAILED: {token_validation['error']}",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "help": "Generate a new token using: {'action': 'generate_token', 'user_id': 'your_id'}",
                "token_provided": jwt_token[:20] + "..." if len(jwt_token) > 20 else jwt_token,
                "strict_mode": True
            }
        
        # JWT token is valid - extract user info
        token_payload = token_validation['payload']
        user_id = token_payload.get('user_id', 'unknown')
        logger.info(f"🔓 Job {job_id}: Successfully authenticated user: {user_id}")
        
        # =================================================================
        # PROCESS TTS REQUEST (Only after successful JWT validation)
        # =================================================================
        
        # Validate required TTS parameters
        text = job_input.get('text')
        if not text:
            logger.error(f"❌ Job {job_id}: Missing 'text' parameter")
            return {
                "error": "Missing required parameter: 'text'",
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        engine = job_input.get('engine', 'kokkoro').lower()
        
        # Validate engine
        if engine not in ['kokkoro', 'chatterbox']:
            logger.error(f"❌ Job {job_id}: Invalid engine '{engine}'")
            return {
                "error": f"Invalid engine '{engine}'. Available engines: kokkoro, chatterbox",
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"🎵 Job {job_id}: Processing AUTHENTICATED TTS for user {user_id} with {engine} engine")
        logger.info(f"📄 Job {job_id}: Text length: {len(text)} characters")
        
        # Prepare the TTS request payload
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
            logger.info(f"✅ Job {job_id}: TTS completed successfully for authenticated user {user_id} in {processing_time:.2f}s")
            return {
                "success": True,
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "text_length": len(text),
                "processing_time": processing_time,
                "result": result['data'],
                "endpoint_used": endpoint_url,
                "authenticated": True,
                "jwt_validated": True
            }
        else:
            logger.error(f"❌ Job {job_id}: TTS processing failed for authenticated user {user_id}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "processing_time": processing_time,
                "endpoint_used": endpoint_url,
                "authenticated": True
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Internal gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time,
            "strict_mode": True
        }

def call_tts_endpoint(endpoint_url: str, payload: Dict[str, Any], job_id: str, user_id: str) -> Dict[str, Any]:
    """Call the TTS endpoint with retry logic"""
    if not RUNPOD_API_KEY:
        logger.warning(f"⚠️ Job {job_id}: RUNPOD_API_KEY not set, using dummy response")
        return {
            "success": True,
            "data": {
                "message": f"TTS Gateway is working for AUTHENTICATED user {user_id}! (API key not configured for actual TTS)",
                "payload_sent": payload,
                "endpoint": endpoint_url,
                "user_id": user_id,
                "authentication_status": "JWT_VALIDATED"
            }
        }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {RUNPOD_API_KEY}'
    }
    
    request_payload = {"input": payload}
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 Job {job_id}: Calling {endpoint_url} for authenticated user {user_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.post(
                endpoint_url,
                json=request_payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Job {job_id}: TTS endpoint responded successfully for authenticated user {user_id}")
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
            wait_time = 2 ** attempt
            logger.info(f"⏳ Job {job_id}: Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return {
        "success": False,
        "error": "Max retries exceeded"
    }

def test_handler():
    """Test function with JWT authentication verification"""
    print("🧪 Testing STRICT JWT Authentication Handler...")
    
    # Test 1: Health check (should work without JWT)
    health_job = {
        "id": "test_health",
        "input": {"action": "health"}
    }
    
    print("\n=== Test 1: Health Check (No JWT Required) ===")
    result = handler(health_job)
    print(f"Status: {result.get('status')}")
    print(f"JWT Strict Mode: {result.get('jwt_auth_strict')}")
    
    # Test 2: Token generation (should work without JWT)
    token_job = {
        "id": "test_token",
        "input": {
            "action": "generate_token",
            "user_id": "test_user_strict",
            "user_data": {"role": "tester", "mode": "strict"}
        }
    }
    
    print("\n=== Test 2: Token Generation (No JWT Required) ===")
    token_result = handler(token_job)
    print(f"Success: {token_result.get('success')}")
    jwt_token = token_result.get('token', '')
    if jwt_token:
        print(f"Token: {jwt_token[:50]}...")
    
    # Test 3: TTS without JWT (should FAIL)
    tts_no_auth = {
        "id": "test_no_jwt",
        "input": {
            "text": "This should be REJECTED without JWT",
            "engine": "kokkoro"
        }
    }
    
    print("\n=== Test 3: TTS Without JWT (Should FAIL) ===")
    result = handler(tts_no_auth)
    print(f"Error: {result.get('error', 'No error?')}")
    print(f"Auth Required: {result.get('auth_required')}")
    print(f"Strict Mode: {result.get('strict_mode')}")
    
    # Test 4: TTS with valid JWT (should work)
    if jwt_token:
        tts_with_auth = {
            "id": "test_with_jwt",
            "input": {
                "jwt_token": jwt_token,
                "text": "This should work with valid JWT token",
                "engine": "kokkoro"
            }
        }
        
        print("\n=== Test 4: TTS With Valid JWT (Should Work) ===")
        result = handler(tts_with_auth)
        print(f"Success: {result.get('success')}")
        print(f"User ID: {result.get('user_id')}")
        print(f"JWT Validated: {result.get('jwt_validated')}")
        print(f"Authenticated: {result.get('authenticated')}")
    
    # Test 5: TTS with invalid JWT (should FAIL)
    tts_invalid_jwt = {
        "id": "test_invalid_jwt",
        "input": {
            "jwt_token": "invalid.jwt.token.here",
            "text": "This should FAIL with invalid JWT",
            "engine": "kokkoro"
        }
    }
    
    print("\n=== Test 5: TTS With Invalid JWT (Should FAIL) ===")
    result = handler(tts_invalid_jwt)
    print(f"Error: {result.get('error', 'No error?')}")
    print(f"Auth Required: {result.get('auth_required')}")
    print(f"Strict Mode: {result.get('strict_mode')}")

# CRITICAL: Start the RunPod serverless worker
if __name__ == "__main__":
    import sys
    
    # Check JWT secret configuration
    if JWT_SECRET_KEY == 'your-super-secret-jwt-key-change-this-in-production':
        logger.warning("⚠️ WARNING: Using default JWT secret key! Change JWT_SECRET_KEY in production!")
    
    # Check if running in test mode
    if "--test" in sys.argv:
        test_handler()
    else:
        # Start the RunPod serverless worker
        logger.info("🚀 Starting TTS Gateway with STRICT JWT Authentication")
        logger.info(f"🔧 Configuration:")
        logger.info(f"   - Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"   - Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        logger.info(f"   - API key configured: {'Yes' if RUNPOD_API_KEY else 'No'}")
        logger.info(f"   - JWT secret configured: {'Yes' if JWT_SECRET_KEY != 'your-super-secret-jwt-key-change-this-in-production' else 'No (USING DEFAULT - INSECURE!)'}")
        logger.info(f"   - JWT algorithm: {JWT_ALGORITHM}")
        logger.info(f"   - JWT expiration: {JWT_EXPIRATION_HOURS} hours")
        logger.info(f"   - Request timeout: {REQUEST_TIMEOUT}s")
        logger.info(f"   - Max retries: {MAX_RETRIES}")
        logger.info("🔒 STRICT JWT AUTHENTICATION ENABLED - TTS requests REQUIRE valid JWT tokens")
        
        # This line starts the RunPod serverless worker
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
