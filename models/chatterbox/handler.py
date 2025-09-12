#!/usr/bin/env python3
"""
Real Chatterbox TTS Handler with MP3 Output - NO Google TTS
Direct playable files for RunPod
File: models/chatterbox/handler.py
"""

import runpod
import tempfile
import os
import jwt
import logging
import subprocess
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
        print("Initializing Real Chatterbox TTS handler with MP3 output")
        self.model_name = "chatterbox"
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.jwt_required = os.getenv('REQUIRE_JWT', 'true').lower() == 'true'
        
        # Model initialization
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Real Chatterbox voice presets with detailed configurations
        self.voice_presets = {
            "chatterbox_default": {
                "exaggeration": 0.5, 
                "cfg_weight": 0.5, 
                "description": "Balanced natural Chatterbox voice",
                "style": "neutral"
            },
            "chatterbox_casual": {
                "exaggeration": 0.3, 
                "cfg_weight": 0.4, 
                "description": "Relaxed conversational Chatterbox",
                "style": "casual"
            },
            "chatterbox_professional": {
                "exaggeration": 0.4, 
                "cfg_weight": 0.7, 
                "description": "Clear professional Chatterbox voice",
                "style": "formal"
            },
            "chatterbox_energetic": {
                "exaggeration": 0.8, 
                "cfg_weight": 0.3, 
                "description": "High energy expressive Chatterbox",
                "style": "energetic"
            },
            "chatterbox_calm": {
                "exaggeration": 0.2, 
                "cfg_weight": 0.6, 
                "description": "Calm and steady Chatterbox voice",
                "style": "calm"
            },
            "chatterbox_dramatic": {
                "exaggeration": 1.0, 
                "cfg_weight": 0.3, 
                "description": "Highly expressive dramatic Chatterbox",
                "style": "theatrical"
            },
            "chatterbox_narrator": {
                "exaggeration": 0.4, 
                "cfg_weight": 0.6, 
                "description": "Story narration Chatterbox voice",
                "style": "narrator"
            },
            "chatterbox_friendly": {
                "exaggeration": 0.6, 
                "cfg_weight": 0.4, 
                "description": "Warm and friendly Chatterbox voice",
                "style": "friendly"
            }
        }
        
        logger.info(f"🔐 JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 JWT - Required: {self.jwt_required}")
        logger.info(f"🎯 Device: {self.device}")
        logger.info(f"🎭 Available Chatterbox voices: {list(self.voice_presets.keys())}")
        
        if not CHATTERBOX_AVAILABLE:
            logger.error("❌ Real Chatterbox TTS not available")
    
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
        """Verify JWT token"""
        if not self.jwt_secret:
            return {"valid": False, "error": "JWT secret not configured"}
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            logger.info(f"✅ JWT valid for user: {payload.get('user_id', 'unknown')}")
            return {"valid": True, "user_data": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"JWT error: {str(e)}"}
    
    def convert_to_mp3(self, wav_path: str, bitrate: str = "192k") -> str:
        """Convert WAV to MP3 using FFmpeg with high quality"""
        try:
            mp3_path = wav_path.replace('.wav', '.mp3')
            
            # High-quality MP3 conversion
            cmd = [
                'ffmpeg', '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-b:a', bitrate,           # Bitrate (192k for good quality)
                '-ar', '44100',            # Sample rate  
                '-ac', '1',                # Mono (or '2' for stereo)
                '-y',                      # Overwrite output file
                mp3_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Converted to MP3: {mp3_path} (bitrate: {bitrate})")
                return mp3_path
            else:
                logger.error(f"❌ FFmpeg conversion failed: {result.stderr}")
                return wav_path  # Return original if conversion fails
                
        except Exception as e:
            logger.error(f"❌ MP3 conversion error: {str(e)}")
            return wav_path  # Return original if conversion fails
    
    def generate_audio(self, 
                      text: str, 
                      voice: str = "chatterbox_default", 
                      speed: float = 1.0,
                      output_format: str = "mp3",
                      audio_prompt_path: Optional[str] = None,
                      exaggeration: Optional[float] = None,
                      cfg_weight: Optional[float] = None) -> Dict:
        """Generate audio using real Chatterbox TTS model with MP3 output"""
        
        # Ensure model is loaded
        self.load_model()
        
        temp_wav_path = None
        temp_mp3_path = None
        
        try:
            logger.info(f"🎤 Chatterbox generating: '{text[:50]}...' | voice: {voice} | speed: {speed} | format: {output_format}")
            
            # Get voice preset parameters
            preset = self.voice_presets.get(voice, self.voice_presets["chatterbox_default"])
            
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
            
            # Save to temporary WAV file first
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_wav_path = tmp_file.name
            
            # Save the audio (ensure proper tensor dimensions)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            ta.save(temp_wav_path, wav, self.model.sr)
            
            # Convert to requested format
            if output_format.lower() == "mp3":
                temp_mp3_path = self.convert_to_mp3(temp_wav_path)
                final_audio_path = temp_mp3_path
                audio_format = "mp3"
                mime_type = "audio/mpeg"
            else:
                final_audio_path = temp_wav_path
                audio_format = "wav"
                mime_type = "audio/wav"
            
            # Calculate duration and get file info
            duration = len(wav.squeeze()) / self.model.sr
            file_size = os.path.getsize(final_audio_path)
            word_count = len(text.split())
            char_count = len(text)
            
            logger.info(f"✅ Chatterbox audio generated: {duration:.2f}s, {file_size} bytes, {audio_format.upper()}")
            
            # Return result optimized for RunPod playback
            result = {
                "audio_url": final_audio_path,  # Direct file path for RunPod access
                "playable_url": final_audio_path,  # Same as audio_url for clarity
                "audio_format": audio_format,
                "mime_type": mime_type,
                "duration": round(duration, 2),
                "sample_rate": self.model.sr,
                "model": "chatterbox",
                "model_version": "resemble-ai-real-1.0",
                "voice_used": voice,
                "voice_description": preset["description"],
                "voice_style": preset["style"],
                "speed_used": speed,
                "exaggeration_used": final_exaggeration,
                "cfg_weight_used": final_cfg_weight,
                "text_length": char_count,
                "word_count": word_count,
                "audio_size_bytes": file_size,
                "device_used": self.device,
                "has_watermark": True,  # Real Chatterbox includes Perth watermarker
                "is_real_chatterbox": True,
                "audio_prompt_used": audio_prompt_path is not None,
                "output_format": audio_format,
                "bitrate": "192k" if audio_format == "mp3" else None
            }
            
            # Clean up intermediate files (keep final output)
            if temp_wav_path and temp_mp3_path and temp_wav_path != final_audio_path:
                try:
                    os.unlink(temp_wav_path)  # Remove intermediate WAV if MP3 was created
                    logger.info(f"🗑️ Cleaned up intermediate WAV file")
                except:
                    pass
            
            return result
            
        except Exception as e:
            # Clean up temp files on error
            for path in [temp_wav_path, temp_mp3_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass
            
            error_msg = f"Real Chatterbox TTS generation failed: {str(e)}"
            logger.error(f"❌ ERROR: {error_msg}")
            raise Exception(error_msg)

# Global handler instance
chatterbox_handler = ChatterboxHandler()

def handler(event):
    """RunPod handler for Real Chatterbox TTS with MP3 output"""
    temp_files = []
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"🎭 Chatterbox processing job: {job_id}")
        logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # JWT Authentication
        if chatterbox_handler.jwt_required:
            auth_token = input_data.get("jwt_token") or input_data.get("auth_token")
            if not auth_token:
                return {
                    "error": "JWT token required",
                    "model": "chatterbox",
                    "job_id": job_id,
                    "success": False
                }
            
            jwt_result = chatterbox_handler.verify_jwt_token(auth_token)
            if not jwt_result["valid"]:
                return {
                    "error": f"JWT failed: {jwt_result.get('error')}",
                    "model": "chatterbox",
                    "job_id": job_id,
                    "success": False
                }
        
        # Validate input
        text = input_data.get("text")
        if not text:
            return {
                "error": "Missing text parameter",
                "model": "chatterbox",
                "job_id": job_id,
                "success": False,
                "available_voices": list(chatterbox_handler.voice_presets.keys())
            }
        
        # Extract parameters
        voice = input_data.get("voice", "chatterbox_default")
        speed = float(input_data.get("speed", 1.0))
        output_format = input_data.get("format", "mp3")  # Default to MP3
        audio_prompt_path = input_data.get("audio_prompt_path")  # Voice cloning
        exaggeration = input_data.get("exaggeration")  # Custom emotion
        cfg_weight = input_data.get("cfg_weight")  # Custom fine-tuning
        
        # Validate voice
        if voice not in chatterbox_handler.voice_presets:
            available_voices = list(chatterbox_handler.voice_presets.keys())
            return {
                "error": f"Invalid voice '{voice}'. Available: {available_voices}",
                "available_voices": available_voices,
                "model": "chatterbox",
                "job_id": job_id,
                "success": False
            }
        
        logger.info(f"🎤 Processing: voice={voice}, speed={speed}, format={output_format}")
        if exaggeration is not None:
            logger.info(f"🎛️ Custom exaggeration: {exaggeration}")
        if cfg_weight is not None:
            logger.info(f"🎛️ Custom cfg_weight: {cfg_weight}")
        if audio_prompt_path:
            logger.info(f"🎵 Voice cloning: {audio_prompt_path}")
        
        # Generate audio
        result = chatterbox_handler.generate_audio(
            text=text,
            voice=voice,
            speed=speed,
            output_format=output_format,
            audio_prompt_path=audio_prompt_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight
        )
        
        # Store temp file for cleanup (but don't delete immediately for RunPod access)
        if result.get("audio_url"):
            temp_files.append(result["audio_url"])
        
        # Add metadata
        result.update({
            "success": True,
            "job_id": job_id,
            "model": "chatterbox",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Chatterbox job {job_id} completed: {result.get('duration')}s {result.get('output_format').upper()}")
        logger.info(f"📊 File: {result.get('playable_url')} ({result.get('audio_size_bytes')} bytes)")
        
        # Note: Don't clean up files immediately - RunPod needs to access them
        # Files will be cleaned up when container terminates
        
        return result
        
    except Exception as e:
        # Clean up temp files on error only
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
    """Test the Real Chatterbox handler with MP3 output"""
    print("🧪 Testing Real Chatterbox Handler with MP3 output...")
    
    if not CHATTERBOX_AVAILABLE:
        print("❌ Chatterbox TTS not available. Install with: pip install chatterbox-tts")
        return
    
    print(f"🎭 Available voices: {list(chatterbox_handler.voice_presets.keys())}")
    
    # Test different voices and formats
    test_cases = [
        {
            "voice": "chatterbox_default", 
            "text": "Hello! This is the default Chatterbox voice in MP3 format.",
            "format": "mp3"
        },
        {
            "voice": "chatterbox_energetic", 
            "text": "Wow! This is so exciting! High energy Chatterbox voice!",
            "format": "mp3",
            "exaggeration": 0.9
        },
        {
            "voice": "chatterbox_calm", 
            "text": "Take a deep breath. This is the calm Chatterbox voice for relaxation.",
            "format": "wav"
        },
        {
            "voice": "chatterbox_dramatic", 
            "text": "In a world of artificial intelligence, one voice stands supreme!",
            "format": "mp3",
            "exaggeration": 1.0
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n=== Test {i+1}: {test_case['voice']} ({test_case['format'].upper()}) ===")
        
        input_data = {
            "text": test_case["text"],
            "voice": test_case["voice"],
            "speed": 1.0,
            "format": test_case["format"]
        }
        
        if "exaggeration" in test_case:
            input_data["exaggeration"] = test_case["exaggeration"]
        
        result = handler({
            "id": f"test_{i+1}",
            "input": input_data
        })
        
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"Duration: {result.get('duration')}s")
            print(f"Format: {result.get('output_format')}")
            print(f"File: {result.get('playable_url')}")
            print(f"Voice: {result.get('voice_description')}")
            print(f"Style: {result.get('voice_style')}")
            print(f"Size: {result.get('audio_size_bytes')} bytes")
            if result.get('exaggeration_used'):
                print(f"Exaggeration: {result.get('exaggeration_used')}")
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
        logger.info(f"🎵 Output: MP3/WAV files for direct playback")
        logger.info(f"🤖 Real Chatterbox Available: {CHATTERBOX_AVAILABLE}")
        
        # Start RunPod serverless worker
        runpod.serverless.start({
            "handler": handler
        })
