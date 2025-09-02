#!/usr/bin/env python3
"""
Kokkoro TTS Handler with JWT Authentication
Fixed version for RunPod compatibility
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
        
        # JWT Configuration - Updated to match your gateway
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')  # Changed from JWT_SECRET
        self.jwt_required = os.getenv('REQUIRE_JWT', 'true').lower() == 'true'  # Default to true
        
        logger.info(f"🔐 Kokkoro JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 Kokkoro JWT - Required: {self.jwt_required}")
    
    def verify_jwt_token(self, token: str) -> Dict:
        """Verify JWT token and return user info"""
        if not self.jwt_secret:
            logger.error("JWT secret not configured but JWT required")
            return {"valid": False, "error": "JWT secret not configured"}
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            logger.info(f"✅ JWT valid for user: {payload.get('user_id', 'unknown')}")
            return {"valid": True, "user_data": payload}
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
        except Exception as e:
            logger.error(f"JWT verification error: {str(e)}")
            return {"valid": False, "error": f"JWT verification error: {str(e)}"}
    
    def generate_audio(self, text: str, voice: str = "default", 
                      speed: float = 1.0, pitch: float = 1.0) -> Dict:
        """Generate audio using Google TTS (gTTS) - SYNCHRONOUS VERSION"""
        temp_file_path = None
        try:
            logger.info(f"Generating audio for text: '{text[:50]}...' with voice: {voice}, speed: {speed}")
            
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
            
            logger.info(f"Using gTTS with slow={slow_speech}, tld={tld}")
            
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
            
            # Save to temporary file for compatibility (cleaned up later)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                temp_file_path = tmp_file.name
            
            logger.info(f"Audio generated successfully: {word_count} words, {duration:.2f}s duration")
            
            result = {
                "audio_url": temp_file_path,
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
            # Clean up temp file on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            error_msg = f"Kokkoro TTS generation failed: {str(e)}"
            logger.error(f"ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
kokkoro_handler = KokkoroHandler()

def handler(event):
    """
    RunPod handler for Kokkoro TTS with JWT authentication
    Compatible with your gateway's JWT format
    """
    temp_files = []
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"🎵 Kokkoro processing job: {job_id}")
        logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # JWT Authentication (if enabled)
        if kokkoro_handler.jwt_required:
            logger.info(f"🔐 JWT authentication required for Kokkoro")
            
            # Check both possible JWT parameter names for compatibility
            auth_token = input_data.get("jwt_token") or input_data.get("auth_token")
            
            if not auth_token:
                logger.warning(f"🚫 No JWT token provided for job {job_id}")
                return {
                    "error": "Authentication required - JWT token missing",
                    "model": "kokkoro",
                    "job_id": job_id,
                    "success": False
                }
            
            jwt_result = kokkoro_handler.verify_jwt_token(auth_token)
            if not jwt_result["valid"]:
                logger.warning(f"🚫 Invalid JWT token for job {job_id}: {jwt_result.get('error')}")
                return {
                    "error": f"JWT validation failed: {jwt_result.get('error')}",
                    "model": "kokkoro", 
                    "job_id": job_id,
                    "success": False
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
                "job_id": job_id,
                "success": False
            }
        
        # Extract parameters with defaults
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        pitch = float(input_data.get("pitch", 1.0))
        
        logger.info(f"📝 Kokkoro processing: {len(text)} chars, voice: {voice}, speed: {speed}")
        
        # Generate audio using the handler
        result = kokkoro_handler.generate_audio(text, voice, speed, pitch)
        
        # Store temp file path for cleanup
        if result.get("audio_url"):
            temp_files.append(result["audio_url"])
        
        # Add metadata
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "kokkoro",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time": 0.0  # For compatibility
        })
        
        logger.info(f"✅ Kokkoro job {job_id} completed successfully")
        
        # Clean up temp files after successful processing
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.info(f"🗑️ Cleaned up temp file: {temp_file}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Failed to cleanup {temp_file}: {cleanup_error}")
        
        return result
        
    except Exception as e:
        # Clean up temp files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        error_msg = f"Kokkoro handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "kokkoro",
            "job_id": job_id,
            "success": False,
            "timestamp": datetime.utcnow().isoformat()
        }

def test_handler():
    """Test the Kokkoro handler locally"""
    print("🧪 Testing Kokkoro Handler...")
    
    # Test without JWT (if JWT is disabled)
    if not kokkoro_handler.jwt_required:
        print("\n=== Test WITHOUT JWT ===")
        result = handler({
            "id": "test_no_jwt",
            "input": {
                "text": "Hello from Kokkoro without JWT",
                "voice": "default",
                "speed": 1.0
            }
        })
        print(f"Result: {result.get('success', False)}")
        if result.get('audio_base64'):
            print(f"Audio generated: {len(result['audio_base64'])} base64 chars")
    
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
                "jwt_token": test_token,  # Using jwt_token to match gateway
                "text": "Hello from Kokkoro with JWT",
                "voice": "female",
                "speed": 1.2
            }
        })
        print(f"Result: {result.get('success', False)}")
        if result.get('audio_base64'):
            print(f"Audio generated: {len(result['audio_base64'])} base64 chars")

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
