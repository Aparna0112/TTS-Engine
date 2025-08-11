import asyncio
import json
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import httpx
import uvicorn
from config import Config
from models_registry import ModelsRegistry

app = FastAPI(title="TTS Gateway", version="1.0.0")
config = Config()
registry = ModelsRegistry()

class TTSRequest(BaseModel):
    text: str
    model: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0

class TTSResponse(BaseModel):
    audio_url: str
    model_used: str
    duration: Optional[float] = None
    status: str = "success"

@app.get("/")
async def root():
    return {"message": "TTS Gateway Running", "available_models": registry.get_available_models()}

@app.get("/models")
async def get_models():
    return {"models": registry.get_available_models()}

@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    if request.model not in registry.get_available_models():
        raise HTTPException(status_code=400, f"Model {request.model} not available")
    
    model_endpoint = registry.get_model_endpoint(request.model)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{model_endpoint}/synthesize",
                json=request.dict()
            )
            response.raise_for_status()
            result = response.json()
            return TTSResponse(**result)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, f"Model service unavailable: {str(e)}")

@app.get("/health")
async def health_check():
    model_status = {}
    for model_name in registry.get_available_models():
        endpoint = registry.get_model_endpoint(model_name)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{endpoint}/health")
                model_status[model_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            model_status[model_name] = "unreachable"
    
    return {"gateway": "healthy", "models": model_status}

# RunPod handler function
def handler(event):
    """RunPod serverless handler"""
    try:
        # Extract request data
        input_data = event.get('input', {})
        
        # Handle different request types
        if 'text' in input_data and 'model' in input_data:
            # TTS synthesis request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            request = TTSRequest(**input_data)
            result = loop.run_until_complete(synthesize_text(request))
            
            return {"output": result.dict()}
        
        elif input_data.get('action') == 'get_models':
            return {"output": {"models": registry.get_available_models()}}
        
        else:
            return {"error": "Invalid request format"}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Check if running in RunPod environment
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        runpod.serverless.start({"handler": handler})
    else:
        # Local development
        uvicorn.run(app, host="0.0.0.0", port=8000)
