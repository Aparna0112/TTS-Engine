#!/usr/bin/env python3
"""
Chatterbox TTS Handler with JWT Authentication
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

class ChatterboxHandler:
    def __init__(self):
        print("Initializing Chatterbox TTS handler")
        self.model_name = "chatterbox"
        
        # JWT Configuration - Updated to match your gateway
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')  # Changed from JWT_SECRET
        self.jwt_required = os.getenv('REQUIRE_JWT', 'true').lower() == 'true'  # Default to true
        
        logger.info(f"🔐 Chatterbox JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 Chatterbox JWT - Required: {self.jwt_required}")
    
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
    
    def generate_audio(self, text: str, voice: str = "default", speed: float = 1.0) -> Dict:
        """Generate audio using Chatterbox TTS (using gTTS with different settings)"""
        temp_file_path = None
        try:
            logger.info(f"Chatterbox generating audio for: '{text[:50]}...' with voice: {voice}, speed: {speed}")
            
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
            
            logger.info(f"Chatterbox using gTTS with slow={slow_speech}, tld={tld}")
            
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
            
            # Save temporary file (cleaned up later)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                temp_file_path = tmp_file.name
            
            logger.info(f"Chatterbox audio generated: {word_count} words, {duration:.2f}s duration")
            
            result = {
                "audio_url": temp_file_path,
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
            
            return result
            
        except Exception as e:
            # Clean up temp file on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            error_msg = f"Chatterbox TTS generation failed: {str(e)}"
            logger.error(f"ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
chatterbox_handler = ChatterboxHandler()

def handler(event):
    """
    RunPod handler for Chatterbox TTS with JWT authentication
    Compatible with your gateway's JWT format
    """
    temp_files = []
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"💬 Chatterbox processing job: {job_id}")
        logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # JWT Authentication (if enabled)
        if chatterbox_handler.jwt_required:
            logger.info(f"🔐 JWT authentication required for Chatterbox")
            
            # Check both possible JWT parameter names for compatibility
            auth_token = input_data.get("jwt_token") or input_data.get("auth_token")
            
            if not auth_token:
                logger.warning(f"🚫 No JWT token provided for job {job_id}")
                return {
                    "error": "Authentication required - JWT token missing",
                    "model": "chatterbox",
                    "job_id": job_id,
                    "success": False
                }
            
            jwt_result = chatterbox_handler.verify_jwt_token(auth_token)
            if not jwt_result["valid"]:
                logger.warning(f"🚫 Invalid JWT token for job {job_id}: {jwt_result.get('error')}")
                return {
                    "error": f"JWT validation failed: {jwt_result.get('error')}",
                    "model": "chatterbox",
                    "job_id": job_id,
                    "success": False
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
                "job_id": job_id,
                "success": False
            }
        
        # Extract parameters with defaults
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        
        logger.info(f"📝 Chatterbox processing: {len(text)} chars, voice: {voice}, speed: {speed}")
        
        # Generate audio using the handler
        result = chatterbox_handler.generate_audio(text, voice, speed)
        
        # Store temp file path for cleanup
        if result.get("audio_url"):
            temp_files.append(result["audio_url"])
        
        # Add metadata
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "chatterbox",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time": 0.0  # For compatibility
        })
        
        logger.info(f"✅ Chatterbox job {job_id} completed successfully")
        
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
        
        error_msg = f"Chatterbox handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "chatterbox",
            "job_id": job_id,
            "success": False,
            "timestamp": datetime.utcnow().isoformat()
        }

def test_handler():
    """Test the Chatterbox handler locally"""
    print("🧪 Testing Chatterbox Handler...")
    
    # Test without JWT (if JWT is disabled)
    if not chatterbox_handler.jwt_required:
        print("\n=== Test WITHOUT JWT ===")
        result = handler({
            "id": "test_no_jwt",
            "input": {
                "text": "Hello from Chatterbox without JWT",
                "voice": "casual",
                "speed": 1.0
            }
        })
        print(f"Result: {result.get('success', False)}")
        if result.get('audio_base64'):
            print(f"Audio generated: {len(result['audio_base64'])} base64 chars")
    
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
                "jwt_token": test_token,  # Using jwt_token to match gateway
                "text": "Hello from Chatterbox with JWT",
                "voice": "formal",
                "speed": 1.3
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
        logger.info("🚀 Starting Chatterbox TTS Handler")
        logger.info(f"🔧 JWT Authentication: {'Enabled' if chatterbox_handler.jwt_required else 'Disabled'}")
        
        # Start RunPod serverless worker
        runpod.serverless.start({
            "handler": handler
        })
