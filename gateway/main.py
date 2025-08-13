import os
import requests
from typing import Dict, Optional

def handler(event):
    """Simple working Gateway handler"""
    try:
        print(f"Gateway received event: {event}")
        
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        # Handle health check
        if input_data.get('action') == 'health_check':
            return {
                "output": {
                    "status": "healthy",
                    "service": "gateway",
                    "models": ["kokkoro", "chatterbox"]
                }
            }
        
        # Handle get models
        if input_data.get('action') == 'get_models':
            return {
                "output": {
                    "models": ["kokkoro", "chatterbox"]
                }
            }
        
        # Get text from input
        text = input_data.get('text') or input_data.get('prompt') or input_data.get('message')
        
        if not text:
            return {
                "error": "Text field is required",
                "usage": "Send: {'input': {'text': 'your text', 'model': 'kokkoro'}}"
            }
        
        # Get model (default to kokkoro)
        model = input_data.get('model', 'kokkoro')
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        
        # Model endpoints
        endpoints = {
            'kokkoro': os.getenv('KOKKORO_ENDPOINT'),
            'chatterbox': os.getenv('CHATTERBOX_ENDPOINT')
        }
        
        if model not in endpoints or not endpoints[model]:
            return {
                "error": f"Model '{model}' not configured",
                "available_models": list(endpoints.keys()),
                "configured_endpoints": {k: v for k, v in endpoints.items() if v}
            }
        
        model_endpoint = endpoints[model]
        
        print(f"Routing to {model}: {model_endpoint}")
        
        # Make request to model
        headers = {"Content-Type": "application/json"}
        if os.getenv('RUNPOD_API_KEY'):
            headers["Authorization"] = f"Bearer {os.getenv('RUNPOD_API_KEY')}"
        
        try:
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
                return {
                    "error": f"Model service error: {response.status_code}",
                    "details": response.text[:200]
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Failed to connect to {model} service",
                "details": str(e)
            }
        
    except Exception as e:
        print(f"Gateway error: {str(e)}")
        return {
            "error": f"Gateway internal error: {str(e)}"
        }

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting Gateway on RunPod...")
        print(f"Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting Gateway locally...")
        # Local FastAPI server for testing
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        @app.post("/test")
        def test_endpoint(data: dict):
            return handler({"input": data})
        
        uvicorn.run(app, host="0.0.0.0", port=8000)
