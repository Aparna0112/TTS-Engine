#!/usr/bin/env python3
"""
Gateway/rp_handler.py
TTS Gateway V3 - Serverless Handler for Kokkoro + Chatterbox
Enhanced version with complete voice management and MP3 support
"""

import runpod
import requests
import os
import time
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jwt_utils import jwt_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# V3 Serverless Configuration
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/kokkoro-v3-serverless/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/chatterbox-v3-serverless/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# Request settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Model configurations for serverless endpoints
MODEL_CONFIGS = {
    'kokkoro': {
        'endpoint': KOKKORO_ENDPOINT,
        'timeout': 180,
        'builtin_voices': [
            'kokkoro_default',
            'kokkoro_sweet', 
            'kokkoro_energetic',
            'kokkoro_calm',
            'kokkoro_english'
        ],
        'supports_japanese': True,
        'supports_custom_voices': True,
        'supports_mp3': True,
        'model_type': 'kokkoro_serverless',
        'languages': ['ja-JP', 'en-US']
    },
    'chatterbox': {
        'endpoint': CHATTERBOX_ENDPOINT,
        'timeout': 200,
        'builtin_voices': [
            'female_default',
            'male_default',
            'narrator'
        ],
        'supports_voice_cloning': True,
        'supports_emotion_control': True,
        'supports_custom_voices': True,
        'supports_mp3': True,
        'model_type': 'chatterbox_serverless',
        'languages': ['en-US']
    }
}

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced Gateway handler for serverless TTS models"""
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        logger.info(f"TTS Gateway V3 Serverless: Processing job {job_id}")
        
        job_input = job.get('input', {})
        action = job_input.get('action')
        
        logger.info(f"Job {job_id} action: {action}")
        logger.info(f"Job {job_id} input keys: {list(job_input.keys())}")
        
        # =================================================================
        # PUBLIC ENDPOINTS (No JWT required)
        # =================================================================
        
        if action == 'health':
            return {
                "status": "healthy",
                "gateway_version": "3.0.0-serverless",
                "available_engines": list(MODEL_CONFIGS.keys()),
                "model_configs": {
                    engine: {
                        "builtin_voices": config["builtin_voices"],
                        "model_type": config["model_type"],
                        "supports_mp3": config["supports_mp3"],
                        "languages": config.get("languages", ["en-US"]),
                        "features": [key for key in config.keys() if key.startswith('supports_') and config[key]]
                    }
                    for engine, config in MODEL_CONFIGS.items()
                },
                "endpoints": {
                    "kokkoro": KOKKORO_ENDPOINT,
                    "chatterbox": CHATTERBOX_ENDPOINT
                },
                "jwt_auth_enabled": True,
                "features": [
                    "serverless_architecture",
                    "real_model_voices", 
                    "mp3_output",
                    "voice_cloning",
                    "custom_voices",
                    "japanese_support",
                    "emotion_control"
                ],
                "timestamp": time.time(),
                "job_id": job_id
            }
        
        if action == 'generate_token':
            user_id = job_input.get('user_id')
            if not user_id:
                return {
                    "error": "Missing required parameter: 'user_id'",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time
                }
            
            user_data = job_input.get('user_data', {})
            token = jwt_manager.generate_token(user_id, user_data)
            
            return {
                "success": True,
                "token": token,
                "user_id": user_id,
                "expires_in_hours": jwt_manager.expiration_hours,
                "message": "JWT token generated for serverless TTS access",
                "gateway_version": "3.0.0-serverless",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        if action == 'list_models' or action == 'models':
            return {
                "available_models": MODEL_CONFIGS,
                "total_engines": len(MODEL_CONFIGS),
                "total_builtin_voices": sum(len(config["builtin_voices"]) for config in MODEL_CONFIGS.values()),
                "gateway_version": "3.0.0-serverless",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # =================================================================
        # PROTECTED ENDPOINTS (JWT required)
        # =================================================================
        
        logger.info(f"Job {job_id}: Checking JWT authentication")
        
        jwt_token = (
            job_input.get('jwt_token') or 
            job_input.get('token') or 
            job_input.get('authorization') or
            job_input.get('auth_token')
        )
        
        if not jwt_token:
            logger.error(f"Job {job_id}: JWT token missing")
            return {
                "error": "AUTHENTICATION REQUIRED: Please provide a valid JWT token",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "help": "Generate token: {'action': 'generate_token', 'user_id': 'your_id'}",
                "gateway_version": "3.0.0-serverless"
            }
        
        token_validation = jwt_manager.validate_token(jwt_token)
        
        if not token_validation['valid']:
            logger.error(f"Job {job_id}: Invalid JWT token")
            return {
                "error": f"AUTHENTICATION FAILED: {token_validation['error']}",
                "auth_required": True,
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "gateway_version": "3.0.0-serverless"
            }
        
        user_id = token_validation['user_id']
        logger.info(f"Job {job_id}: Authenticated user: {user_id}")
        
        # =================================================================
        # TTS MODEL OPERATIONS
        # =================================================================
        
        engine = job_input.get('engine', 'chatterbox').lower()
        
        if engine not in MODEL_CONFIGS:
            return {
                "error": f"Invalid engine '{engine}'. Available: {list(MODEL_CONFIGS.keys())}",
                "available_engines": list(MODEL_CONFIGS.keys()),
                "job_id": job_id,
                "user_id": user_id,
                "processing_time": time.time() - start_time
            }
        
        model_config = MODEL_CONFIGS[engine]
        
        # Handle different TTS operations
        if action == 'list_voices' or (not action and job_input.get('list_voices')):
            # List voices for specific engine
            result = call_serverless_endpoint(
                model_config['endpoint'],
                {"action": "voices", "jwt_token": jwt_token},
                job_id, user_id, engine, "list_voices"
            )
        
        elif action == 'create_voice':
            # Create custom voice
            required_fields = ['voice_name', 'audio_base64']
            missing_fields = [field for field in required_fields if not job_input.get(field)]
            
            if missing_fields:
                return {
                    "error": f"Missing required fields: {missing_fields}",
                    "job_id": job_id,
                    "user_id": user_id,
                    "processing_time": time.time() - start_time
                }
            
            payload = {
                "action": "create_voice",
                "voice_name": job_input.get("voice_name"),
                "voice_description": job_input.get("voice_description", ""),
                "audio_base64": job_input.get("audio_base64"),
                "language": job_input.get("language"),
                "jwt_token": jwt_token
            }
            
            result = call_serverless_endpoint(
                model_config['endpoint'], payload, job_id, user_id, engine, "create_voice"
            )
        
        else:
            # Default: Speech synthesis
            text = job_input.get("text")
            if not text:
                return {
                    "error": "Missing required parameter: 'text'",
                    "job_id": job_id,
                    "user_id": user_id,
                    "processing_time": time.time() - start_time
                }
            
            # Build synthesis payload
            payload = {
                "text": text,
                "jwt_token": jwt_token,
                "format": job_input.get("format", "mp3")
            }
            
            # Engine-specific parameters
            if engine == 'kokkoro':
                payload.update({
                    "voice_id": job_input.get("voice", "kokkoro_default"),
                    "speed": job_input.get("speed", 1.0),
                    "language": job_input.get("language")
                })
            elif engine == 'chatterbox':
                payload.update({
                    "voice_id": job_input.get("voice", "female_default"),
                    "exaggeration": job_input.get("exaggeration", 0.5),
                    "temperature": job_input.get("temperature", 0.8),
                    "audio_prompt_path": job_input.get("audio_prompt_path")
                })
            
            result = call_serverless_endpoint(
                model_config['endpoint'], payload, job_id, user_id, engine, "synthesize"
            )
        
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info(f"Job {job_id}: Serverless TTS completed for user {user_id} in {processing_time:.2f}s")
            
            response = {
                "success": True,
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "model_type": model_config['model_type'],
                "processing_time": processing_time,
                "gateway_version": "3.0.0-serverless",
                "authenticated": True,
                "jwt_validated": True
            }
            
            # Merge TTS result
            if 'data' in result:
                response.update(result['data'])
            
            return response
        else:
            logger.error(f"Job {job_id}: Serverless TTS failed for user {user_id}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "user_id": user_id,
                "engine": engine,
                "processing_time": processing_time,
                "gateway_version": "3.0.0-serverless"
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time,
            "gateway_version": "3.0.0-serverless"
        }

def call_serverless_endpoint(endpoint_url: str, payload: Dict[str, Any], job_id: str, user_id: str, engine: str, operation: str) -> Dict[str, Any]:
    """Call serverless TTS endpoint"""
    if not RUNPOD_API_KEY:
        logger.warning(f"Job {job_id}: RUNPOD_API_KEY not set, using mock response")
        return {
            "success": True,
            "data": {
                "message": f"Serverless {engine} {operation} working for user {user_id}",
                "mock_response": True,
                "endpoint": endpoint_url
            }
        }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {RUNPOD_API_KEY}'
    }
    
    request_payload = {"input": payload}
    timeout = MODEL_CONFIGS[engine]['timeout']
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Job {job_id}: Calling serverless {engine} for {operation} (attempt {attempt + 1})")
            
            response = requests.post(
                endpoint_url,
                json=request_payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Job {job_id}: Serverless {engine} responded successfully")
                
                if result.get('success'):
                    return {"success": True, "data": result}
                else:
                    return {"success": False, "error": result.get('error', f'{engine} {operation} failed')}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.error(f"Job {job_id}: {error_msg}")
                
                if attempt == MAX_RETRIES - 1:
                    return {"success": False, "error": error_msg}
                    
        except requests.exceptions.Timeout:
            logger.error(f"Job {job_id}: Timeout on attempt {attempt + 1} (waited {timeout}s)")
            if attempt == MAX_RETRIES - 1:
                return {"success": False, "error": f"Request timeout after {timeout}s"}
                
        except Exception as e:
            logger.error(f"Job {job_id}: Error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return {"success": False, "error": str(e)}
        
        if attempt < MAX_RETRIES - 1:
            wait_time = 2 ** attempt
            logger.info(f"Job {job_id}: Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return {"success": False, "error": "Max retries exceeded"}

# Start the RunPod serverless worker
if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        print("Testing Gateway V3 Serverless Handler...")
        
        # Test health
        result = handler({"id": "test", "input": {"action": "health"}})
        print(f"Health: {result.get('status')}")
        print(f"Engines: {list(result.get('model_configs', {}).keys())}")
        
    else:
        logger.info("Starting TTS Gateway V3 - Serverless Architecture")
        logger.info(f"Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        logger.info(f"JWT Manager initialized")
        
        runpod.serverless.start({"handler": handler})
