#!/usr/bin/env python3
"""
Kokkoro TTS Handler with JWT Authentication
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

class KokkoroHandler:
    def __init__(self):
        print("Initializing Kokkoro TTS handler with Google TTS")
        self.model_name = "kokkoro"
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.jwt_required = os.getenv('REQUIRE_JWT', 'false').lower() == 'true'
        
        logger.info(f"🔐 Kokkoro JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 Kokkoro JWT - Required: {self.jwt_required}")
    
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
    
    def generate_audio(self, text: str, voice: str = "default", 
                      speed: float = 1.0, pitch: float = 1.0) -> Dict:
        """Generate audio using Google TTS (gTTS) - SYNCHRONOUS VERSION"""
        try:
            print(f"Generating audio for text: '{text}' with voice: {voice}, speed: {speed}")
            
            # Map speed to gTTS slow parameter
            slow_speech = speed < 0.8
            
            # Map voice to different TLD for variation
            tld_map = {
                'default': 'com',
                'female': 'co.uk',
                'male': 'com.au',
                'casual': 'ca',
                'formal': 'co.in'
            }
            tld = tld_map.get(voice, 'com')
            
            print(f"Using gTTS with slow={slow_speech}, tld={tld}")
            
            # Generate TTS audio
            tts = gTTS(
                text=text, 
                lang='en', 
                slow=slow_speech,
                tld=tld
            )
            
            # Use BytesIO for in-memory audio processing
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # Convert to base64 for easy transfer
            audio_data = audio_buffer.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create data URL for immediate playback
            audio_data_url = f"data:audio/mp3;base64,{audio_base64}"
            
            # Estimate duration (rough calculation)
            word_count = len(text.split())
            char_count = len(text)
            duration = (word_count * 0.6) / speed  # ~0.6 seconds per word adjusted for speed
            
            # Save to temporary file for compatibility
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                audio_path = tmp_file.name
            
            print(f"Audio generated successfully: {word_count} words, {duration:.2f}s duration")
            
            result = {
                "audio_url": audio_path,
                "audio_base64": audio_base64,
                "audio_data_url": audio_data_url,
                "audio_format": "mp3",
                "duration": round(duration, 2),
                "sample_rate": 22050,
                "model": "kokkoro",
                "model_version": "1.0.0",
                "voice_used": voice,
                "speed_used": speed,
                "pitch_used": pitch,
                "text_length": char_count,
                "word_count": word_count,
                "tld_used": tld,
                "slow_speech": slow_speech,
                "audio_size_bytes": len(audio_data),
                "audio_size_base64": len(audio_base64)
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Kokkoro TTS generation failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
kokkoro_handler = KokkoroHandler()

def handler(event):
    """
    RunPod handler for Kokkoro TTS with optional JWT authentication
    """
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"🎵 Kokkoro processing job: {job_id}")
        
        # JWT Authentication (if enabled)
        if kokkoro_handler.jwt_required:
            logger.info(f"🔐 JWT authentication required for Kokkoro")
            
            auth_token = input_data.get("auth_token")
            if not auth_token:
                logger.warning(f"🚫 No JWT token provided for job {job_id}")
                return {
                    "error": "Authentication required - JWT token missing",
                    "model": "kokkoro",
                    "job_id": job_id
                }
            
            if not kokkoro_handler.verify_jwt_token(auth_token):
                logger.warning(f"🚫 Invalid JWT token for job {job_id}")
                return {
                    "error": "Invalid or expired JWT token",
                    "model": "kokkoro", 
                    "job_id": job_id
                }
            
            logger.info(f"✅ JWT authentication successful for job {job_id}")
        else:
            logger.info(f"⚠️ JWT authentication disabled for Kokkoro")
        
        # Validate required parameters
        text = input_data.get("text")
        if not text:
            return {
                "error": "Missing required parameter: text",
                "model": "kokkoro",
                "job_id": job_id
            }
        
        # Extract parameters
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        pitch = float(input_data.get("pitch", 1.0))
        
        logger.info(f"📝 Kokkoro processing: {len(text)} chars, voice: {voice}, speed: {speed}")
        
        # Generate audio using the handler
        result = kokkoro_handler.generate_audio(text, voice, speed, pitch)
        
        # Add metadata
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "kokkoro",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Kokkoro job {job_id} completed successfully")
        return result
        
    except Exception as e:
        error_msg = f"Kokkoro handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "kokkoro",
            "job_id": job_id,
            "success": False
        }

def test_handler():
    """Test the Kokkoro handler locally"""
    print("🧪 Testing Kokkoro Handler...")
    
    # Test without JWT
    print("\n=== Test WITHOUT JWT ===")
    result = handler({
        "id": "test_no_jwt",
        "input": {
            "text": "Hello from Kokkoro without JWT",
            "voice": "default",
            "speed": 1.0
        }
    })
    print(f"Result: {result}")
    
    # Test with JWT (if enabled)
    if kokkoro_handler.jwt_required and kokkoro_handler.jwt_secret:
        print("\n=== Test WITH JWT ===")
        
        # Generate test token
        test_token = jwt.encode({
            "user_id": "test_user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, kokkoro_handler.jwt_secret, algorithm="HS256")
        
        result = handler({
            "id": "test_with_jwt", 
            "input": {
                "auth_token": test_token,
                "text": "Hello from Kokkoro with JWT",
                "voice": "female",
                "speed": 1.2
            }
        })
        print(f"Result: {result}")

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_handler()
    else:
        logger.info("🚀 Starting Kokkoro TTS Handler")
        logger.info(f"🔧 JWT Authentication: {'Enabled' if kokkoro_handler.jwt_required else 'Disabled'}")
        
        # Start RunPod serverless worker
        runpod.serverless.start({
            "handler": handler
        })
