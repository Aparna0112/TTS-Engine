# gateway/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
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
    title="TTS Gateway with JWT Authentication",
    description="Centralized gateway for multiple TTS engines with JWT authentication",
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

class HealthResponse(BaseModel):
    status: str
    models: dict

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
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    tts_request: TTSRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate speech from text using specified TTS model.
    Requires valid JWT token.
    """
    logger.info(f"TTS request from user {current_user.username} for model {tts_request.model}")
    
    # Validate model
    if tts_request.model not in TTS_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{tts_request.model}' not supported. Available models: {list(TTS_ENGINES.keys())}"
        )
    
    # Get engine configuration
    engine = TTS_ENGINES[tts_request.model]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward request to appropriate TTS engine
            response = await client.post(
                f"{engine['url']}/generate",
                json=tts_request.dict()
            )
            
            if response.status_code != 200:
                logger.error(f"TTS engine {tts_request.model} returned error: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS engine error: {response.text}"
                )
            
            result = response.json()
            
            return TTSResponse(
                audio_url=result.get("audio_url", ""),
                message=f"Speech generated successfully using {tts_request.model}",
                model_used=tts_request.model
            )
            
    except httpx.TimeoutException:
        logger.error(f"Timeout when calling TTS engine {tts_request.model}")
        raise HTTPException(
            status_code=504,
            detail=f"TTS engine {tts_request.model} timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error when calling TTS engine {tts_request.model}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"TTS engine {tts_request.model} unavailable"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Public health check endpoint (no authentication required).
    Check the status of all TTS engines.
    """
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
        models=models_status
    )

@app.get("/models")
async def list_models(current_user: User = Depends(get_current_active_user)):
    """
    List available TTS models.
    Requires valid JWT token.
    """
    return {
        "available_models": list(TTS_ENGINES.keys()),
        "total_models": len(TTS_ENGINES)
    }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "TTS Gateway API with JWT Authentication",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/login",
            "tts": "/tts",
            "health": "/health",
            "models": "/models",
            "docs": "/docs"
        },
        "authentication": "JWT Bearer Token Required (except /health and /docs)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
