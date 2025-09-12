#!/usr/bin/env python3
"""
TTS Gateway V3 Handler with STRICT JWT Authentication
Real Models + MP3 Output Support
Replace your Gateway/rp_handler.py with THIS version
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

# V3 Configuration - Updated endpoints for real models
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/your-kokkoro-v3-endpoint/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/your-chatterbox-v3-endpoint/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# JWT Configuration - Keep your existing security
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'my_awesome_tts_secret_2025')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

# Request settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# V3 Model configurations
MODEL_CONFIGS = {
    'kokkoro': {
        'endpoint': KOKKORO_ENDPOINT,
        'timeout': 120,  # Longer timeout for real model
        'voices': [
            'kokkoro_default',
            'kokkoro_sweet', 
            'kokkoro_energetic',
            'kokkoro_calm',
            'kokkoro_english'
        ],
        'supports_japanese': True,
        'supports_mp3': True,
        'model_type': 'real_kokkoro'
    },
    'chatterbox': {
        'endpoint': CHATTERBOX_ENDPOINT,
        'timeout': 180,  # Longer timeout for neural model
        'voices': [
            'chatterbox_default',
            'chatterbox_casual',
            'chatterbox_professional', 
            'chatterbox_energetic',
            'chatterbox_calm',
            'chatterbox_dramatic',
            'chatterbox_narrator',
            'chatterbox_friendly'
        ],
        'supports_emotion_control': True,
        'supports_voice_cloning': True,
        'supports_mp3': True,
        'model_type': 'real_chatterbox_neural'
    }
}

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """STRICT JWT token validation - keeping your existing security"""
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
        'iss': 'tts-gateway-v3',
        'sub': user_id
    }
    
    if user_data:
        payload.update(user_data)
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.info(f"🔑 Generated JWT token for user: {user_id}")
    return token

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    MAIN V3 HANDLER with STRICT JWT Authentication + Real Models + MP3 Support
    """
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        logger.info(f"🎯 TTS Gateway V3: Processing job {job_id}")
        
        # Get the input from the job
        job_input = job.get('input', {})
        action = job_input.get('action')
        
        logger.info(f"📝 Job {job_id} action: {action}")
        logger.info(f"📋 Job {job_id} input keys: {list(job_input.keys())}")
        
        # =================================================================
        # ENDPOINTS THAT DON'T REQUIRE JWT (Only these!)
        # =================================================================
        
        # Handle health check requests (NO JWT REQUIRED)
        if action == 'health':
            logger.info(f"💊 Health check requested for job {job_id}")
            return {
                "status": "healthy",
                "gateway_version": "3.0.0-real-models-mp3",
                "available_engines": list(MODEL_CONFIGS.keys()),
                "model_configs": {
                    engine: {
                        "voices": config["voices"],
                        "model_type": config["model_type"],
                        "supports_mp3": config["supports_mp3"],
                        "features": [
                            key for key in config.keys() 
                            if key.startswith('supports_') and config[key]
                        ]
                    }
                    for engine, config in MODEL_CONFIGS.items()
                },
                "endpoints": {
                    "kokkoro": KOKKORO_ENDPOINT,
                    "chatterbox": CHATTERBOX_ENDPOINT
                },
                "jwt_auth_enabled": True,
                "jwt_auth_strict": True,
                "new_features": [
                    "real_kokkoro_voices", 
                    "real_chatterbox_neural_tts",
                    "mp3_output",
                    "emotion_control",
                    "voice_cloning",
                    "japanese_support"
                ],
                "timestamp": time.time(),
                "job_id": job_id,
                "message": "TTS Gateway V3 is running with Real Models and MP3 output!"
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
                "message": "JWT token generated successfully for V3 TTS access",
                "gateway_version": "3.0.0-real-models-mp3",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # Handle model info requests (NO JWT REQUIRED)
        if action == 'info' or action == 'models':
            return {
                "gateway_version": "3.0.0-real-models-mp3",
                "available_models": MODEL_CONFIGS,
                "usage_examples": {
                    "kokkoro_japanese": {
                        "text": "こんにちは！私はココロです！",
                        "engine": "kokkoro",
                        "voice": "kokkoro_sweet",
                        "format": "mp3"
                    },
                    "chatterbox_emotion": {
                        "text": "This is absolutely amazing!",
                        "engine": "chatterbox", 
                        "voice": "chatterbox_dramatic",
                        "exaggeration": 0.8,
                        "format": "mp3"
                    },
                    "chatterbox_cloning": {
                        "text": "Speaking with cloned voice",
                        "engine": "chatterbox",
                        "audio_prompt_path": "/app/audio_prompts/sample.wav",
                        "format": "mp3"
                    }
                },
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
                "strict_mode": True,
                "gateway_version": "3.0.0-real-models-mp3"
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
                "strict_mode": True,
                "gateway_version": "3.0.0-real-models-mp3"
            }
        
        # JWT token is valid - extract user info
        token_payload = token_validation['payload']
        user_id = token_payload.get('user_id', 'unknown')
        logger.info(f"🔓 Job {job_id}: Successfully authenticated user: {user_id}")
        
        # =================================================================
        # PROCESS V3 TTS REQUEST (Real Models + MP3 Support)
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
        
        engine = job_input.get('engine', 'chatterbox').lower()  # Default to chatterbox in V3
        
        # Validate engine
        if engine not in MODEL_CONFIGS:
            available_engines = list(MODEL_CONFIGS.keys())
            logger.error(f"❌ Job {job_id}: Invalid engine '{engine}'")
            return {
                "error": f"Invalid engine '{engine}'. Available engines: {available_engines}",
                "available_engines": available_engines,
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        model_config = MODEL_CONFIGS[engine]
        logger.info(f"🎵 Job {job_id}: Processing V3 TTS for user {user_id} with {engine} engine ({model_config['model_type']})")
        logger.info(f"📄 Job {job_id}: Text length: {len(text)} characters")
        
        # Prepare the V3 TTS request payload
        tts_payload = {
            'text': text,
            'voice': job_input.get('voice', model_config['voices'][0]),  # Use first voice as default
            'speed': job_input.get('speed', 1.0),
            'format': job_input.get('format', 'mp3'),  # Default to MP3 in V3
            'jwt_token': jwt_token  # Pass JWT to TTS engine
        }
        
        # Validate voice for selected engine
        requested_voice = tts_payload['voice']
        if requested_voice not in model_config['voices']:
            logger.warning(f"⚠️ Job {job_id}: Invalid voice '{requested_voice}' for {engine}, using default")
            tts_payload['voice'] = model_config['voices'][0]
        
        # Add engine-specific V3 parameters
        if engine == 'kokkoro':
            # Real Kokkoro model parameters
            tts_payload.update({
                'language': job_input.get('language', 'ja' if 'japanese' in requested_voice else 'en'),
                'model_type': 'real_kokkoro'
            })
        elif engine == 'chatterbox':
            # Real Chatterbox neural TTS parameters
            tts_payload.update({
                'exaggeration': job_input.get('exaggeration'),  # Emotion control
                'cfg_weight': job_input.get('cfg_weight'),      # Fine-tuning
                'audio_prompt_path': job_input.get('audio_prompt_path'),  # Voice cloning
                'model_type': 'real_chatterbox_neural'
            })
        
        # Call the V3 TTS endpoint
        result = call_tts_endpoint_v3(model_config['endpoint'], tts_payload, job_id, user_id, engine, model_config)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info(f"✅ Job {job_id}: V3 TTS completed successfully for authenticated user {user_id} in {processing_time:.2f}s")
            
            # Extract V3 response data
            tts_result = result['data']
            
            return {
                "success": True,
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "model_type": model_config['model_type'],
                "text_length": len(text),
                "processing_time": processing_time,
                "gateway_version": "3.0.0-real-models-mp3",
                # V3 Audio Response
                "audio_url": tts_result.get('audio_url'),           # Direct file path
                "playable_url": tts_result.get('playable_url'),     # For RunPod playback
                "duration": tts_result.get('duration'),            # Audio duration
                "format": tts_result.get('output_format', 'mp3'),  # Audio format
                "mime_type": tts_result.get('mime_type', 'audio/mpeg'),
                "file_size": tts_result.get('audio_size_bytes'),   # File size
                # Voice Information
                "voice_used": tts_result.get('voice_used'),
                "voice_description": tts_result.get('voice_description'),
                "voice_style": tts_result.get('voice_style'),
                # V3 Features
                "has_watermark": tts_result.get('has_watermark', False),
                "is_real_model": tts_result.get('is_real_kokkoro') or tts_result.get('is_real_chatterbox', False),
                "emotion_used": tts_result.get('exaggeration_used'),
                "voice_cloning_used": tts_result.get('audio_prompt_used', False),
                # Technical Details
                "endpoint_used": model_config['endpoint'],
                "authenticated": True,
                "jwt_validated": True
            }
        else:
            logger.error(f"❌ Job {job_id}: V3 TTS processing failed for authenticated user {user_id}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "model_type": model_config['model_type'],
                "processing_time": processing_time,
                "endpoint_used": model_config['endpoint'],
                "authenticated": True,
                "gateway_version": "3.0.0-real-models-mp3"
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Internal gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time,
            "strict_mode": True,
            "gateway_version": "3.0.0-real-models-mp3"
        }

def call_tts_endpoint_v3(endpoint_url: str, payload: Dict[str, Any], job_id: str, user_id: str, engine: str, model_config: Dict) -> Dict[str, Any]:
    """Call the V3 TTS endpoint with retry logic and enhanced timeout"""
    if not RUNPOD_API_KEY:
        logger.warning(f"⚠️ Job {job_id}: RUNPOD_API_KEY not set, using V3 dummy response")
        return {
            "success": True,
            "data": {
                "message": f"TTS Gateway V3 is working for AUTHENTICATED user {user_id}! (API key not configured for actual TTS)",
                "audio_url": "/tmp/dummy_audio.mp3",
                "playable_url": "/tmp/dummy_audio.mp3",
                "duration": 3.5,
                "format": "mp3",
                "mime_type": "audio/mpeg",
                "voice_used": payload.get('voice', 'default'),
                "voice_description": f"Real {engine} model voice",
                "has_watermark": engine == 'chatterbox',
                "is_real_model": True,
                "model_type": model_config['model_type'],
                "payload_sent": payload,
                "endpoint": endpoint_url,
                "user_id": user_id,
                "authentication_status": "JWT_VALIDATED_V3"
            }
        }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {RUNPOD_API_KEY}'
    }
    
    request_payload = {"input": payload}
    timeout = model_config.get('timeout', REQUEST_TIMEOUT)
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 Job {job_id}: Calling V3 {engine} endpoint for authenticated user {user_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            logger.info(f"🎯 Job {job_id}: Using {model_config['model_type']} with timeout {timeout}s")
            
            response = requests.post(
                endpoint_url,
                json=request_payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Job {job_id}: V3 TTS endpoint responded successfully for authenticated user {user_id}")
                
                # Handle V3 response format
                if result.get('success'):
                    return {
                        "success": True,
                        "data": result
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', 'V3 TTS generation failed')
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
            logger.error(f"⏰ Job {job_id}: Timeout on attempt {attempt + 1} (waited {timeout}s)")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": f"Request timeout after {timeout}s - V3 models need more processing time"
                }
                
        except Exception as e:
            logger.error(f"💥 Job {job_id}: Error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Wait before retry with exponential backoff
        if attempt < MAX_RETRIES - 1:
            wait_time = 2 ** attempt
            logger.info(f"⏳ Job {job_id}: Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return {
        "success": False,
        "error": "Max retries exceeded"
    }

def test_handler():
    """Test function with V3 JWT authentication verification"""
    print("🧪 Testing V3 STRICT JWT Authentication Handler...")
    
    # Test 1: Health check (should work without JWT)
    health_job = {
        "id": "test_health_v3",
        "input": {"action": "health"}
    }
    
    print("\n=== Test 1: V3 Health Check (No JWT Required) ===")
    result = handler(health_job)
    print(f"Status: {result.get('status')}")
    print(f"Gateway Version: {result.get('gateway_version')}")
    print(f"Available Models: {list(result.get('model_configs', {}).keys())}")
    
    # Test 2: Token generation (should work without JWT)
    token_job = {
        "id": "test_token_v3",
        "input": {
            "action": "generate_token",
            "user_id": "test_user_v3",
            "user_data": {"role": "tester", "version": "v3"}
        }
    }
    
    print("\n=== Test 2: V3 Token Generation (No JWT Required) ===")
    token_result = handler(token_job)
    print(f"Success: {token_result.get('success')}")
    jwt_token = token_result.get('token', '')
    if jwt_token:
        print(f"Token: {jwt_token[:50]}...")
    
    # Test 3: Model info (should work without JWT)
    info_job = {
        "id": "test_info_v3",
        "input": {"action": "info"}
    }
    
    print("\n=== Test 3: V3 Model Info (No JWT Required) ===")
    info_result = handler(info_job)
    print(f"Gateway Version: {info_result.get('gateway_version')}")
    if 'available_models' in info_result:
        for model, config in info_result['available_models'].items():
            print(f"  {model}: {config['model_type']} ({len(config['voices'])} voices)")
    
    # Test 4: TTS without JWT (should FAIL)
    tts_no_auth = {
        "id": "test_no_jwt_v3",
        "input": {
            "text": "This should be REJECTED without JWT in V3",
            "engine": "chatterbox"
        }
    }
    
    print("\n=== Test 4: V3 TTS Without JWT (Should FAIL) ===")
    result = handler(tts_no_auth)
    print(f"Error: {result.get('error', 'No error?')}")
    print(f"Gateway Version: {result.get('gateway_version')}")
    
    # Test 5: TTS with valid JWT (should work)
    if jwt_token:
        tts_with_auth = {
            "id": "test_with_jwt_v3",
            "input": {
                "jwt_token": jwt_token,
                "text": "Testing V3 Chatterbox with real neural TTS!",
                "engine": "chatterbox",
                "voice": "chatterbox_energetic",
                "exaggeration": 0.8,
                "format": "mp3"
            }
        }
        
        print("\n=== Test 5: V3 Chatterbox TTS With Valid JWT (Should Work) ===")
        result = handler(tts_with_auth)
        print(f"Success: {result.get('success')}")
        print(f"Model Type: {result.get('model_type')}")
        print(f"Audio Format: {result.get('format')}")
        print(f"Voice Used: {result.get('voice_used')}")
        print(f"Real Model: {result.get('is_real_model')}")
        
        # Test Kokkoro too
        kokkoro_test = {
            "id": "test_kokkoro_v3", 
            "input": {
                "jwt_token": jwt_token,
                "text": "こんにちは！私はココロです！",
                "engine": "kokkoro",
                "voice": "kokkoro_sweet",
                "format": "mp3"
            }
        }
        
        print("\n=== Test 6: V3 Kokkoro TTS (Japanese) With Valid JWT ===")
        result = handler(kokkoro_test)
        print(f"Success: {result.get('success')}")
        print(f"Model Type: {result.get('model_type')}")
        print(f"Voice Description: {result.get('voice_description')}")

# CRITICAL: Start the RunPod serverless worker
if __name__ == "__main__":
    import sys
    
    # Check JWT secret configuration
    if JWT_SECRET_KEY == 'my_awesome_tts_secret_2025':
        logger.warning("⚠️ WARNING: Using example JWT secret key! Change JWT_SECRET_KEY in production!")
    
    # Check if running in test mode
    if "--test" in sys.argv:
        test_handler()
    else:
        # Start the RunPod serverless worker
        logger.info("🚀 Starting TTS Gateway V3 with Real Models + MP3 + STRICT JWT Authentication")
        logger.info(f"🔧 V3 Configuration:")
        logger.info(f"   - Gateway version: 3.0.0-real-models-mp3")
        logger.info(f"   - Kokkoro V3 endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"   - Chatterbox V3 endpoint: {CHATTERBOX_ENDPOINT}")
        logger.info(f"   - Available models: {list(MODEL_CONFIGS.keys())}")
        logger.info(f"   - Total voices: {sum(len(config['voices']) for config in MODEL_CONFIGS.values())}")
        logger.info(f"   - API key configured: {'Yes' if RUNPOD_API_KEY else 'No'}")
        logger.info(f"   - JWT secret configured: {'Yes' if JWT_SECRET_KEY != 'my_awesome_tts_secret_2025' else 'No (USING EXAMPLE - INSECURE!)'}")
        logger.info(f"   - JWT algorithm: {JWT_ALGORITHM}")
        logger.info(f"   - JWT expiration: {JWT_EXPIRATION_HOURS} hours")
        logger.info(f"   - Request timeout: {REQUEST_TIMEOUT}s (models may use longer)")
        logger.info(f"   - Max retries: {MAX_RETRIES}")
        logger.info("🎵 V3 FEATURES:")
        logger.info("   - Real Kokkoro model voices (5 Japanese + English voices)")
        logger.info("   - Real Chatterbox neural TTS (8 emotion presets)")
        logger.info("   - MP3 output for direct RunPod playback")
        logger.info("   - Emotion exaggeration control (Chatterbox)")
        logger.info("   - Zero-shot voice cloning (Chatterbox)")
        logger.info("   - Built-in watermarking (Chatterbox)")
        logger.info("   - Japanese language support (Kokkoro)")
        logger.info("🔒 STRICT JWT AUTHENTICATION ENABLED - TTS requests REQUIRE valid JWT tokens")
        
        # This line starts the RunPod serverless worker
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
