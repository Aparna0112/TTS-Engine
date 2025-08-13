import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from handler import ChatterboxHandler

app = FastAPI(
    title="Chatterbox TTS Service", 
    version="1.0.0",
    description="Fast and efficient Text-to-Speech using Google TTS"
)

# Initialize handler
handler_instance = ChatterboxHandler()

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0

class TTSResponse(BaseModel):
    audio_url: str
    audio_base64: str
    audio_data_url: str
    audio_format: str
    duration: float
    model_used: str
    voice_used: str
    speed_used: float
    status: str

@app.get("/")
def root():
    return {
        "message": "Chatterbox TTS Model", 
        "status": "ready",
        "model": "chatterbox",
        "version": "1.0.0",
        "supported_voices": ["default", "casual", "formal", "female", "male"],
        "supported_languages": ["en"],
        "features": ["fast_synthesis", "lightweight", "variable_speed"]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "model": "chatterbox",
        "version": "1.0.0",
        "uptime": "running"
    }

@app.get("/info")
def model_info():
    return {
        "model_name": "Chatterbox TTS",
        "model_type": "Text-to-Speech",
        "engine": "Google TTS (gTTS) - Fast Variant",
        "supported_voices": ["default", "casual", "formal", "female", "male"],
        "supported_languages": ["en"],
        "output_format": "mp3",
        "features": [
            "Fast synthesis",
            "Lightweight processing",
            "Multiple voice styles",
            "Variable speed control",
            "Base64 audio output"
        ]
    }

@app.post("/synthesize", response_model=TTSResponse)
def synthesize(request: TTSRequest):
    """Generate speech from text using Chatterbox TTS"""
    try:
        print(f"Chatterbox received: text='{request.text[:50]}...', voice={request.voice}, speed={request.speed}")
        
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(request.text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        if not 0.1 <= request.speed <= 3.0:
            raise HTTPException(status_code=400, detail="Speed must be between 0.1 and 3.0")
        
        # Generate audio
        result = handler_instance.generate_audio(
            text=request.text.strip(),
            voice=request.voice,
            speed=request.speed
        )
        
        response = TTSResponse(
            audio_url=result["audio_url"],
            audio_base64=result["audio_base64"],
            audio_data_url=result["audio_data_url"],
            audio_format=result["audio_format"],
            duration=result["duration"],
            model_used="chatterbox",
            voice_used=result["voice_used"],
            speed_used=result["speed_used"],
            status="success"
        )
        
        print(f"Chatterbox synthesis completed: {result['duration']}s audio generated")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Chatterbox synthesis error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/test")
def test_synthesis():
    """Quick test endpoint"""
    try:
        result = handler_instance.generate_audio(
            text="This is a test of the Chatterbox TTS system.",
            voice="default",
            speed=1.0
        )
        return {
            "status": "success",
            "message": "Chatterbox test synthesis completed",
            "duration": result["duration"],
            "audio_size": result["audio_size_bytes"],
            "model": "chatterbox"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# RunPod serverless handler - FIXED SYNCHRONOUS VERSION
def handler(event):
    """RunPod serverless handler for Chatterbox TTS"""
    try:
        print(f"Chatterbox RunPod handler received event: {event}")
        
        # Extract input data with multiple fallback methods
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        print(f"Chatterbox input data: {input_data}")
        
        # Try multiple ways to get text
        text = input_data.get('text') or input_data.get('prompt') or input_data.get('message')
        
        if not text or not str(text).strip():
            return {
                "error": "Text field is required for Chatterbox TTS",
                "received_input": input_data,
                "model": "chatterbox"
            }
        
        # Extract parameters
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        
        try:
            speed = float(speed)
        except (ValueError, TypeError):
            speed = 1.0
        
        print(f"Chatterbox processing: text='{str(text)[:50]}...', voice={voice}, speed={speed}")
        
        # Generate audio
        result = handler_instance.generate_audio(
            text=str(text).strip(),
            voice=str(voice),
            speed=speed
        )
        
        print(f"Chatterbox generation successful: {result['duration']}s audio")
        
        # Return result
        return {
            "output": {
                "audio_url": result["audio_url"],
                "audio_base64": result["audio_base64"],
                "audio_data_url": result["audio_data_url"],
                "audio_format": result["audio_format"],
                "duration": result["duration"],
                "model_used": "chatterbox",
                "voice_used": result["voice_used"],
                "speed_used": result["speed_used"],
                "text_length": result["text_length"],
                "word_count": result["word_count"],
                "status": "success"
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Chatterbox handler error: {error_msg}")
        return {
            "error": error_msg,
            "model": "chatterbox",
            "input_received": event.get('input', {})
        }

# Application startup
if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting Chatterbox TTS on RunPod serverless...")
        print(f"RunPod Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting Chatterbox TTS locally...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8002,
            log_level="info"
        )
