#!/usr/bin/env python3
"""
Chatterbox TTS Serverless Handler - Based on Your Working Repo
Adapted from https://github.com/Aparna0112/Chatterbox-TTS for RunPod Serverless
Uses REAL Chatterbox model with voice cloning - MP3 output
File: models/chatterbox/handler.py
"""

import runpod
import tempfile
import os
import base64
import jwt
import logging
import json
import subprocess
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import uuid

# Import the real Chatterbox TTS model (same as your working repo)
try:
    from chatterbox.src.chatterbox.tts import ChatterboxTTS
    CHATTERBOX_AVAILABLE = True
except ImportError:
    try:
        from chatterbox.tts import ChatterboxTTS
        CHATTERBOX_AVAILABLE = True
    except ImportError:
        print("⚠️ Chatterbox TTS not installed. Install with: pip install chatterbox-tts")
        CHATTERBOX_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatterboxServerlessHandler:
    def __init__(self):
        print("Initializing Real Chatterbox TTS Serverless Handler")
        self.model_name = "chatterbox"
        
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.jwt_required = os.getenv('REQUIRE_JWT', 'true').lower() == 'true'
        
        # Model initialization
        self.model = None
        self.device = "cuda" if os.system("nvidia-smi") == 0 else "cpu"
        
        # Voice storage paths (serverless compatible)
        self.voices_dir = "/tmp/voices"
        self.audio_dir = "/tmp/audio"
        os.makedirs(self.voices_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Built-in voice presets (same as your repo approach)
        self.builtin_voices = {
            "female_default": {
                "name": "Female Default",
                "description": "Professional female voice",
                "type": "builtin",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "male_default": {
                "name": "Male Default", 
                "description": "Professional male voice",
                "type": "builtin",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "narrator": {
                "name": "Narrator",
                "description": "Clear storytelling voice",
                "type": "builtin",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
        
        logger.info(f"🔐 JWT - Secret exists: {self.jwt_secret is not None}")
        logger.info(f"🔐 JWT - Required: {self.jwt_required}")
        logger.info(f"🎯 Device: {self.device}")
        logger.info(f"🎭 Built-in voices: {list(self.builtin_voices.keys())}")
        logger.info(f"📁 Voices dir: {self.voices_dir}")
        
        if not CHATTERBOX_AVAILABLE:
            logger.error("❌ Real Chatterbox TTS not available")
    
    def load_model(self):
        """Load the real Chatterbox TTS model (same as your repo)"""
        if not CHATTERBOX_AVAILABLE:
            raise Exception("Chatterbox TTS not installed. Please install chatterbox-tts package.")
            
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
    
    def convert_to_mp3(self, wav_path: str) -> str:
        """Convert WAV to MP3 using FFmpeg"""
        try:
            mp3_path = wav_path.replace('.wav', '.mp3')
            
            cmd = [
                'ffmpeg', '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-b:a', '192k',
                '-ar', '44100',
                '-y',
                mp3_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Converted to MP3: {mp3_path}")
                return mp3_path
            else:
                logger.error(f"❌ FFmpeg failed: {result.stderr}")
                return wav_path
                
        except Exception as e:
            logger.error(f"❌ MP3 conversion error: {str(e)}")
            return wav_path
    
    def list_voices(self) -> Dict:
        """List all available voices (builtin + custom)"""
        try:
            voices = []
            
            # Add builtin voices
            for voice_id, voice_info in self.builtin_voices.items():
                voices.append({
                    "voice_id": voice_id,
                    **voice_info
                })
            
            # Add custom voices (scan voices directory)
            if os.path.exists(self.voices_dir):
                for voice_file in os.listdir(self.voices_dir):
                    if voice_file.endswith('.json'):
                        voice_id = voice_file.replace('.json', '')
                        try:
                            with open(os.path.join(self.voices_dir, voice_file), 'r') as f:
                                voice_info = json.load(f)
                                voices.append({
                                    "voice_id": voice_id,
                                    **voice_info
                                })
                        except Exception as e:
                            logger.warning(f"Failed to load voice {voice_id}: {e}")
            
            builtin_count = len(self.builtin_voices)
            custom_count = len(voices) - builtin_count
            
            return {
                "success": True,
                "voices": voices,
                "total": len(voices),
                "builtin": builtin_count,
                "custom": custom_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list voices: {str(e)}"
            }
    
    def create_voice_from_audio(self, voice_name: str, voice_description: str, audio_data: bytes) -> Dict:
        """Create a new voice from audio data (same as your repo logic)"""
        try:
            # Generate unique voice ID
            voice_id = f"voice_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # Save audio file temporarily
            audio_path = os.path.join(self.voices_dir, f"{voice_id}.wav")
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Get audio duration (basic validation)
            try:
                import librosa
                y, sr = librosa.load(audio_path)
                duration = len(y) / sr
                
                # Validate duration (5-30 seconds as in your repo)
                if duration < 5 or duration > 30:
                    os.remove(audio_path)
                    return {
                        "success": False,
                        "error": f"Audio duration {duration:.1f}s invalid. Must be 5-30 seconds."
                    }
            except Exception:
                duration = 0  # Fallback if librosa not available
            
            # Create voice metadata
            voice_info = {
                "name": voice_name,
                "description": voice_description,
                "type": "custom",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "audio_duration": round(duration, 2),
                "audio_path": audio_path
            }
            
            # Save voice metadata
            voice_json_path = os.path.join(self.voices_dir, f"{voice_id}.json")
            with open(voice_json_path, 'w') as f:
                json.dump(voice_info, f, indent=2)
            
            logger.info(f"✅ Created voice: {voice_id} ({voice_name})")
            
            return {
                "success": True,
                "voice_id": voice_id,
                "message": f"Voice '{voice_name}' created successfully",
                "voice_info": {
                    "voice_id": voice_id,
                    **voice_info
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Voice creation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Voice creation failed: {str(e)}"
            }
    
    def synthesize_speech(self, text: str, voice_id: str, exaggeration: float = 0.5, temperature: float = 0.8, output_format: str = "mp3") -> Dict:
        """Synthesize speech using voice (same logic as your repo)"""
        
        # Ensure model is loaded
        self.load_model()
        
        temp_wav_path = None
        temp_mp3_path = None
        
        try:
            logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice: {voice_id}")
            
            # Get voice info
            voice_info = None
            audio_prompt_path = None
            
            if voice_id in self.builtin_voices:
                # Use builtin voice
                voice_info = self.builtin_voices[voice_id]
                logger.info(f"Using builtin voice: {voice_info['name']}")
            else:
                # Load custom voice
                voice_json_path = os.path.join(self.voices_dir, f"{voice_id}.json")
                if os.path.exists(voice_json_path):
                    with open(voice_json_path, 'r') as f:
                        voice_info = json.load(f)
                    audio_prompt_path = voice_info.get('audio_path')
                    logger.info(f"Using custom voice: {voice_info['name']} (cloning from {audio_prompt_path})")
                else:
                    return {
                        "success": False,
                        "error": f"Voice '{voice_id}' not found"
                    }
            
            # Generate audio using real Chatterbox TTS (same as your repo)
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                # Voice cloning
                wav = self.model.generate(
                    text, 
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    temperature=temperature
                )
            else:
                # Default voice
                wav = self.model.generate(
                    text,
                    exaggeration=exaggeration,
                    temperature=temperature
                )
            
            # Save to temporary WAV file
            audio_id = f"audio_{uuid.uuid4().hex}"
            temp_wav_path = os.path.join(self.audio_dir, f"{audio_id}.wav")
            
            # Save audio (handle tensor dimensions)
            import torchaudio
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            torchaudio.save(temp_wav_path, wav, self.model.sr)
            
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
            
            # Calculate duration
            duration = len(wav.squeeze()) / self.model.sr
            file_size = os.path.getsize(final_audio_path)
            
            logger.info(f"✅ Speech synthesized: {duration:.2f}s, {file_size} bytes, {audio_format.upper()}")
            
            return {
                "success": True,
                "audio_id": audio_id,
                "audio_url": final_audio_path,
                "playable_url": final_audio_path,
                "message": f"Speech synthesized successfully using voice '{voice_info['name']}'",
                "duration": round(duration, 2),
                "format": audio_format,
                "mime_type": mime_type,
                "sample_rate": self.model.sr,
                "file_size": file_size,
                "voice_used": voice_id,
                "voice_name": voice_info['name'],
                "voice_type": voice_info['type'],
                "exaggeration_used": exaggeration,
                "temperature_used": temperature
            }
            
        except Exception as e:
            # Clean up temp files on error
            for path in [temp_wav_path, temp_mp3_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass
            
            error_msg = f"Speech synthesis failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

# Global handler instance
chatterbox_handler = ChatterboxServerlessHandler()

def handler(event):
    """
    RunPod Serverless handler for Real Chatterbox TTS (based on your working repo)
    """
    temp_files = []
    try:
        input_data = event.get("input", {})
        job_id = event.get("id", "unknown")
        
        logger.info(f"🎭 Chatterbox Serverless processing job: {job_id}")
        logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # Get action (endpoint simulation)
        action = input_data.get("action", "synthesize")  # Default to synthesis
        
        # JWT Authentication (if required)
        if chatterbox_handler.jwt_required and action not in ['health', 'voices']:
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
        
        # Handle different actions (simulating your repo's endpoints)
        
        if action == "health":
            # Health check
            return {
                "status": "healthy",
                "model": "chatterbox",
                "version": "serverless-1.0",
                "chatterbox_available": CHATTERBOX_AVAILABLE,
                "device": chatterbox_handler.device,
                "job_id": job_id,
                "success": True
            }
        
        elif action == "voices" or action == "list_voices":
            # List voices
            result = chatterbox_handler.list_voices()
            result.update({
                "job_id": job_id,
                "model": "chatterbox"
            })
            return result
        
        elif action == "create_voice":
            # Create voice from audio data
            voice_name = input_data.get("voice_name")
            voice_description = input_data.get("voice_description", "")
            audio_base64 = input_data.get("audio_base64")
            
            if not voice_name or not audio_base64:
                return {
                    "error": "Missing voice_name or audio_base64",
                    "job_id": job_id,
                    "success": False
                }
            
            try:
                audio_data = base64.b64decode(audio_base64)
                result = chatterbox_handler.create_voice_from_audio(voice_name, voice_description, audio_data)
                result.update({
                    "job_id": job_id,
                    "model": "chatterbox"
                })
                return result
            except Exception as e:
                return {
                    "error": f"Voice creation failed: {str(e)}",
                    "job_id": job_id,
                    "success": False
                }
        
        elif action == "synthesize" or not action:
            # Synthesize speech (main functionality)
            text = input_data.get("text")
            if not text:
                return {
                    "error": "Missing text parameter",
                    "job_id": job_id,
                    "success": False
                }
            
            voice_id = input_data.get("voice_id", "female_default")
            exaggeration = float(input_data.get("exaggeration", 0.5))
            temperature = float(input_data.get("temperature", 0.8))
            output_format = input_data.get("format", "mp3")
            
            logger.info(f"🎤 Synthesizing with voice: {voice_id}, exaggeration: {exaggeration}")
            
            result = chatterbox_handler.synthesize_speech(
                text=text,
                voice_id=voice_id,
                exaggeration=exaggeration,
                temperature=temperature,
                output_format=output_format
            )
            
            if result.get("success") and result.get("audio_url"):
                temp_files.append(result["audio_url"])
            
            result.update({
                "job_id": job_id,
                "model": "chatterbox",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return result
        
        else:
            return {
                "error": f"Unknown action: {action}",
                "available_actions": ["health", "voices", "create_voice", "synthesize"],
                "job_id": job_id,
                "success": False
            }
        
    except Exception as e:
        # Clean up temp files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        error_msg = f"Chatterbox serverless handler error: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        
        return {
            "error": error_msg,
            "model": "chatterbox",
            "job_id": job_id,
            "success": False,
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        print("🧪 Testing Chatterbox Serverless Handler...")
        
        # Test health
        result = handler({"id": "test_health", "input": {"action": "health"}})
        print(f"Health: {result.get('status')}")
        
        # Test voices
        result = handler({"id": "test_voices", "input": {"action": "voices"}})
        print(f"Voices: {result.get('total', 0)} available")
        
        # Test synthesis
        result = handler({
            "id": "test_synth",
            "input": {
                "text": "Hello! This is the real Chatterbox model speaking with voice cloning!",
                "voice_id": "female_default",
                "exaggeration": 0.7,
                "format": "mp3"
            }
        })
        print(f"Synthesis: {result.get('success', False)}")
        if result.get('audio_url'):
            print(f"Audio: {result['audio_url']} ({result.get('duration')}s)")
        
    else:
        logger.info("🚀 Starting Chatterbox TTS Serverless Handler")
        logger.info(f"🎭 Based on working repo implementation")
        logger.info(f"🔧 JWT: {'Enabled' if chatterbox_handler.jwt_required else 'Disabled'}")
        logger.info(f"🎯 Device: {chatterbox_handler.device}")
        logger.info(f"🤖 Chatterbox Available: {CHATTERBOX_AVAILABLE}")
        
        runpod.serverless.start({"handler": handler})
