#!/usr/bin/env python3
"""
Real Chatterbox TTS Handler - Replaces gTTS with actual Chatterbox model
Compatible with your existing TTS-Engine project structure
File: models/chatterbox/handler.py
"""

import runpod
import tempfile
import os
import base64
import io
import jwt
import logging
import torchaudio as ta
import torch
from typing import Dict, Optional
from datetime import datetime, timedelta

# Import the real Chatterbox TTS model
try:
    from chatterbox.tts import ChatterboxTTS
    CHATTERBOX_AVAILABLE = True
except ImportError:
    print("⚠️ Chatterbox TTS not installed. Install with: pip install chatterbox-tts")
    CHATTERBOX_AVAILABLE = False

import librosa
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatterboxHandler:
    def __init__(self):
        print("Initializing Real Chatterbox TTS handler")
        self.model_name = "chatterbox"
        
        # JWT Configuration - matching your existing system
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.jwt_required = os.getenv('REQUIRE_JWT', 'true').lower() == 'true'
        
        # Model initialization
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Voice presets - replacing the old TLD-based system
        self.voice_presets = {
            "default": {
                "exaggeration": 0.5, 
                "cfg_weight": 0.5, 
                "description": "Balanced natural voice"
            },
            "casual": {
                "exaggeration": 0.3, 
                "cfg_weight": 0.4, 
                "description": "Relaxed conversational tone"
            },
            "formal": {
                "exaggeration": 0.4, 
                "cfg_weight": 0.7, 
                "description": "Clear and professional"
            },
            "female": {
                "exaggeration": 0.6, 
                "cfg_weight": 0.5, 
                "description": "Warm feminine voice"
            },
            "male": {
                "exaggeration": 0.4, 
                "cfg_weight": 0.6, 
                "description": "Strong masculine voice"
            },
            "energetic": {
                "exaggeration": 0.8, 
                "cfg_weight": 0.3, 
                "description": "High energy and expressive"
            },
            "calm": {
                "exaggeration": 0.2, 
                "cfg_weight": 0.6, 
                "description": "Calm and steady"
            },
            "dramatic": {
                "exaggeration": 1.0, 
                "cfg_weight": 0.3, 
                "description": "Highly expressive and dramatic"
            }
        }
        
        logger.info(f"🔐 Chatterbox JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 Chatterbox JWT - Required: {self.jwt_required}")
        logger.info(f"🎯 Device: {self.device}")
        logger.info(f"🎭 Available voice presets: {list(self.voice_presets.keys())}")
        
        if not CHATTERBOX_AVAILABLE:
            logger.error("❌ Real Chatterbox TTS not available - falling back to error mode")
    
    def load_model(self):
        """Load the real Chatterbox TTS model"""
        if not CHATTERBOX_AVAILABLE:
            raise Exception("Chatterbox TTS library not installed. Please install with: pip install chatterbox-tts")
            
        if self.model is None:
            try:
                logger.info("🚀 Loading real Chatterbox TTS model...")
                self.model = ChatterboxTTS.from_pretrained(device=self.device)
                logger.info("✅ Real Chatterbox TTS model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load Chatterbox model: {str(e)}")
                raise Exception(f"Model loading failed: {str(e)}")
    
    def verify_jwt_token(self, token: str) -> Dict:
        """Verify JWT token and return user info - compatible with your existing system"""
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
    
    def generate_audio(self, 
                      text: str, 
                      voice: str = "default", 
                      speed: float = 1.0,
                      audio_prompt_path: Optional[str] = None,
                      exaggeration: Optional[float] = None,
                      cfg_weight: Optional[float] = None) -> Dict:
        """Generate audio using real Chatterbox TTS model"""
        
        # Ensure model is loaded
        self.load_model()
        
        temp_file_path = None
        try:
            logger.info(f"🎤 Real Chatterbox generating: '{text[:50]}...' | voice: {voice} | speed: {speed}")
            
            # Get voice preset parameters (maintaining compatibility with your existing voice names)
            preset = self.voice_presets.get(voice, self.voice_presets["default"])
            
            # Use custom parameters or defaults from preset
            final_exaggeration = exaggeration if exaggeration is not None else preset["exaggeration"]
            final_cfg_weight = cfg_weight if cfg_weight is not None else preset["cfg_weight"]
            
            # Adjust parameters based on speed for optimal quality
            if speed != 1.0:
                if speed < 0.8:
                    final_cfg_weight = min(1.0, final_cfg_weight + 0.1)
                elif speed > 1.2:
                    final_cfg_weight = max(0.1, final_cfg_weight - 0.1)
            
            logger.info(f"🎛️ Using exaggeration: {final_exaggeration}, cfg_weight: {final_cfg_weight}")
            
            # Generate audio using real Chatterbox TTS
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                logger.info(f"🎵 Using audio prompt for voice cloning: {audio_prompt_path}")
                wav = self.model.generate(
                    text, 
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=final_exaggeration,
                    cfg_weight=final_cfg_weight
                )
            else:
                wav = self.model.generate(
                    text,
                    exaggeration=final_exaggeration,
                    cfg_weight=final_cfg_weight
                )
            
            # Handle speed adjustment using high-quality time stretching
            if speed != 1.0:
                logger.info(f"⚡ Adjusting speed by factor: {speed}")
                if torch.is_tensor(wav):
                    wav_np = wav.cpu().numpy()
                else:
                    wav_np = wav
                
                # Use librosa for high-quality time stretching
                wav_stretched = librosa.effects.time_stretch(wav_np, rate=speed)
                wav = torch.from_numpy(wav_stretched)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_file_path = tmp_file.name
            
            # Save the audio (ensure proper tensor dimensions)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            ta.save(temp_file_path, wav, self.model.sr)
            
            # Read the generated audio file for base64 encoding
            with open(temp_file_path, 'rb') as f:
                audio_data = f.read()
            
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create data URL (maintaining compatibility with your existing format)
            audio_data_url = f"data:audio/wav;base64,{audio_base64}"
            
            # Calculate duration and metadata
            duration = len(wav.squeeze()) / self.model.sr
            word_count = len(text.split())
            char_count = len(text)
            
            logger.info(f"✅ Real Chatterbox audio generated: {duration:.2f}s duration, {word_count} words")
            
            # Return result in format compatible with your existing system
            result = {
                "audio_url": temp_file_path,
                "audio_base64": audio_base64,
                "audio_data_url": audio_data_url,
                "audio_format": "wav",
                "duration": round(duration, 2),
                "sample_rate": self.model.sr,
                "model": "chatterbox",
                "model_version": "resemble-ai-real-1.0",  # Updated to indicate real model
                "voice_used": voice,
                "voice_description": preset["description"],
                "speed_used": speed,
                "exaggeration_used": final_exaggeration,
                "cfg_weight_used": final_cfg_weight,
                "text_length": char_count,
                "word_count": word_count,
                "audio_size_bytes": len(audio_data),
                "audio_size_base64": len(audio_base64),
                "device_used": self.device,
                "has_watermark": True,  # Real Chatterbox includes Perth watermarker
                "available_voices": list(self.voice_presets.keys()),
                "audio_prompt_used": audio_prompt_path is not None,
                "is_real_chatterbox": True  # Flag to indicate this is the real model
            }
            
            return result
            
        except Exception as e:
            # Clean up temp file on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            error_msg = f"Real Chatterbox TTS generation failed: {str(e)}"
            logger.error(f"❌ ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
chatterbox_handler = ChatterboxHandler()

def handler(event):
    """
    RunPod handler for Real Chatterbox TTS
    Compatible with your existing TTS-Engine system
    """
    temp_files = []
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"🎭 Real Chatterbox processing job: {job_id}")
        logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # JWT Authentication (matching your existing system)
        if chatterbox_handler.jwt_required:
            logger.info(f"🔐 JWT authentication required")
            
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
        
        # Validate required parameters
        text = input_data.get("text")
        if not text:
            return {
                "error": "Missing required parameter: text",
                "model": "chatterbox",
                "job_id": job_id,
                "success": False,
                "available_voices": list(chatterbox_handler.voice_presets.keys())
            }
        
        # Extract parameters (maintaining compatibility with your existing API)
        voice = input_data.get("voice", "default")
        speed = float(input_data.get("speed", 1.0))
        audio_prompt_path = input_data.get("audio_prompt_path")  # New feature: voice cloning
        exaggeration = input_data.get("exaggeration")  # New feature: emotion control
        cfg_weight = input_data.get("cfg_weight")  # New feature: fine-tuning
        
        # Validate voice (maintaining compatibility)
        if voice not in chatterbox_handler.voice_presets:
            available_voices = list(chatterbox_handler.voice_presets.keys())
            return {
                "error": f"Invalid voice '{voice}'. Available voices: {available_voices}",
                "available_voices": available_voices,
                "model": "chatterbox",
                "job_id": job_id,
                "success": False
            }
        
        logger.info(f"🎤 Processing: {len(text)} chars, voice: {voice}, speed: {speed}")
        if exaggeration is not None:
            logger.info(f"🎛️ Custom exaggeration: {exaggeration}")
        if cfg_weight is not None:
            logger.info(f"🎛️ Custom cfg_weight: {cfg_weight}")
        
        # Generate audio using the real Chatterbox handler
        result = chatterbox_handler.generate_audio(
            text=text,
            voice=voice,
            speed=speed,
            audio_prompt_path=audio_prompt_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight
        )
        
        # Store temp file path for cleanup
        if result.get("audio_url"):
            temp_files.append(result["audio_url"])
        
        # Add metadata (maintaining compatibility with your existing system)
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "chatterbox",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Real Chatterbox job {job_id} completed successfully")
        logger.info(f"📊 Duration: {result.get('duration')}s, Size: {result.get('audio_size_bytes')} bytes")
        
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
        
        error_msg = f"Real Chatterbox handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "chatterbox",
            "job_id": job_id,
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "available_voices": list(chatterbox_handler.voice_presets.keys()) if hasattr(chatterbox_handler, 'voice_presets') else []
        }

def test_handler():
    """Test the Real Chatterbox handler locally"""
    print("🧪 Testing Real Chatterbox Handler...")
    
    if not CHATTERBOX_AVAILABLE:
        print("❌ Chatterbox TTS not available. Install with: pip install chatterbox-tts")
        return
    
    # Test available voices
    print(f"🎭 Available voices: {list(chatterbox_handler.voice_presets.keys())}")
    
    # Test different voices with your existing voice names
    test_cases = [
        {"voice": "default", "text": "Hello, this is the real Chatterbox TTS model replacing Google TTS."},
        {"voice": "casual", "text": "Hey there! This sounds much more natural than the old system, right?"},
        {"voice": "formal", "text": "Good day. I am pleased to demonstrate the professional voice preset."},
        {"voice": "energetic", "text": "Wow! This is so much better! The real Chatterbox model is amazing!"}
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n=== Test {i+1}: {test_case['voice']} voice ===")
        
        result = handler({
            "id": f"test_{i+1}",
            "input": {
                "text": test_case["text"],
                "voice": test_case["voice"],
                "speed": 1.0
            }
        })
        
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Duration: {result.get('duration')}s")
            print(f"Voice used: {result.get('voice_used')}")
            print(f"Description: {result.get('voice_description')}")
            print(f"Is real Chatterbox: {result.get('is_real_chatterbox')}")
            print(f"Audio size: {result.get('audio_size_bytes')} bytes")
        else:
            print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_handler()
    else:
        logger.info("🚀 Starting Real Chatterbox TTS Handler")
        logger.info(f"🔧 JWT Authentication: {'Enabled' if chatterbox_handler.jwt_required else 'Disabled'}")
        logger.info(f"🎭 Voice Presets: {len(chatterbox_handler.voice_presets)}")
        logger.info(f"🎯 Device: {chatterbox_handler.device}")
        logger.info(f"🤖 Real Chatterbox Available: {CHATTERBOX_AVAILABLE}")
        
        # Start RunPod serverless worker
        runpod.serverless.start({
            "handler": handler
        })
