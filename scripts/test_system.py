#!/usr/bin/env python3
import requests
import json
import time
import base64

class TTSSystemTester:
    def __init__(self, gateway_url, api_key=None):
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json'
        }
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def test_health(self):
        """Test gateway health"""
        print("🔍 Testing gateway health...")
        try:
            response = requests.post(
                self.gateway_url,
                json={"input": {"action": "health_check"}},
                headers=self.headers,
                timeout=10
            )
            result = response.json()
            print(f"✅ Health check: {result}")
            return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def test_models_list(self):
        """Test getting available models"""
        print("📋 Testing models list...")
        try:
            response = requests.post(
                self.gateway_url,
                json={"input": {"action": "get_models"}},
                headers=self.headers,
                timeout=10
            )
            result = response.json()
            print(f"✅ Available models: {result}")
            return result.get('output', {}).get('models', [])
        except Exception as e:
            print(f"❌ Models list failed: {e}")
            return []
    
    def test_tts_synthesis(self, text, model):
        """Test TTS synthesis"""
        print(f"🎵 Testing TTS synthesis with {model}...")
        try:
            start_time = time.time()
            response = requests.post(
                self.gateway_url,
                json={
                    "input": {
                        "text": text,
                        "model": model,
                        "voice": "default",
                        "speed": 1.0
                    }
                },
                headers=self.headers,
                timeout=60
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and result['output'].get('audio_base64'):
                    audio_size = len(result['output']['audio_base64'])
                    print(f"✅ TTS synthesis successful!")
                    print(f"   Model: {result['output'].get('model_used')}")
                    print(f"   Duration: {result['output'].get('duration')} seconds")
                    print(f"   Audio size: {audio_size} characters (base64)")
                    print(f"   Response time: {end_time - start_time:.2f} seconds")
                    
                    # Save audio file for verification
                    if result['output'].get('audio_base64'):
                        self.save_audio(result['output']['audio_base64'], f"test_{model}_{int(time.time())}.mp3")
                    
                    return True
                else:
                    print(f"❌ No audio data in response: {result}")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
            
        except Exception as e:
            print(f"❌ TTS synthesis failed: {e}")
        
        return False
    
    def save_audio(self, audio_base64, filename):
        """Save base64 audio to file"""
        try:
            audio_data = base64.b64decode(audio_base64)
            with open(filename, 'wb') as f:
                f.write(audio_data)
            print(f"💾 Audio saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save audio: {e}")
    
    def run_full_test(self):
        """Run complete system test"""
        print("🚀 Starting full TTS system test...\n")
        
        # Test 1: Health check
        if not self.test_health():
            print("❌ System is not healthy, aborting tests")
            return False
        
        print()
        
        # Test 2: Get available models
        models = self.test_models_list()
        if not models:
            print("❌ No models available, aborting tests")
            return False
        
        print()
        
        # Test 3: Test each model
        test_text = "Hello! This is a test of the modular text-to-speech system."
        success_count = 0
        
        for model in models:
            if self.test_tts_synthesis(test_text, model):
                success_count += 1
            print()
        
        # Summary
        print(f"📊 Test Summary:")
        print(f"   Total models: {len(models)}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {len(models) - success_count}")
        
        if success_count == len(models):
            print("🎉 All tests passed! System is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the logs above.")
            return False

if __name__ == "__main__":
    # Configuration
    GATEWAY_URL = input("Enter Gateway URL: ").strip()
    API_KEY = input("Enter API Key (or press Enter to skip): ").strip() or None
    
    if not GATEWAY_URL:
        print("❌ Gateway URL is required")
        exit(1)
    
    # Run tests
    tester = TTSSystemTester(GATEWAY_URL, API_KEY)
    success = tester.run_full_test()
    
    exit(0 if success else 1)
