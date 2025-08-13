import os
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn

app = FastAPI(title="TTS Gateway", version="1.0.0")

class TTSRequest(BaseModel):
    text: str
    model: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0

class TTSResponse(BaseModel):
    audio_url: str
    audio_base64: Optional[str] = None
    audio_data_url: Optional[str] = None
    model_used: str
    duration: Optional[float] = None
    status: str = "success"

# Model endpoints configuration
def get_model_endpoints():
    return {
        'kokkoro': os.getenv('KOKKORO_ENDPOINT'),
        'chatterbox': os.getenv('CHATTERBOX_ENDPOINT')
    }

@app.get("/")
def root():
    endpoints = get_model_endpoints()
    available_models = [model for model, endpoint in endpoints.items() if endpoint]
    
    return {
        "message": "TTS Gateway Running", 
        "available_models": available_models,
        "version": "1.0.0",
        "endpoints_configured": len(available_models),
        "total_models": len(endpoints)
    }

@app.get("/models")
def get_models():
    endpoints = get_model_endpoints()
    available_models = [model for model, endpoint in endpoints.items() if endpoint]
    return {"models": available_models}

@app.get("/health")
async def health_check():
    endpoints = get_model_endpoints()
    model_status = {}
    
    for model_name, endpoint_url in endpoints.items():
        if endpoint_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    headers = {}
                    if os.getenv('RUNPOD_API_KEY'):
                        headers["Authorization"] = f"Bearer {os.getenv('RUNPOD_API_KEY')}"
                    
                    response = await client.post(
                        endpoint_url,
                        json={"input": {"text": "health check"}},
                        headers=headers
                    )
                    model_status[model_name] = "healthy" if response.status_code == 200 else "unhealthy"
            except:
                model_status[model_name] = "unreachable"
        else:
            model_status[model_name] = "not_configured"
    
    return {"gateway": "healthy", "models": model_status}

@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    endpoints = get_model_endpoints()
    
    if request.model not in endpoints:
        available = [model for model, endpoint in endpoints.items() if endpoint]
        raise HTTPException(
            status_code=400, 
            detail=f"Model '{request.model}' not available. Available models: {available}"
        )
    
    model_endpoint = endpoints[request.model]
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
            "speed": request.speed
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            headers = {"Content-Type": "application/json"}
            if os.getenv('RUNPOD_API_KEY'):
                headers["Authorization"] = f"Bearer {os.getenv('RUNPOD_API_KEY')}"
            
            print(f"Gateway routing to {request.model}: {model_endpoint}")
            
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
            elif "error" in result:
                raise HTTPException(status_code=500, detail=f"Model error: {result['error']}")
            else:
                raise HTTPException(status_code=500, detail="Invalid response from model service")
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Model service unavailable: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Model service error: {e.response.text}")

# RunPod handler function - FIXED SYNCHRONOUS VERSION
def handler(event):
    """RunPod serverless handler for Gateway"""
    try:
        print(f"Gateway handler received event: {event}")
        
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        # Handle different request types
        action = input_data.get('action')
        
        if action == 'get_models':
            endpoints = get_model_endpoints()
            available_models = [model for model, endpoint in endpoints.items() if endpoint]
            return {"output": {"models": available_models}}
        
        if action == 'health_check':
            endpoints = get_model_endpoints()
            available_models = [model for model, endpoint in endpoints.items() if endpoint]
            return {"output": {"status": "healthy", "models": available_models}}
        
        # Handle TTS synthesis request
        text = input_data.get('text') or input_data.get('prompt') or input_data.get('message')
        model = input_data.get('model', 'kokkoro')  # Default to kokkoro
        
        if not text:
            return {"error": "Text field is required for TTS synthesis"}
        
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        
        try:
            speed = float(speed)
        except (ValueError, TypeError):
            speed = 1.0
        
        print(f"Gateway processing TTS: model={model}, text='{str(text)[:50]}...'")
        
        # For now, create a synchronous version for RunPod
        # This is a simplified version - in production you might want to use async
        import requests
        
        endpoints = get_model_endpoints()
        
        if model not in endpoints or not endpoints[model]:
            available = [m for m, e in endpoints.items() if e]
            return {"error": f"Model '{model}' not available. Available: {available}"}
        
        model_endpoint = endpoints[model]
        
        # Make request to model
        headers = {"Content-Type": "application/json"}
        if os.getenv('RUNPOD_API_KEY'):
            headers["Authorization"] = f"Bearer {os.getenv('RUNPOD_API_KEY')}"
        
        response = requests.post(
            model_endpoint,
            json={"input": {"text": text, "voice": voice, "speed": speed}},
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if "output" in result:
                return {"output": result["output"]}
            else:
                return {"error": f"Model returned: {result}"}
        else:
            return {"error": f"Model service error: {response.status_code} - {response.text}"}
        
    except Exception as e:
        print(f"Gateway handler error: {str(e)}")
        return {"error": f"Gateway error: {str(e)}"}

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting TTS Gateway on RunPod...")
        print(f"Configured endpoints: {get_model_endpoints()}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting TTS Gateway locally...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
