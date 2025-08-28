#!/usr/bin/env python3
"""
Production-Ready RunPod Handler for TTS Gateway
Focused version with only Kokkoro + Chatterbox engines
Based on your existing 2-engine setup
"""

import runpod
import requests
import os
import time
import logging
import json
import hashlib
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import redis
from datetime import datetime
import traceback
import jwt
from functools import wraps

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
        if len(self.text) > 5000:  # Reasonable limit for TTS
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
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '300'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
        
        # JWT Configuration (OPTIONAL - you can enable this)
        self.jwt_secret = os.getenv('JWT_SECRET')  # Set this if you want JWT auth
        self.jwt_required = os.getenv('REQUIRE_JWT', 'false').lower() == 'true'
        
        # Redis for caching (OPTIONAL - improves performance)
        self.redis_client = None
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable: {e}")
                self.redis_client = None
        
        # Simple rate limiting (in-memory)
        self.rate_limits = {}
        self.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
        self.rate_limit_window = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
        
        # Metrics tracking
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'kokkoro_requests': 0,
            'chatterbox_requests': 0
        }

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token (OPTIONAL - only if you want authentication)"""
        if not self.jwt_secret:
            return None
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None

    def check_rate_limit(self, client_id: str) -> bool:
        """Simple rate limiting"""
        current_time = int(time.time())
        window_start = current_time - self.rate_limit_window
        
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = []
        
        # Clean old requests
        self.rate_limits[client_id] = [
            req_time for req_time in self.rate_limits[client_id] 
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.rate_limits[client_id]) >= self.rate_limit_requests:
            return False
        
        self.rate_limits[client_id].append(current_time)
        return True

    def get_cache_key(self, request: TTSRequest) -> str:
        """Generate cache key"""
        content = f"{request.engine.value}:{request.text}:{request.voice}:{request.speed}:{request.language}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(f"tts:{cache_key}")
            if cached:
                self.metrics['cache_hits'] += 1
                logger.info(f"✅ Cache hit: {cache_key[:8]}...")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache result"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(f"tts:{cache_key}", self.cache_ttl, json.dumps(result))
            logger.info(f"💾 Cached: {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def call_tts_endpoint(self, request: TTSRequest, job_id: str) -> Dict[str, Any]:
        """Call TTS endpoint with your existing logic + improvements"""
        endpoint_url = self.endpoints[request.engine]
        
        if not self.api_key:
            logger.warning(f"⚠️ Job {job_id}: No API key, using dummy response")
            return {
                "success": True,
                "data": {
                    "message": "TTS Gateway working (no API key configured)",
                    "request": request.__dict__,
                    "endpoint": endpoint_url
                }
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # Your existing payload logic
        payload = {
            'text': request.text,
            'voice': request.voice,
            'speed': request.speed
        }
        
        # Engine-specific parameters (keeping your existing logic)
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
        
        # Enhanced retry logic with async
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🔄 Job {job_id}: Calling {request.engine.value} (attempt {attempt + 1})")
                    
                    async with session.post(endpoint_url, json=request_payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"✅ Job {job_id}: Success from {request.engine.value}")
                            return {"success": True, "data": result}
                        else:
                            error_text = await response.text()
                            error_msg = f"HTTP {response.status}: {error_text[:200]}"
                            logger.error(f"❌ Job {job_id}: {error_msg}")
                            
                            if attempt == self.max_retries - 1:
                                return {"success": False, "error": error_msg}
                                
                except asyncio.TimeoutError:
                    logger.error(f"⏰ Job {job_id}: Timeout on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        return {"success": False, "error": "Request timeout"}
                        
                except Exception as e:
                    logger.error(f"💥 Job {job_id}: Error: {str(e)}")
                    if attempt == self.max_retries - 1:
                        return {"success": False, "error": str(e)}
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
        
        return {"success": False, "error": "Max retries exceeded"}

    def validate_request(self, job_input: Dict[str, Any]) -> TTSRequest:
        """Validate request (keeping your existing validation + improvements)"""
        if not job_input.get('text'):
            raise ValueError("Missing required parameter: 'text'")
        
        text = job_input['text'].strip()
        if not text:
            raise ValueError("Text cannot be empty")
        
        # Parse engine - only your 2 engines
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
    Enhanced version of your original handler with production improvements
    """
    start_time = time.time()
    job_id = job.get('id', f'job_{int(time.time())}')
    client_id = job.get('webhook', 'anonymous')
    
    try:
        logger.info(f"🎯 Processing job {job_id}")
        job_input = job.get('input', {})
        
        # JWT Authentication (OPTIONAL - only if enabled)
        if gateway.jwt_required:
            auth_token = job_input.get('auth_token')
            if not auth_token:
                return {
                    "error": "Authentication required",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time
                }
            
            jwt_payload = gateway.verify_jwt_token(auth_token)
            if not jwt_payload:
                return {
                    "error": "Invalid or expired token",
                    "job_id": job_id,
                    "processing_time": time.time() - start_time
                }
            
            logger.info(f"🔐 Authenticated user: {jwt_payload.get('user_id', 'unknown')}")
        
        # Handle health check (improved)
        if job_input.get('action') == 'health':
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "gateway_version": "1.1.0",
                "available_engines": ["kokkoro", "chatterbox"],  # Your engines only
                "endpoints": {
                    "kokkoro": gateway.endpoints[TTSEngine.KOKKORO],
                    "chatterbox": gateway.endpoints[TTSEngine.CHATTERBOX]
                },
                "features": {
                    "caching": gateway.redis_client is not None,
                    "jwt_auth": gateway.jwt_required,
                    "rate_limiting": True
                },
                "metrics": gateway.metrics,
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # Rate limiting
        if not gateway.check_rate_limit(client_id):
            logger.warning(f"🚫 Rate limit exceeded for {client_id}")
            return {
                "error": "Rate limit exceeded",
                "job_id": job_id,
                "processing_time": time.time() - start_time,
                "retry_after": gateway.rate_limit_window
            }
        
        # Validate request
        try:
            tts_request = gateway.validate_request(job_input)
        except ValueError as e:
            logger.error(f"❌ Validation error: {str(e)}")
            return {
                "error": f"Invalid request: {str(e)}",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"📝 Job {job_id}: {tts_request.engine.value}, {len(tts_request.text)} chars")
        
        # Check cache
        cache_key = gateway.get_cache_key(tts_request)
        cached_result = gateway.get_cached_result(cache_key)
        
        if cached_result:
            gateway.metrics['total_requests'] += 1
            gateway.metrics['successful_requests'] += 1
            return {
                "success": True,
                "job_id": job_id,
                "engine": tts_request.engine.value,
                "text_length": len(tts_request.text),
                "processing_time": time.time() - start_time,
                "cached": True,
                "result": cached_result
            }
        
        # Process TTS request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                gateway.call_tts_endpoint(tts_request, job_id)
            )
        finally:
            loop.close()
        
        processing_time = time.time() - start_time
        
        # Update metrics
        gateway.metrics['total_requests'] += 1
        if tts_request.engine == TTSEngine.KOKKORO:
            gateway.metrics['kokkoro_requests'] += 1
        else:
            gateway.metrics['chatterbox_requests'] += 1
        
        if result['success']:
            gateway.metrics['successful_requests'] += 1
            gateway.cache_result(cache_key, result['data'])
            
            logger.info(f"✅ Job {job_id}: Success in {processing_time:.2f}s")
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
            logger.error(f"❌ Job {job_id}: Failed - {result['error']}")
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
        logger.error(f"💥 Job {job_id}: Critical error: {str(e)}\n{error_trace}")
        
        return {
            "success": False,
            "error": f"Internal error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time
        }

# Your existing test function enhanced
def test_handler():
    """Test function matching your setup"""
    print("🧪 Testing Your 2-Engine TTS Gateway...")
    
    # Health check
    print("\n=== Health Check ===")
    health = handler({"id": "test_health", "input": {"action": "health"}})
    print(json.dumps(health, indent=2))
    
    # Test both your engines
    engines = ["kokkoro", "chatterbox"]
    for engine in engines:
        print(f"\n=== Testing {engine.upper()} ===")
        result = handler({
            "id": f"test_{engine}",
            "input": {
                "text": f"Testing {engine} TTS engine",
                "engine": engine
            }
        })
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_handler()
    else:
        logger.info("🚀 Starting Enhanced TTS Gateway (Kokkoro + Chatterbox)")
        logger.info(f"🔧 Features enabled:")
        logger.info(f"   - Caching: {'Yes' if gateway.redis_client else 'No'}")
        logger.info(f"   - JWT Auth: {'Yes' if gateway.jwt_required else 'No (optional)'}")
        logger.info(f"   - Rate Limiting: Yes ({gateway.rate_limit_requests}/hour)")
        logger.info(f"   - Async Processing: Yes")
        logger.info(f"   - Enhanced Logging: Yes")
        
        # Start RunPod worker
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
