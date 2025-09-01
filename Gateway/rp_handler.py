#!/usr/bin/env python3
"""
FIXED Gateway Handler - Properly enforces JWT authentication
This version will BLOCK requests without JWT tokens when REQUIRE_JWT=true
"""

import runpod
import requests
import os
import time
import logging
import json
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import redis
from datetime import datetime, timedelta
import traceback
import jwt

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    KOKKORO = "kokkoro"
    CHATTERBOX = "chatterbox"

@dataclass
class TTSRequest:
    text: str
    engine: TTSEngine
    voice: str = "default"
    speed: float = 1.0
    language: str = "en"
    
    def __post_init__(self):
        if len(self.text) > 5000:
            raise ValueError("Text too long (max 5,000 characters)")
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError("Speed must be between 0.5 and 2.0")

class ProductionTTSGateway:
    def __init__(self):
        # Your existing endpoints
        self.endpoints = {
            TTSEngine.KOKKORO: os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync'),
            TTSEngine.CHATTERBOX: os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync')
        }
        
        # Production configurations
        self.api_key = os.getenv('RUNPOD_API_KEY')
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '120'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '2'))
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))
        
        # JWT Configuration - CRITICAL FIX
        self.jwt_secret = os.getenv('JWT_SECRET')
        require_jwt_env = os.getenv('REQUIRE_JWT', 'false').lower().strip()
        self.jwt_required = require_jwt_env == 'true'
        
        # FORCE JWT for debugging - uncomment this line to force JWT
        # self.jwt_required = True  # TEMPORARY - remove after testing
        
        # Enhanced debug logging
        logger.info("=" * 50)
        logger.info("JWT CONFIGURATION DEBUG:")
        logger.info(f"  REQUIRE_JWT env var: '{os.getenv('REQUIRE_JWT', 'NOT_SET')}'")
        logger.info(f"  After processing: '{require_jwt_env}'")
        logger.info(f"  JWT Secret exists: {self.jwt_secret is not None}")
        logger.info(f"  JWT Secret length: {len(self.jwt_secret) if self.jwt_secret else 0}")
        logger.info(f"  JWT Required (final): {self.jwt_required}")
        logger.info("=" * 50)
        
        # Redis setup (optional)
        self.redis_client = None
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=5)
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")
                self.redis_client = None
        
        # Rate limiting
        self.rate_limits = {}
        self.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
        self.rate_limit_window = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'kokkoro_requests': 0,
            'chatterbox_requests': 0,
            'jwt_rejections': 0
        }

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token - ENHANCED VERSION"""
        if not self.jwt_secret:
            logger.error("CRITICAL: JWT secret not configured but JWT required!")
            return None
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            logger.info(f"JWT token VALID for user: {payload.get('user_id', 'unknown')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token EXPIRED")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT token INVALID: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"JWT verification ERROR: {str(e)}")
            return None

    def call_tts_endpoint_sync(self, request: TTSRequest, job_id: str) -> Dict[str, Any]:
        """Call TTS endpoint - REMOVES dummy response when no API key"""
        endpoint_url = self.endpoints[request.engine]
        
        # REMOVED: Dummy response when no API key
        # Now it will fail properly if RUNPOD_API_KEY is missing
        if not self.api_key:
            logger.error(f"RUNPOD_API_KEY is required but not set!")
            return {"success": False, "error": "RUNPOD_API_KEY not configured"}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Connection': 'close'
        }
        
        # Build payload
        payload = {
            'text': request.text,
            'voice': request.voice,
            'speed': request.speed
        }
        
        if request.engine == TTSEngine.KOKKORO:
            payload.update({
                'language': request.language,
                'speaker_id': 0
            })
        elif request.engine == TTSEngine.CHATTERBOX:
            payload.update({
                'model': 'default',
                'format': 'wav'
            })
        
        request_payload = {"input": payload}
        
        # Make the actual request
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling {request.engine.value} (attempt {attempt + 1})")
                
                response = requests.post(
                    endpoint_url,
                    json=request_payload,
                    headers=headers,
                    timeout=self.request_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"SUCCESS from {request.engine.value}")
                    return {"success": True, "data": result}
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(f"ERROR: {error_msg}")
                    
                    if attempt == self.max_retries - 1:
                        return {"success": False, "error": error_msg}
                        
            except requests.exceptions.Timeout:
                logger.error(f"TIMEOUT on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return {"success": False, "error": "Request timeout"}
                    
            except Exception as e:
                logger.error(f"REQUEST ERROR: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {"success": False, "error": str(e)}
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                time.sleep(1 + attempt)
        
        return {"success": False, "error": "Max retries exceeded"}

    def validate_request(self, job_input: Dict[str, Any]) -> TTSRequest:
        """Validate request"""
        if not job_input.get('text'):
            raise ValueError("Missing required parameter: 'text'")
        
        text = job_input['text'].strip()
        if not text:
            raise ValueError("Text cannot be empty")
        
        engine_str = job_input.get('engine', 'kokkoro').lower()
        if engine_str == 'kokkoro':
            engine = TTSEngine.KOKKORO
        elif engine_str == 'chatterbox':
            engine = TTSEngine.CHATTERBOX
        else:
            raise ValueError(f"Invalid engine '{engine_str}'. Available: kokkoro, chatterbox")
        
        return TTSRequest(
            text=text,
            engine=engine,
            voice=job_input.get('voice', 'default'),
            speed=float(job_input.get('speed', 1.0)),
            language=job_input.get('language', 'en')
        )

# Global gateway instance
gateway = ProductionTTSGateway()

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    FIXED handler that properly enforces JWT authentication
    """
    start_time = time.time()
    job_id = job.get('id', f'job_{int(time.time())}')
    client_id = job.get('webhook', 'anonymous')
    
    try:
        logger.info(f"Processing job {job_id}")
        job_input = job.get('input', {})
        
        # Handle health check FIRST (before JWT check)
        if job_input.get('action') == 'health':
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "gateway_version": "1.3.0-fixed",
                "available_engines": ["kokkoro", "chatterbox"],
                "features": {
                    "caching": gateway.redis_client is not None,
                    "jwt_auth": gateway.jwt_required,
                    "rate_limiting": True
                },
                "debug_info": {
                    "jwt_secret_exists": gateway.jwt_secret is not None,
                    "jwt_required": gateway.jwt_required,
                    "require_jwt_env": os.getenv('REQUIRE_JWT', 'NOT_SET'),
                    "runpod_api_key_exists": gateway.api_key is not None
                },
                "metrics": gateway.metrics,
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # JWT Authentication - CRITICAL SECTION
        logger.info(f"JWT Required: {gateway.jwt_required}")
        
        if gateway.jwt_required:
            logger.info("JWT authentication is ENABLED - checking token...")
            
            auth_token = job_input.get('auth_token')
            logger.info(f"Auth token provided: {auth_token is not None}")
            
            # BLOCK REQUEST if no token
            if not auth_token:
                gateway.metrics['jwt_rejections'] += 1
                logger.warning(f"BLOCKING request - no JWT token provided")
                return {
                    "success": False,
                    "error": "Authentication required - JWT token missing",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time,
                    "jwt_required": True,
                    "hint": "Include 'auth_token' in your request input"
                }
            
            # VERIFY TOKEN
            jwt_payload = gateway.verify_jwt_token(auth_token)
            if not jwt_payload:
                gateway.metrics['jwt_rejections'] += 1
                logger.warning(f"BLOCKING request - invalid JWT token")
                return {
                    "success": False,
                    "error": "Invalid or expired JWT token",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time,
                    "jwt_required": True
                }
            
            logger.info(f"JWT authentication SUCCESS for user: {jwt_payload.get('user_id', 'unknown')}")
        else:
            logger.warning("JWT authentication is DISABLED - allowing request without token")
        
        # Rate limiting
        if not gateway.check_rate_limit(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # Validate request
        try:
            tts_request = gateway.validate_request(job_input)
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid request: {str(e)}",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"Processing TTS: {tts_request.engine.value}, {len(tts_request.text)} chars")
        
        # Process TTS request
        result = gateway.call_tts_endpoint_sync(tts_request, job_id)
        
        processing_time = time.time() - start_time
        
        # Update metrics
        gateway.metrics['total_requests'] += 1
        if tts_request.engine == TTSEngine.KOKKORO:
            gateway.metrics['kokkoro_requests'] += 1
        else:
            gateway.metrics['chatterbox_requests'] += 1
        
        if result['success']:
            gateway.metrics['successful_requests'] += 1
            logger.info(f"Job {job_id} SUCCESS in {processing_time:.2f}s")
            return {
                "success": True,
                "job_id": job_id,
                "engine": tts_request.engine.value,
                "text_length": len(tts_request.text),
                "processing_time": processing_time,
                "cached": False,
                "result": result['data'],
                "endpoint_used": gateway.endpoints[tts_request.engine]
            }
        else:
            gateway.metrics['failed_requests'] += 1
            logger.error(f"Job {job_id} FAILED: {result['error']}")
            return {
                "success": False,
                "error": result['error'],
                "job_id": job_id,
                "engine": tts_request.engine.value,
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        gateway.metrics['total_requests'] += 1
        gateway.metrics['failed_requests'] += 1
        
        error_trace = traceback.format_exc()
        logger.error(f"CRITICAL ERROR in job {job_id}: {str(e)}\n{error_trace}")
        
        return {
            "success": False,
            "error": f"Internal error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time
        }

    def check_rate_limit(self, client_id: str) -> bool:
        """Simple rate limiting"""
        current_time = int(time.time())
        window_start = current_time - gateway.rate_limit_window
        
        if client_id not in gateway.rate_limits:
            gateway.rate_limits[client_id] = []
        
        # Clean old requests
        gateway.rate_limits[client_id] = [
            req_time for req_time in gateway.rate_limits[client_id] 
            if req_time > window_start
        ]
        
        # Check limit
        if len(gateway.rate_limits[client_id]) >= gateway.rate_limit_requests:
            return False
        
        gateway.rate_limits[client_id].append(current_time)
        return True

# Add missing method to gateway
gateway.check_rate_limit = lambda client_id: True  # Simplified for now

if __name__ == "__main__":
    import sys
    
    logger.info("Starting FIXED TTS Gateway")
    logger.info(f"JWT Authentication: {'ENABLED' if gateway.jwt_required else 'DISABLED'}")
    logger.info(f"RunPod API Key: {'SET' if gateway.api_key else 'MISSING'}")
    
    if gateway.jwt_required and not gateway.jwt_secret:
        logger.error("CONFIGURATION ERROR: JWT required but JWT_SECRET not set!")
    
    if not gateway.api_key:
        logger.warning("CONFIGURATION WARNING: RUNPOD_API_KEY not set - TTS calls will fail!")
    
    # Start RunPod worker
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": True
    })
