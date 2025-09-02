# rp_handler.py - SECURE RunPod handler that properly enforces JWT authentication
import runpod
import json
import traceback
import logging
import time
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from jose import JWTError, jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(filename)-15s :%(lineno)-4d %(asctime)s,%(msecs)03d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add current directory to Python path for imports
sys.path.append('/app')

try:
    # Import authentication functions directly instead of using TestClient
    from auth import (
        authenticate_user, 
        create_access_token, 
        get_user,
        verify_password,
        SECRET_KEY,
        ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES
    )
    from main import TTS_ENGINES  # Import TTS engine configurations
    logger.info("✅ Successfully imported authentication modules")
except ImportError as e:
    logger.error(f"❌ Failed to import authentication modules: {e}")
    raise

import httpx  # For making requests to TTS engines
from datetime import timedelta

class SecureRunPodHandler:
    """Secure RunPod handler that properly enforces JWT authentication"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("🛡️  Secure RunPod TTS Handler initialized with JWT enforcement")
    
    def _validate_jwt_token(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user info"""
        try:
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.replace("Bearer ", "")
            
            # Decode and validate JWT token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            
            if username is None:
                return None
            
            # Get user from database
            user = get_user(username)
            if user is None or not user.is_active:
                return None
            
            return {
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active
            }
            
        except JWTError as e:
            logger.warning(f"🔒 JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"🔥 Token validation error: {e}")
            return None
    
    def _handle_login(self, body: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Handle login requests and return JWT token"""
        logger.info(f"🔐 Job {job_id}: Processing login request")
        
        try:
            username = body.get("username")
            password = body.get("password")
            
            if not username or not password:
                logger.warning(f"❌ Job {job_id}: Missing username or password")
                return {
                    "statusCode": 400,
                    "body": {"detail": "Username and password are required"},
                    "headers": {"Content-Type": "application/json"}
                }
            
            # Authenticate user
            user = authenticate_user(username, password)
            if not user:
                logger.warning(f"❌ Job {job_id}: Authentication failed for user: {username}")
                return {
                    "statusCode": 401,
                    "body": {"detail": "Incorrect username or password"},
                    "headers": {"Content-Type": "application/json"}
                }
            
            # Create JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username}, 
                expires_delta=access_token_expires
            )
            
            logger.info(f"✅ Job {job_id}: Login successful for user: {username}")
            
            return {
                "statusCode": 200,
                "body": {
                    "access_token": access_token,
                    "token_type": "bearer"
                },
                "headers": {"Content-Type": "application/json"}
            }
            
        except Exception as e:
            logger.error(f"🔥 Job {job_id}: Login error: {e}")
            return {
                "statusCode": 500,
                "body": {"detail": f"Login error: {str(e)}"},
                "headers": {"Content-Type": "application/json"}
            }
    
    def _handle_user_info(self, headers: Dict[str, str], job_id: str) -> Dict[str, Any]:
        """Handle user info requests"""
        logger.info(f"👤 Job {job_id}: Processing user info request")
        
        # Validate JWT token
        auth_header = headers.get("Authorization", "")
        user = self._validate_jwt_token(auth_header)
        
        if not user:
            logger.warning(f"🔒 Job {job_id}: Unauthorized user info request")
            return {
                "statusCode": 401,
                "body": {
                    "error": "Authentication required",
                    "message": "Valid JWT token required for user information"
                },
                "headers": {"Content-Type": "application/json"}
            }
        
        logger.info(f"✅ Job {job_id}: User info request successful for: {user['username']}")
        return {
            "statusCode": 200,
            "body": user,
            "headers": {"Content-Type": "application/json"}
        }
    
    def _handle_models_list(self, headers: Dict[str, str], job_id: str) -> Dict[str, Any]:
        """Handle models list requests"""
        logger.info(f"📋 Job {job_id}: Processing models list request")
        
        # Validate JWT token
        auth_header = headers.get("Authorization", "")
        user = self._validate_jwt_token(auth_header)
        
        if not user:
            logger.warning(f"🔒 Job {job_id}: Unauthorized models list request")
            return {
                "statusCode": 401,
                "body": {
                    "error": "Authentication required",
                    "message": "Valid JWT token required to list models"
                },
                "headers": {"Content-Type": "application/json"}
            }
        
        logger.info(f"✅ Job {job_id}: Models list request successful for: {user['username']}")
        return {
            "statusCode": 200,
            "body": {
                "available_models": list(TTS_ENGINES.keys()),
                "total_models": len(TTS_ENGINES),
                "user": user['username'],
                "message": "Authentication required for TTS generation"
            },
            "headers": {"Content-Type": "application/json"}
        }
    
    async def _handle_tts_request(self, body: Dict[str, Any], headers: Dict[str, str], job_id: str) -> Dict[str, Any]:
        """Handle TTS generation requests with proper JWT validation"""
        logger.info(f"🎵 Job {job_id}: Processing TTS request")
        
        # FIRST: Validate JWT token - THIS IS THE CRITICAL SECURITY CHECK
        auth_header = headers.get("Authorization", "")
        user = self._validate_jwt_token(auth_header)
        
        if not user:
            logger.warning(f"🔒 Job {job_id}: Unauthorized TTS request - NO VALID JWT TOKEN")
            return {
                "statusCode": 401,
                "body": {
                    "error": "Authentication required", 
                    "message": "You must provide a valid JWT token to access TTS services",
                    "instructions": "Please login at /auth/login to get a token, then include it in the Authorization header as 'Bearer <token>'"
                },
                "headers": {"Content-Type": "application/json"}
            }
        
        # JWT token is valid, proceed with TTS generation
        logger.info(f"🔐 Job {job_id}: JWT validated - user: {user['username']}")
        
        try:
            # Validate TTS request
            text = body.get('text')
            model = body.get('model')
            voice = body.get('voice', 'default')
            speed = body.get('speed', 1.0)
            
            if not text:
                logger.warning(f"⚠️  Job {job_id}: Missing text in TTS request")
                return {
                    "statusCode": 400,
                    "body": {"error": "Text is required for TTS generation"},
                    "headers": {"Content-Type": "application/json"}
                }
            
            if not model or model not in TTS_ENGINES:
                logger.warning(f"⚠️  Job {job_id}: Invalid model: {model}")
                return {
                    "statusCode": 400,
                    "body": {
                        "error": f"Invalid model '{model}'. Available models: {list(TTS_ENGINES.keys())}"
                    },
                    "headers": {"Content-Type": "application/json"}
                }
            
            logger.info(f"🤖 Job {job_id}: TTS request - User: {user['username']}, Model: {model}, Text length: {len(text)}")
            
            # Get engine configuration
            engine = TTS_ENGINES[model]
            
            # Forward request to TTS engine
            async with httpx.AsyncClient(timeout=30.0) as client:
                enhanced_request = {
                    "text": text,
                    "model": model,
                    "voice": voice,
                    "speed": speed,
                    "user": user['username'],
                    "authenticated": True
                }
                
                logger.info(f"🚀 Job {job_id}: Forwarding to TTS engine: {engine['url']}")
                
                response = await client.post(
                    f"{engine['url']}/generate",
                    json=enhanced_request
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Job {job_id}: TTS generation successful for user: {user['username']}")
                    
                    return {
                        "statusCode": 200,
                        "body": {
                            "audio_url": result.get("audio_url", ""),
                            "message": f"Speech generated successfully using {model}",
                            "model_used": model,
                            "user": user['username']
                        },
                        "headers": {"Content-Type": "application/json"}
                    }
                else:
                    logger.error(f"❌ Job {job_id}: TTS engine error: {response.status_code}")
                    return {
                        "statusCode": response.status_code,
                        "body": {"error": f"TTS engine error: {response.text}"},
                        "headers": {"Content-Type": "application/json"}
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"⏰ Job {job_id}: TTS engine timeout")
            return {
                "statusCode": 504,
                "body": {"error": f"TTS engine {model} timeout"},
                "headers": {"Content-Type": "application/json"}
            }
        except Exception as e:
            logger.error(f"🔥 Job {job_id}: TTS generation error: {e}")
            logger.error(f"🔥 Job {job_id}: Traceback: {traceback.format_exc()}")
            return {
                "statusCode": 500,
                "body": {"error": f"TTS generation error: {str(e)}"},
                "headers": {"Content-Type": "application/json"}
            }
    
    def _handle_health_check(self, job_id: str) -> Dict[str, Any]:
        """Handle health check requests (PUBLIC - no auth required)"""
        logger.info(f"🏥 Job {job_id}: Processing health check (public)")
        
        try:
            # Check TTS engines health
            models_status = {}
            
            for model_name, engine in TTS_ENGINES.items():
                try:
                    import httpx
                    response = httpx.get(f"{engine['url']}{engine['health_endpoint']}", timeout=5.0)
                    models_status[model_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "url": engine['url']
                    }
                except Exception as e:
                    models_status[model_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "url": engine['url']
                    }
            
            overall_status = "healthy" if all(
                model["status"] == "healthy" for model in models_status.values()
            ) else "degraded"
            
            logger.info(f"✅ Job {job_id}: Health check completed - status: {overall_status}")
            
            return {
                "statusCode": 200,
                "body": {
                    "status": overall_status,
                    "models": models_status,
                    "authentication_required": True,
                    "message": "🔒 ALL TTS endpoints require JWT authentication"
                },
                "headers": {"Content-Type": "application/json"}
            }
            
        except Exception as e:
            logger.error(f"🔥 Job {job_id}: Health check error: {e}")
            return {
                "statusCode": 500,
                "body": {"error": f"Health check error: {str(e)}"},
                "headers": {"Content-Type": "application/json"}
            }
    
    async def process_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Main request processing with ENFORCED JWT authentication"""
        job_id = event.get('id', 'unknown')
        start_time = time.time()
        
        logger.info(f"🎯 Processing job {job_id}")
        
        try:
            # Extract input data
            input_data = event.get('input', {})
            if not input_data:
                logger.error(f"❌ Job {job_id}: No input data provided")
                return {
                    "statusCode": 400,
                    "body": {"error": "No input data provided"},
                    "headers": {"Content-Type": "application/json"}
                }
            
            method = input_data.get('method', 'POST')
            path = input_data.get('path', '/tts')
            headers = input_data.get('headers', {})
            body = input_data.get('body', {})
            
            logger.info(f"🔧 Job {job_id}: {method} {path}")
            
            # Route requests with PROPER SECURITY CHECKS
            if path == '/auth/login' and method == 'POST':
                # LOGIN: Public endpoint
                result = self._handle_login(body, job_id)
                
            elif path == '/health' and method == 'GET':
                # HEALTH: Public endpoint
                result = self._handle_health_check(job_id)
                
            elif path == '/auth/me' and method == 'GET':
                # USER INFO: Requires JWT
                result = self._handle_user_info(headers, job_id)
                
            elif path == '/models' and method == 'GET':
                # MODELS LIST: Requires JWT
                result = self._handle_models_list(headers, job_id)
                
            elif path.startswith('/tts') and method == 'POST':
                # TTS GENERATION: Requires JWT - THIS IS THE CRITICAL PATH
                result = await self._handle_tts_request(body, headers, job_id)
                
            elif path == '/' and method == 'GET':
                # ROOT: Public endpoint
                result = {
                    "statusCode": 200,
                    "body": {
                        "message": "🔒 Secure TTS Gateway API with JWT Authentication",
                        "version": "1.0.0",
                        "security": "🛡️ ALL TTS endpoints require JWT authentication",
                        "authentication": "🚨 JWT Bearer Token REQUIRED for all TTS operations"
                    },
                    "headers": {"Content-Type": "application/json"}
                }
                
            else:
                # UNSUPPORTED: Return error
                logger.warning(f"⚠️  Job {job_id}: Unsupported endpoint: {method} {path}")
                result = {
                    "statusCode": 405,
                    "body": {"error": f"Method {method} not supported for path {path}"},
                    "headers": {"Content-Type": "application/json"}
                }
            
            # Log completion
            processing_time = time.time() - start_time
            status_code = result.get("statusCode", 500)
            
            if status_code == 200:
                logger.info(f"✅ Job {job_id}: Completed successfully in {processing_time:.2f}s")
            elif status_code == 401:
                logger.warning(f"🔒 Job {job_id}: Unauthorized request blocked in {processing_time:.2f}s")
            else:
                logger.warning(f"⚠️  Job {job_id}: Completed with status {status_code} in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"🔥 Job {job_id}: Unexpected error after {processing_time:.2f}s: {e}")
            logger.error(f"🔥 Job {job_id}: Full traceback:\n{traceback.format_exc()}")
            
            return {
                "statusCode": 500,
                "body": {
                    "error": "Internal server error",
                    "message": str(e),
                    "job_id": job_id
                },
                "headers": {"Content-Type": "application/json"}
            }

# Create handler instance
handler_instance = SecureRunPodHandler()

def handler(event):
    """RunPod serverless handler entry point - SECURE VERSION"""
    import asyncio
    
    # Run the async handler
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(handler_instance.process_request(event))
        return result
    finally:
        loop.close()

# Start RunPod serverless worker
if __name__ == "__main__":
    logger.info("🛡️  Starting SECURE RunPod TTS Handler with JWT enforcement")
    logger.info(f"⏰ Handler started at: {datetime.now().isoformat()}")
    logger.info("🚨 ALL TTS endpoints now require valid JWT tokens")
    
    # Start RunPod serverless worker
    runpod.serverless.start({"handler": handler})
