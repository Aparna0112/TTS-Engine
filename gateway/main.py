import os
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
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
    audio_base64: Optional[str] = None
    audio_data_url: Optional[str] = None
    model_used: str
    duration: Optional[float] = None
    status: str = "success"

@app.get("/")
async def root():
    return {
        "message": "TTS Gateway Running", 
        "available_models": registry.get_available_models(),
        "version": "1.0.0"
    }

@app.get("/models")
async def get_models():
    return {"models": registry.get_available_models()}

@app.get("/health")
async def health_check():
    model_status = {}
    for model_name in registry.get_available_models():
        endpoint = registry.get_model_endpoint(model_name)
        if endpoint:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        endpoint,
                        json={"input": {"text": "health check"}},
                        headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY', 'test')}"}
                    )
                    model_status[model_name] = "healthy" if response.status_code == 200 else "unhealthy"
            except:
                model_status[model_name] = "unreachable"
        else:
            model_status[model_name] = "not_configured"
    
    return {"gateway": "healthy", "models": model_status}

@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    if request.model not in registry.get_available_models():
        raise HTTPException(
            status_code=400, 
            detail=f"Model '{request.model}' not available. Available models: {registry.get_available_models()}"
        )
    
    model_endpoint = registry.get_model_endpoint(request.model)
    if not model_endpoint:
        raise HTTPException(
            status_code=503, 
            detail=f"Model '{request.model}' endpoint not configured"
        )
    
    # Prepare request for model endpoint
    model_request = {
        "input": {
            "text": request.text,
            "voice": request.voice,
            "speed": request.speed,
            "pitch": request.pitch
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            headers = {}
            if os.getenv('RUNPOD_API_KEY'):
                headers["Authorization"] = f"Bearer {os.getenv('RUNPOD_API_KEY')}"
            
            response = await client.post(
                model_endpoint,
                json=model_request,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            if "output" in result:
                output = result["output"]
                return TTSResponse(
                    audio_url=output.get("audio_url", ""),
                    audio_base64=output.get("audio_base64"),
                    audio_data_url=output.get("audio_data_url"),
                    model_used=output.get("model_used", request.model),
                    duration=output.get("duration"),
                    status=output.get("status", "success")
                )
            else:
                raise HTTPException(status_code=500, detail="Invalid response from model service")
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Model service unavailable: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Model service error: {e.response.text}")

# RunPod handler function
def handler(event):
    """RunPod serverless handler"""
    try:
        input_data = event.get('input', {})
        
        if input_data.get('action') == 'get_models':
            return {"output": {"models": registry.get_available_models()}}
        
        if input_data.get('action') == 'health_check':
            return {"output": {"status": "healthy", "models": registry.get_available_models()}}
        
        # Handle TTS synthesis request
        if 'text' in input_data and 'model' in input_data:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            request = TTSRequest(**input_data)
            result = loop.run_until_complete(synthesize_text(request))
            
            return {"output": result.dict()}
        
        return {"error": "Invalid request format. Required: text and model"}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting TTS Gateway on RunPod...")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting TTS Gateway locally...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
