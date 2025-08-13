import tempfile
import os
import base64
import io
from typing import Dict
from gtts import gTTS

class ChatterboxHandler:
    def __init__(self):
        print("Initializing Chatterbox TTS handler")
        self.model_name = "chatterbox"
    
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
