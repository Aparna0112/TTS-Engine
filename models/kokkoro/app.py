import os
import asyncio
import json

def handler(event):
    """Minimal RunPod handler for testing"""
    try:
        input_data = event.get('input', {})
        text = input_data.get('text', 'Hello World')
        
        # Simple response without actual TTS
        return {
            "output": {
                "message": f"Kokkoro received: {text}",
                "audio_url": "/tmp/placeholder.wav",
                "model_used": "kokkoro",
                "duration": 2.5,
                "status": "success"
            }
        }
    except Exception as e:
        return {"error": f"Handler error: {str(e)}"}

if __name__ == "__main__":
    # Check if running in RunPod environment
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        try:
            import runpod
            print("Starting RunPod serverless handler...")
            runpod.serverless.start({"handler": handler})
        except Exception as e:
            print(f"RunPod start error: {e}")
            exit(1)
    else:
        # Local development fallback
        print("Running in local mode")
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        @app.post("/test")
        def test():
            return {"message": "Local test working"}
        
        uvicorn.run(app, host="0.0.0.0", port=8001)
