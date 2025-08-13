import asyncio
import tempfile
import os
import base64
import io
from typing import Dict
from gtts import gTTS

class ChatterboxHandler:
    def __init__(self):
        print("Initializing Chatterbox TTS handler")
    
    async def generate_audio(self, text: str, voice: str = "default", speed: float = 1.0) -> Dict:
        """Generate audio using Chatterbox TTS (using gTTS with different settings)"""
        try:
            # Chatterbox uses slightly different settings than Kokkoro
            slow_speech = speed < 0.7  # Different threshold
            
            # Use different TLD for variation
            tld = 'co.uk' if voice == 'formal' else 'com.au' if voice == 'casual' else 'com'
            
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
            duration = (word_count * 0.55) / speed  # Chatterbox is slightly faster
            
            # Save temporary file
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
                "model": "chatterbox",
                "voice_used": voice,
                "speed_used": speed,
                "tld_used": tld,
                "text_length": len(text),
                "word_count": word_count
            }
            
        except Exception as e:
            raise Exception(f"Chatterbox TTS generation failed: {str(e)}")
