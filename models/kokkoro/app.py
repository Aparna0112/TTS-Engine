import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from handler import KokkoroHandler

app = FastAPI(
    title="Kokkoro TTS Service", 
    version="1.0.0",
    description="High-quality Text-to-Speech using Google TTS"
)

# Initialize handler
handler_instance = KokkoroHandler()

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0
    pitch: float = 1.0

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
        "message": "Kokkoro TTS Model", 
        "status": "ready",
        "model": "kokkoro",
        "version": "1.0.0",
        "supported_voices": ["default", "female", "male", "casual", "formal"],
        "supported_languages": ["en"],
        "features": ["base64_audio", "data_urls", "variable_speed"]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "model": "kokkoro",
        "version": "1.0.0",
        "uptime": "running"
    }

@app.get("/info")
def model_info():
    return {
        "model_name": "Kokkoro TTS",
        "model_type": "Text-to-Speech",
        "engine": "Google TTS (gTTS)",
        "supported_voices": ["default", "female", "male", "casual", "formal"],
        "supported_languages": ["en"],
        "output_format": "mp3",
        "features": [
            "High-quality synthesis",
            "Multiple voice styles",
            "Variable speed control",
            "Base64 audio output",
            "Data URL generation",
            "Immediate playback support"
        ]
    }

@app.post("/synthesize", response_model=TTSResponse)
def synthesize(request: TTSRequest):
    """Generate speech from text using Kokkoro TTS"""
    try:
        print(f"Received synthesis request: text='{request.text[:50]}...', voice={request.voice}, speed={request.speed}")
        
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
            speed=request.speed,
            pitch=request.pitch
        )
        
        response = TTSResponse(
            audio_url=result["audio_url"],
            audio_base64=result["audio_base64"],
            audio_data_url=result["audio_data_url"],
            audio_format=result["audio_format"],
            duration=result["duration"],
            model_used="kokkoro",
            voice_used=result["voice_used"],
            speed_used=result["speed_used"],
            status="success"
        )
        
        print(f"Synthesis completed successfully: {result['duration']}s audio generated")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Synthesis error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/test")
def test_synthesis():
    """Quick test endpoint"""
    try:
        result = handler_instance.generate_audio(
            text="This is a test of the Kokkoro TTS system.",
            voice="default",
            speed=1.0
        )
        return {
            "status": "success",
            "message": "Test synthesis completed",
            "duration": result["duration"],
            "audio_size": result["audio_size_bytes"],
            "model": "kokkoro"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# RunPod serverless handler - FIXED SYNCHRONOUS VERSION
def handler(event):
    """RunPod serverless handler - handles TTS requests"""
    try:
        print(f"RunPod handler received event: {event}")
        
        # Extract input data
        input_data = event.get('input', {})
        
        # Validate required fields
        if not input_data:
            return {"error": "No input data provided"}
        
        text = input_data.get('text')
        if not text:
            return {"error": "Text field is required"}
        
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        pitch = input_data.get('pitch', 1.0)
        
        print(f"Processing TTS request: text='{text[:50]}...', voice={voice}, speed={speed}")
        
        # Generate audio using synchronous handler
        result = handler_instance.generate_audio(
            text=text,
            voice=voice,
            speed=float(speed),
            pitch=float(pitch)
        )
        
        print(f"TTS generation successful: {result['duration']}s audio")
        
        # Return result in RunPod format
        return {
            "output": {
                "audio_url": result["audio_url"],
                "audio_base64": result["audio_base64"],
                "audio_data_url": result["audio_data_url"],
                "audio_format": result["audio_format"],
                "duration": result["duration"],
                "model_used": "kokkoro",
                "voice_used": result["voice_used"],
                "speed_used": result["speed_used"],
                "text_length": result["text_length"],
                "word_count": result["word_count"],
                "status": "success"
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"RunPod handler error: {error_msg}")
        return {"error": error_msg}

# Application startup
if __name__ == "__main__":
    # Check if running in RunPod environment
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting Kokkoro TTS on RunPod serverless...")
        print(f"RunPod Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting Kokkoro TTS locally...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8001,
            log_level="info"
        )
