# gateway/main.py - FIXED VERSION WITH PROPER JWT SECURITY
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import timedelta
import httpx
import logging
from typing import Optional
import os

# Import authentication modules
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user, 
    User, 
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Secure TTS Gateway with JWT Authentication",
    description="Centralized gateway for multiple TTS engines - ALL TTS endpoints require JWT authentication",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme - this will be required for TTS endpoints
security = HTTPBearer()

# Pydantic models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    model: str  # kokkoro, chatterbox, etc.

class TTSResponse(BaseModel):
    audio_url: str
    message: str
    model_used: str
    user: str  # Include user info in response

class HealthResponse(BaseModel):
    status: str
    models: dict
    authentication_required: bool

# TTS Engine configurations
TTS_ENGINES = {
    "kokkoro": {
        "url": os.getenv("KOKKORO_URL", "http://kokkoro-service:8001"),
        "health_endpoint": "/health"
    },
    "chatterbox": {
        "url": os.getenv("CHATTERBOX_URL", "http://chatterbox-service:8002"),
        "health_endpoint": "/health"
    }
}

# Custom exception handler for authentication errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication required",
                "message": "You must provide a valid JWT token to access TTS services",
                "instructions": "Please login at /auth/login to get a token, then include it in the Authorization header as 'Bearer <token>'"
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/auth/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint to get JWT access token.
    
    Use credentials:
    - username: testuser or demo
    - password: secret
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information - requires JWT token."""
    return current_user

# ==================== PROTECTED TTS ENDPOINTS ====================

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    tts_request: TTSRequest,
    current_user: User = Depends(get_current_active_user)  # THIS ENFORCES JWT AUTHENTICATION
):
    """
    🔒 SECURE: Generate speech from text using specified TTS model.
    
    ⚠️  REQUIRES VALID JWT TOKEN ⚠️
    
    Headers required:
    Authorization: Bearer <your-jwt-token>
    """
    logger.info(f"🔐 Authenticated TTS request from user: {current_user.username} for model: {tts_request.model}")
    
    # Validate model
    if tts_request.model not in TTS_ENGINES:
        logger.warning(f"❌ User {current_user.username} requested invalid model: {tts_request.model}")
        raise HTTPException(
            status_code=400,
            detail=f"Model '{tts_request.model}' not supported. Available models: {list(TTS_ENGINES.keys())}"
        )
    
    # Get engine configuration
    engine = TTS_ENGINES[tts_request.model]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Add user info to the request to TTS engine
            enhanced_request = tts_request.dict()
            enhanced_request['user'] = current_user.username
            enhanced_request['authenticated'] = True
            
            logger.info(f"🚀 Forwarding authenticated request to {tts_request.model} engine")
            
            # Forward request to appropriate TTS engine
            response = await client.post(
                f"{engine['url']}/generate",
                json=enhanced_request
            )
            
            if response.status_code != 200:
                logger.error(f"❌ TTS engine {tts_request.model} returned error: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS engine error: {response.text}"
                )
            
            result = response.json()
            
            logger.info(f"✅ TTS generation successful for user {current_user.username}")
            
            return TTSResponse(
                audio_url=result.get("audio_url", ""),
                message=f"Speech generated successfully using {tts_request.model}",
                model_used=tts_request.model,
                user=current_user.username
            )
            
    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout when calling TTS engine {tts_request.model} for user {current_user.username}")
        raise HTTPException(
            status_code=504,
            detail=f"TTS engine {tts_request.model} timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"🔥 Request error when calling TTS engine {tts_request.model} for user {current_user.username}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"TTS engine {tts_request.model} unavailable"
        )

@app.get("/models")
async def list_models(current_user: User = Depends(get_current_active_user)):
    """
    🔒 SECURE: List available TTS models.
    
    ⚠️  REQUIRES VALID JWT TOKEN ⚠️
    """
    logger.info(f"🔐 User {current_user.username} requested model list")
    
    return {
        "available_models": list(TTS_ENGINES.keys()),
        "total_models": len(TTS_ENGINES),
        "user": current_user.username,
        "message": "Authentication required for TTS generation"
    }

@app.post("/tts/batch")
async def batch_text_to_speech(
    requests: list[TTSRequest],
    current_user: User = Depends(get_current_active_user)  # ALSO PROTECTED
):
    """
    🔒 SECURE: Generate speech for multiple texts in batch.
    
    ⚠️  REQUIRES VALID JWT TOKEN ⚠️
    """
    logger.info(f"🔐 Batch TTS request from user: {current_user.username} for {len(requests)} items")
    
    if len(requests) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400,
            detail="Batch size limited to 10 requests"
        )
    
    results = []
    for i, tts_request in enumerate(requests):
        try:
            # Process each request individually
            result = await text_to_speech(tts_request, current_user)
            results.append({"index": i, "result": result, "status": "success"})
        except Exception as e:
            results.append({"index": i, "error": str(e), "status": "failed"})
    
    return {
        "results": results,
        "total_requested": len(requests),
        "successful": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "failed"]),
        "user": current_user.username
    }

# ==================== PUBLIC ENDPOINTS (No Authentication Required) ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    ✅ PUBLIC: Health check endpoint (no authentication required).
    Check the status of all TTS engines.
    
    This is the ONLY endpoint that doesn't require authentication.
    """
    logger.info("🏥 Public health check requested")
    
    models_status = {}
    
    for model_name, engine in TTS_ENGINES.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{engine['url']}{engine['health_endpoint']}")
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
    
    return HealthResponse(
        status=overall_status,
        models=models_status,
        authentication_required=True
    )

@app.get("/")
async def root():
    """✅ PUBLIC: Root endpoint with API information."""
    return {
        "message": "🔒 Secure TTS Gateway API with JWT Authentication",
        "version": "1.0.0",
        "security": "🛡️ ALL TTS endpoints require JWT authentication",
        "endpoints": {
            "🔓 public": {
                "health": "/health",
                "docs": "/docs",
                "login": "/auth/login"
            },
            "🔒 protected (JWT required)": {
                "tts": "/tts",
                "batch_tts": "/tts/batch", 
                "models": "/models",
                "user_info": "/auth/me"
            }
        },
        "instructions": {
            "step_1": "POST /auth/login with username/password to get JWT token",
            "step_2": "Include 'Authorization: Bearer <token>' header in all TTS requests",
            "step_3": "Use /tts endpoint to generate speech"
        },
        "authentication": "🚨 JWT Bearer Token REQUIRED for all TTS operations"
    }

# ==================== SECURITY MIDDLEWARE ====================

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Security middleware to log all requests and ensure TTS endpoints are protected.
    """
    # Log all incoming requests
    logger.info(f"📥 {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    # Check if this is a TTS endpoint
    protected_paths = ["/tts", "/models", "/auth/me"]
    is_protected_path = any(request.url.path.startswith(path) for path in protected_paths)
    
    if is_protected_path:
        # Verify Authorization header exists for protected paths
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"🚨 Unauthorized access attempt to {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": f"Access to {request.url.path} requires JWT authentication",
                    "instructions": "Login at /auth/login to get a token"
                }
            )
    
    response = await call_next(request)
    
    # Log response status
    logger.info(f"📤 Response: {response.status_code}")
    
    return response

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting SECURE TTS Gateway with JWT Authentication")
    logger.info("🔒 ALL TTS endpoints require valid JWT tokens")
    logger.info("🔓 Public endpoints: /, /health, /docs, /auth/login")
    uvicorn.run(app, host="0.0.0.0", port=8000)
