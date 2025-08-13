import asyncio
import tempfile
import os
import base64
import io
from typing import Dict
from gtts import gTTS

class KokkoroHandler:
    def __init__(self):
        print("Initializing Kokkoro TTS handler with Google TTS")
    
    async def generate_audio(self, text: str, voice: str = "default", 
                           speed: float = 1.0, pitch: float = 1.0) -> Dict:
        """Generate audio using Google TTS (gTTS)"""
        try:
            # Map speed to gTTS slow parameter
            slow_speech = speed < 0.8
            
            # Generate TTS audio
            tts = gTTS(
                text=text, 
                lang='en', 
                slow=slow_speech,
                tld='com'  # Use .com domain for consistency
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
            duration = (word_count * 0.6) / speed  # ~0.6 seconds per word adjusted for speed
            
            # Save to temporary file for compatibility
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                audio_path = tmp_file.name
            
            return {
                "audio_url": audio_path,
                "audio_base64": audio_base64,
                "audio_data_url": audio_data_url,
                "audio_format": "mp3",
                "duration": duration,
                "sample_rate": 22050,
                "model": "kokkoro",
                "voice_used": voice,
                "speed_used": speed,
                "text_length": len(text),
                "word_count": word_count
            }
            
        except Exception as e:
            raise Exception(f"Kokkoro TTS generation failed: {str(e)}")
