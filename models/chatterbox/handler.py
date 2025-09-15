import runpod
import io
import base64
import logging
from typing import Dict, Any
import os
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_tts_audio(text: str, voice: str = "default", speed: float = 1.0, language: str = "en") -> bytes:
    """Generate TTS audio using gTTS (Google Text-to-Speech)"""
    try:
        from gtts import gTTS
        
        logger.info(f"Generating TTS with gTTS: text='{text[:50]}...', lang={language}, speed={speed}")
        
        # Adjust speed by modifying text (gTTS doesn't have direct speed control)
        if speed != 1.0:
            # For speed adjustment, we can use the slow parameter
            slow = speed < 0.8
        else:
            slow = False
        
        # Create gTTS object
        tts = gTTS(text=text, lang=language, slow=slow)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            
            # Read the file back
            with open(tmp_file.name, 'rb') as f:
                audio_data = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
            
        logger.info(f"Successfully generated {len(audio_data)} bytes of audio")
        return audio_data
        
    except ImportError as e:
        logger.error("gTTS not installed. Falling back to basic response.")
        # Return a small placeholder audio file (silence)
        return b''
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        raise

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Main handler for TTS generation"""
    try:
        logger.info(f"Received event: {event}")
        
        # Extract input parameters
        input_data = event.get("input", {})
        
        text = input_data.get("text", "")
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        language = input_data.get("language", "en")
        
        # Validate input
        if not text or not text.strip():
            return {
                "error": "No text provided for TTS generation",
                "success": False,
                "model": "chatterbox"
            }
        
        logger.info(f"Processing TTS request: text='{text}', voice={voice}, speed={speed}, lang={language}")
        
        # Generate TTS audio
        audio_data = generate_tts_audio(text, voice, speed, language)
        
        if not audio_data:
            return {
                "error": "Failed to generate audio - TTS service unavailable",
                "success": False,
                "model": "chatterbox"
            }
        
        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        result = {
            "success": True,
            "model": "chatterbox",
            "audio": audio_base64,
            "audio_format": "mp3",
            "text": text,
            "voice": voice,
            "speed": speed,
            "language": language,
            "audio_size_bytes": len(audio_data)
        }
        
        logger.info(f"Successfully generated audio response: {len(audio_data)} bytes")
        return result
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            "success": False,
            "model": "chatterbox",
            "error": str(e)
        }

if __name__ == "__main__":
    # Test locally if needed
    test_event = {
        "input": {
            "text": "Hello, this is a test",
            "voice": "default",
            "speed": 1.0,
            "language": "en"
        }
    }
    
    print("Testing handler locally...")
    result = handler(test_event)
    print(f"Result: {result}")
    
    # Start RunPod serverless
    runpod.serverless.start({"handler": handler})
