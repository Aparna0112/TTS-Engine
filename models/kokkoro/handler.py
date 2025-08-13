import tempfile
import os
import base64
import io
from typing import Dict
from gtts import gTTS

class KokkoroHandler:
    def __init__(self):
        print("Initializing Kokkoro TTS handler with Google TTS")
        self.model_name = "kokkoro"
    
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
