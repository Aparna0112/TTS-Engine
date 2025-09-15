import runpod
import base64
import logging
import subprocess
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event):
    try:
        logger.info(f"CHATTERBOX TTS - Received event: {event}")
        
        # Extract input
        input_data = event.get("input", {})
        text = input_data.get("text", "")
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        
        if not text:
            return {"success": False, "error": "No text provided", "model": "chatterbox"}
        
        logger.info(f"TTS Request: '{text}' voice={voice} speed={speed}")
        
        # Generate audio using espeak
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                temp_path = tmp_file.name
            
            # Run espeak command
            cmd = ["espeak", "-w", temp_path, text]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"espeak failed: {result.stderr}")
                return {"success": False, "error": "TTS generation failed", "model": "chatterbox"}
            
            # Read audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(temp_path)
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            logger.info(f"SUCCESS: Generated {len(audio_data)} bytes of audio")
            
            return {
                "success": True,
                "model": "chatterbox", 
                "audio": audio_base64,
                "audio_format": "wav",
                "text": text,
                "voice": voice,
                "speed": speed,
                "audio_size_bytes": len(audio_data)
            }
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return {"success": False, "error": str(e), "model": "chatterbox"}
            
    except Exception as e:
        logger.error(f"Handler Error: {e}")
        return {"success": False, "error": str(e), "model": "chatterbox"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
