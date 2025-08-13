import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests
from typing import Optional

app = FastAPI(title="TTS Gateway", version="1.0.0")

class TTSRequest(BaseModel):
    text: str
    model: str = "kokkoro"
    voice: str = "default"
    speed: float = 1.0

@app.get("/")
def root():
    return {"message": "TTS Gateway", "status": "ready"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "gateway"}

@app.post("/synthesize")
def synthesize(request: TTSRequest):
    try:
        # Get model endpoints
        endpoints = {
            'kokkoro': os.getenv('KOKKORO_ENDPOINT'),
            'chatterbox': os.getenv('CHATTERBOX_ENDPOINT')
        }
        
        if request.model not in endpoints or not endpoints[request.model]:
            raise HTTPException(status_code=400, detail=f"Model {request.model} not configured")
        
        # Route to model
        model_endpoint = endpoints[request.model]
        
        response = requests.post(
            model_endpoint,
            json={"input": {"text": request.text, "voice": request.voice, "speed": request.speed}},
            headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY', '')}"} if os.getenv('RUNPOD_API_KEY') else {},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if "output" in result:
                return result["output"]
            else:
                return result
        else:
            raise HTTPException(status_code=500, detail=f"Model error: {response.status_code}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RunPod handler - COPIED FROM WORKING KOKKORO
def handler(event):
    try:
        print(f"Gateway handler received event: {event}")
        
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        print(f"Gateway input data: {input_data}")
        
        # Handle health check
        if input_data.get('action') == 'health_check':
            return {"output": {"status": "healthy", "service": "gateway"}}
        
        # Handle get models
        if input_data.get('action') == 'get_models':
            return {"output": {"models": ["kokkoro", "chatterbox"]}}
        
        # Try multiple ways to get text
        text = input_data.get('text') or input_data.get('prompt') or input_data.get('message')
        
        if not text or not str(text).strip():
            return {
                "error": "Text field is required for Gateway",
                "received_input": input_data
            }
        
        # Extract parameters
        model = input_data.get('model', 'kokkoro')
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        
        try:
            speed = float(speed)
        except (ValueError, TypeError):
            speed = 1.0
        
        print(f"Gateway routing to {model}: text='{str(text)[:50]}...'")
        
        # Get model endpoints
        endpoints = {
            'kokkoro': os.getenv('KOKKORO_ENDPOINT'),
            'chatterbox': os.getenv('CHATTERBOX_ENDPOINT')
        }
        
        if model not in endpoints or not endpoints[model]:
            return {"error": f"Model {model} not configured in Gateway"}
        
        model_endpoint = endpoints[model]
        
        # Route to model endpoint
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
                return result
        else:
            return {"error": f"Model service error: {response.status_code} - {response.text}"}
        
    except Exception as e:
        error_msg = str(e)
        print(f"Gateway handler error: {error_msg}")
        return {"error": error_msg}

# Application startup - COPIED FROM WORKING KOKKORO
if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting TTS Gateway on RunPod...")
        print(f"RunPod Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting TTS Gateway locally...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
