import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from handler import ChatterboxHandler

app = FastAPI(
    title="Real Chatterbox TTS Service", 
    version="2.0.0",  # Updated version
    description="State-of-the-art Text-to-Speech using Resemble AI's Chatterbox with emotion control and voice cloning"
)

# Initialize handler
handler_instance = ChatterboxHandler()

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize", max_length=10000)
    voice: str = Field(default="default", description="Voice preset to use")
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="Speech speed multiplier")
    # New optional parameters for real Chatterbox
    exaggeration: Optional[float] = Field(None, ge=0.0, le=2.0, description="Emotion intensity control")
    cfg_weight: Optional[float] = Field(None, ge=0.1, le=1.0, description="CFG weight for fine-tuning")
    audio_prompt_path: Optional[str] = Field(None, description="Path to reference audio for voice cloning")

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
    # New fields for real Chatterbox
    voice_description: Optional[str] = None
    exaggeration_used: Optional[float] = None
    cfg_weight_used: Optional[float] = None
    is_real_chatterbox: bool = True
    has_watermark: bool = True

@app.get("/")
def root():
    return {
        "message": "Real Chatterbox TTS Model", 
        "status": "ready",
        "model": "chatterbox",
        "version": "2.0.0",  # Updated
        "engine": "Resemble AI Chatterbox",  # Updated
        "supported_voices": list(handler_instance.voice_presets.keys()),  # Dynamic from handler
        "supported_languages": ["en"],
        "features": [
            "neural_synthesis",
            "emotion_control", 
            "voice_cloning",
            "watermarking",
            "variable_speed",
            "gpu_accelerated"
        ]
    }

@app.get("/health")
def health_check():
    """Enhanced health check with model status"""
    try:
        model_loaded = handler_instance.model is not None
        device_status = handler_instance.device
        
        return {
            "status": "healthy", 
            "model": "chatterbox",
            "version": "2.0.0",
            "engine": "resemble-ai-real",
            "model_loaded": model_loaded,
            "device": device_status,
            "gpu_available": device_status == "cuda",
            "uptime": "running"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "model": "chatterbox", 
            "error": str(e)
        }

@app.get("/info")
def model_info():
    """Updated model info for real Chatterbox"""
    return {
        "model_name": "Real Chatterbox TTS",
        "model_type": "Neural Text-to-Speech",
        "engine": "Resemble AI Chatterbox",  # Updated from gTTS
        "supported_voices": list(handler_instance.voice_presets.keys()),
        "voice_descriptions": {
            voice: preset["description"] 
            for voice, preset in handler_instance.voice_presets.items()
        },
        "supported_languages": ["en"],
        "output_format": "wav",  # Changed from mp3 to wav
        "features": [
            "Neural synthesis with 500M parameters",
            "Emotion exaggeration control (0.0-1.0+)",
            "Zero-shot voice cloning",
            "Built-in watermarking (Perth)",
            "Variable speed with quality preservation",
            "CFG weight fine-tuning",
            "GPU acceleration",
            "Base64 audio output"
        ],
        "new_parameters": {
            "exaggeration": "Controls emotional intensity (0.0 = monotone, 1.0+ = expressive)",
            "cfg_weight": "Controls adherence vs naturalness (0.1-1.0)",
            "audio_prompt_path": "Reference audio file path for voice cloning"
        }
    }

@app.get("/voices")
def list_voices():
    """New endpoint to list available voices with descriptions"""
    return {
        "voices": handler_instance.voice_presets,
        "total_count": len(handler_instance.voice_presets),
        "voice_names": list(handler_instance.voice_presets.keys())
    }

@app.post("/synthesize", response_model=TTSResponse)
def synthesize(request: TTSRequest):
    """Generate speech from text using Real Chatterbox TTS"""
    try:
        print(f"Real Chatterbox received: text='{request.text[:50]}...', voice={request.voice}, speed={request.speed}")
        if request.exaggeration is not None:
            print(f"  Custom exaggeration: {request.exaggeration}")
        if request.cfg_weight is not None:
            print(f"  Custom cfg_weight: {request.cfg_weight}")
        if request.audio_prompt_path:
            print(f"  Voice cloning with: {request.audio_prompt_path}")
        
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(request.text) > 10000:  # Increased limit for real Chatterbox
            raise HTTPException(status_code=400, detail="Text too long (max 10,000 characters)")
        
        if request.voice not in handler_instance.voice_presets:
            available_voices = list(handler_instance.voice_presets.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid voice '{request.voice}'. Available: {available_voices}"
            )
        
        # Generate audio with new parameters
        result = handler_instance.generate_audio(
            text=request.text.strip(),
            voice=request.voice,
            speed=request.speed,
            exaggeration=request.exaggeration,
            cfg_weight=request.cfg_weight,
            audio_prompt_path=request.audio_prompt_path
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
            status="success",
            # New fields
            voice_description=result.get("voice_description"),
            exaggeration_used=result.get("exaggeration_used"),
            cfg_weight_used=result.get("cfg_weight_used"),
            is_real_chatterbox=result.get("is_real_chatterbox", True),
            has_watermark=result.get("has_watermark", True)
        )
        
        print(f"Real Chatterbox synthesis completed: {result['duration']}s audio generated")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Real Chatterbox synthesis error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/test")
def test_synthesis():
    """Quick test endpoint with enhanced output"""
    try:
        result = handler_instance.generate_audio(
            text="This is a test of the Real Chatterbox TTS system with neural synthesis.",
            voice="default",
            speed=1.0
        )
        return {
            "status": "success",
            "message": "Real Chatterbox test synthesis completed",
            "duration": result["duration"],
            "audio_size": result["audio_size_bytes"],
            "model": "chatterbox",
            "model_version": result.get("model_version", "resemble-ai-real-1.0"),
            "device_used": result.get("device_used"),
            "is_real_chatterbox": result.get("is_real_chatterbox", True),
            "has_watermark": result.get("has_watermark", True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@app.post("/test-voice/{voice_name}")
def test_specific_voice(voice_name: str):
    """Test specific voice preset"""
    try:
        if voice_name not in handler_instance.voice_presets:
            available_voices = list(handler_instance.voice_presets.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice '{voice_name}'. Available: {available_voices}"
            )
        
        preset = handler_instance.voice_presets[voice_name]
        test_text = f"Testing the {voice_name} voice preset. {preset['description']}"
        
        result = handler_instance.generate_audio(
            text=test_text,
            voice=voice_name,
            speed=1.0
        )
        
        return {
            "status": "success",
            "message": f"Voice test completed for: {voice_name}",
            "voice_description": preset["description"],
            "duration": result["duration"],
            "audio_size": result["audio_size_bytes"],
            "exaggeration_used": result.get("exaggeration_used"),
            "cfg_weight_used": result.get("cfg_weight_used")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice test failed: {str(e)}")

# RunPod serverless handler - Updated for real Chatterbox
def handler(event):
    """RunPod serverless handler for Real Chatterbox TTS"""
    try:
        print(f"Real Chatterbox RunPod handler received event: {event}")
        
        # Extract input data with multiple fallback methods
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        print(f"Real Chatterbox input data: {input_data}")
        
        # Try multiple ways to get text
        text = input_data.get('text') or input_data.get('prompt') or input_data.get('message')
        
        if not text or not str(text).strip():
            return {
                "error": "Text field is required for Real Chatterbox TTS",
                "received_input": input_data,
                "model": "chatterbox",
                "available_voices": list(handler_instance.voice_presets.keys())
            }
        
        # Extract parameters (including new ones)
        voice = input_data.get('voice', 'default')
        speed = input_data.get('speed', 1.0)
        exaggeration = input_data.get('exaggeration')
        cfg_weight = input_data.get('cfg_weight')
        audio_prompt_path = input_data.get('audio_prompt_path')
        
        try:
            speed = float(speed)
        except (ValueError, TypeError):
            speed = 1.0
        
        # Validate exaggeration if provided
        if exaggeration is not None:
            try:
                exaggeration = float(exaggeration)
                if not (0.0 <= exaggeration <= 2.0):
                    exaggeration = None
            except (ValueError, TypeError):
                exaggeration = None
        
        # Validate cfg_weight if provided
        if cfg_weight is not None:
            try:
                cfg_weight = float(cfg_weight)
                if not (0.1 <= cfg_weight <= 1.0):
                    cfg_weight = None
            except (ValueError, TypeError):
                cfg_weight = None
        
        print(f"Real Chatterbox processing: text='{str(text)[:50]}...', voice={voice}, speed={speed}")
        if exaggeration is not None:
            print(f"  Custom exaggeration: {exaggeration}")
        if cfg_weight is not None:
            print(f"  Custom cfg_weight: {cfg_weight}")
        if audio_prompt_path:
            print(f"  Voice cloning with: {audio_prompt_path}")
        
        # Generate audio with enhanced parameters
        result = handler_instance.generate_audio(
            text=str(text).strip(),
            voice=str(voice),
            speed=speed,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            audio_prompt_path=audio_prompt_path
        )
        
        print(f"Real Chatterbox generation successful: {result['duration']}s audio")
        
        # Return enhanced result
        return {
            "output": {
                "audio_url": result["audio_url"],
                "audio_base64": result["audio_base64"],
                "audio_data_url": result["audio_data_url"],
                "audio_format": result["audio_format"],
                "duration": result["duration"],
                "model_used": "chatterbox",
                "model_version": result.get("model_version", "resemble-ai-real-1.0"),
                "voice_used": result["voice_used"],
                "voice_description": result.get("voice_description"),
                "speed_used": result["speed_used"],
                "text_length": result["text_length"],
                "word_count": result["word_count"],
                "device_used": result.get("device_used"),
                "exaggeration_used": result.get("exaggeration_used"),
                "cfg_weight_used": result.get("cfg_weight_used"),
                "is_real_chatterbox": result.get("is_real_chatterbox", True),
                "has_watermark": result.get("has_watermark", True),
                "audio_prompt_used": result.get("audio_prompt_used", False),
                "status": "success"
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Real Chatterbox handler error: {error_msg}")
        return {
            "error": error_msg,
            "model": "chatterbox",
            "model_version": "resemble-ai-real-1.0",
            "input_received": event.get('input', {}),
            "available_voices": list(handler_instance.voice_presets.keys()) if hasattr(handler_instance, 'voice_presets') else []
        }

# Application startup
if __name__ == "__main__":
    print("🚀 Starting Real Chatterbox TTS Service...")
    print(f"📱 Model: Resemble AI Chatterbox")
    print(f"🎭 Available voices: {list(handler_instance.voice_presets.keys())}")
    print(f"🎯 Device: {handler_instance.device}")
    
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("🌐 Starting Real Chatterbox TTS on RunPod serverless...")
        print(f"🔗 RunPod Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("🏠 Starting Real Chatterbox TTS locally...")
        print("📋 Available endpoints:")
        print("  GET  / - Service info")
        print("  GET  /health - Health check")
        print("  GET  /info - Model details")
        print("  GET  /voices - List voices")
        print("  POST /synthesize - Generate speech")
        print("  POST /test - Quick test")
        print("  POST /test-voice/{voice_name} - Test specific voice")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8002,  # Keep your existing port
            log_level="info"
        )
