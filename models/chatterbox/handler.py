#!/usr/bin/env python3
"""
Chatterbox TTS Handler with JWT Authentication
Based on your existing handler + JWT security
"""

import runpod
import tempfile
import os
import base64
import io
import jwt
import logging
from typing import Dict
from gtts import gTTS
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatterboxHandler:
    def __init__(self):
        print("Initializing Chatterbox TTS handler")
        self.model_name = "chatterbox"
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.jwt_required = os.getenv('REQUIRE_JWT', 'false').lower() == 'true'
        
        logger.info(f"🔐 Chatterbox JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 Chatterbox JWT - Required: {self.jwt_required}")
    
    def verify_jwt_token(self, token: str) -> bool:
        """Verify JWT token"""
        if not self.jwt_secret:
            logger.error("JWT secret not configured but JWT required")
            return False
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            logger.info(f"✅ JWT valid for user: {payload.get('user_id', 'unknown')}")
            return True
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return False
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return False
        except Exception as e:
            logger.error(f"JWT verification error: {str(e)}")
            return False
    
    def generate_audio(self, text: str, voice: str = "default", speed: float = 1.0) -> Dict:
        """Generate audio using Chatterbox TTS (using gTTS with different settings)"""
        try:
            print(f"Chatterbox generating audio for: '{text}' with voice: {voice}, speed: {speed}")
            
            # Chatterbox uses slightly different settings than Kokkoro
            slow_speech = speed < 0.7  # Different threshold than Kokkoro
            
            # Use different TLD for variation from Kokkoro
            tld_map = {
                'default': 'com.au',
                'casual': 'ca', 
                'formal': 'co.uk',
                'female': 'co.in',
                'male': 'com'
            }
            tld = tld_map.get(voice, 'com.au')
            
            print(f"Chatterbox using gTTS with slow={slow_speech}, tld={tld}")
            
            # Generate TTS audio
            tts = gTTS(
                text=text, 
                lang='en', 
                slow=slow_speech,
                tld=tld
            )
            
            # Use BytesIO for in-memory processing
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # Convert to base64
            audio_data = audio_buffer.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create data URL
            audio_data_url = f"data:audio/mp3;base64,{audio_base64}"
            
            # Duration calculation (slightly different from Kokkoro)
            word_count = len(text.split())
            char_count = len(text)
            duration = (word_count * 0.55) / speed  # Chatterbox is slightly faster
            
            # Save temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                audio_path = tmp_file.name
            
            print(f"Chatterbox audio generated: {word_count} words, {duration:.2f}s duration")
            
            return {
                "audio_url": audio_path,
                "audio_base64": audio_base64,
                "audio_data_url": audio_data_url,
                "audio_format": "mp3",
                "duration": round(duration, 2),
                "sample_rate": 22050,
                "model": "chatterbox",
                "model_version": "1.0.0",
                "voice_used": voice,
                "speed_used": speed,
                "text_length": char_count,
                "word_count": word_count,
                "tld_used": tld,
                "slow_speech": slow_speech,
                "audio_size_bytes": len(audio_data),
                "audio_size_base64": len(audio_base64)
            }
            
        except Exception as e:
            error_msg = f"Chatterbox TTS generation failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
chatterbox_handler = ChatterboxHandler()

def handler(event):
    """
    RunPod handler for Chatterbox TTS with optional JWT authentication
    """
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"💬 Chatterbox processing job: {job_id}")
        
        # JWT Authentication (if enabled)
        if chatterbox_handler.jwt_required:
            logger.info(f"🔐 JWT authentication required for Chatterbox")
            
            auth_token = input_data.get("auth_token")
            if not auth_token:
                logger.warning(f"🚫 No JWT token provided for job {job_id}")
                return {
                    "error": "Authentication required - JWT token missing",
                    "model": "chatterbox",
                    "job_id": job_id
                }
            
            if not chatterbox_handler.verify_jwt_token(auth_token):
                logger.warning(f"🚫 Invalid JWT token for job {job_id}")
                return {
                    "error": "Invalid or expired JWT token",
                    "model": "chatterbox",
                    "job_id": job_id
                }
            
            logger.info(f"✅ JWT authentication successful for job {job_id}")
        else:
            logger.info(f"⚠️ JWT authentication disabled for Chatterbox")
        
        # Validate required parameters
        text = input_data.get("text")
        if not text:
            return {
                "error": "Missing required parameter: text",
                "model": "chatterbox",
                "job_id": job_id
            }
        
        # Extract parameters
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        
        logger.info(f"📝 Chatterbox processing: {len(text)} chars, voice: {voice}, speed: {speed}")
        
        # Generate audio using the handler
        result = chatterbox_handler.generate_audio(text, voice, speed)
        
        # Add metadata
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "chatterbox",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Chatterbox job {job_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Chatterbox handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "chatterbox",
            "job_id": job_id,
            "success": False
        }

def test_handler():
    """Test the Chatterbox handler locally"""
    print("🧪 Testing Chatterbox Handler...")
    
    # Test without JWT
    print("\n=== Test WITHOUT JWT ===")
    result = handler({
        "id": "test_no_jwt",
        "input": {
            "text": "Hello from Chatterbox without JWT",
            "voice": "casual",
            "speed": 1.0
        }
    })
    print(f"Result: {result}")
    
    # Test with JWT (if enabled)
    if chatterbox_handler.jwt_required and chatterbox_handler.jwt_secret:
        print("\n=== Test WITH JWT ===")
        
        # Generate test token
        test_token = jwt.encode({
            "user_id": "test_user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, chatterbox_handler.jwt_secret, algorithm="HS256")
        
        result = handler({
            "id": "test_with_jwt",
            "input": {
                "auth_token": test_token,
                "text": "Hello from Chatterbox with JWT",
                "voice": "formal",
                "speed": 1.3
            }
        })
        print(f"Result: {result}")

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_handler()
    else:
        logger.info("🚀 Starting Chatterbox TTS Handler")
        logger.info(f"🔧 JWT Authentication: {'Enabled' if chatterbox_handler.jwt_required else 'Disabled'}")
        
        # Start RunPod serverless worker
        runpod.serverless.start({
            "handler": handler
        })
