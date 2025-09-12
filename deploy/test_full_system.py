import requests
import json
import base64
import time
import sys
from typing import Dict, Any, List

class TTSSystemTester:
    def __init__(self, gateway_endpoint: str):
        self.gateway_endpoint = gateway_endpoint.rstrip('/')
        self.jwt_token = None
        self.test_results = []
    
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })
    
    def test_gateway_health(self) -> bool:
        """Test gateway health endpoint"""
        try:
            response = requests.get(f"{self.gateway_endpoint}/health", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                version = data.get('gateway_version', 'unknown')
                engines = len(data.get('available_engines', []))
                self.log_test("Gateway Health", True, f"Version: {version}, Engines: {engines}")
                return True
            else:
                self.log_test("Gateway Health", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Gateway Health", False, str(e))
            return False
    
    def test_jwt_generation(self) -> bool:
        """Test JWT token generation"""
        try:
            payload = {
                "input": {
                    "action": "generate_token",
                    "user_id": "system_test_user",
                    "user_data": {"role": "system_tester"}
                }
            }
            
            response = requests.post(
                self.gateway_endpoint, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.jwt_token = data.get('token')
                    expires = data.get('expires_in_hours', 0)
                    self.log_test("JWT Generation", True, f"Token generated, expires in {expires}h")
                    return True
                else:
                    self.log_test("JWT Generation", False, data.get('error', 'Unknown error'))
                    return False
            else:
                self.log_test("JWT Generation", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("JWT Generation", False, str(e))
            return False
    
    def test_engine_synthesis(self, engine: str, text: str, voice: str = None, **kwargs) -> bool:
        """Test TTS synthesis for specific engine"""
        try:
            payload = {
                "input": {
                    "jwt_token": self.jwt_token,
                    "text": text,
                    "engine": engine,
                    "format": "mp3"
                }
            }
            
            if voice:
                payload["input"]["voice"] = voice
            
            # Add engine-specific parameters
            payload["input"].update(kwargs)
            
            response = requests.post(
                self.gateway_endpoint,
                json=payload,
                timeout=120  # Longer timeout for TTS
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    duration = data.get('duration', 0)
                    voice_used = data.get('voice_used', 'unknown')
                    audio_format = data.get('format', 'unknown')
                    self.log_test(f"{engine.title()} Synthesis", True, 
                                f"Voice: {voice_used}, Duration: {duration}s, Format: {audio_format}")
                    return True
                else:
                    self.log_test(f"{engine.title()} Synthesis", False, data.get('error', 'Unknown error'))
                    return False
            else:
                self.log_test(f"{engine.title()} Synthesis", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"{engine.title()} Synthesis", False, str(e))
            return False
    
    def test_voice_listing(self, engine: str) -> bool:
        """Test voice listing for engine"""
        try:
            payload = {
                "input": {
                    "jwt_token": self.jwt_token,
                    "action": "list_voices",
                    "engine": engine
                }
            }
            
            response = requests.post(
                self.gateway_endpoint,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    total = data.get('total', 0)
                    builtin = data.get('builtin', 0)
                    custom = data.get('custom', 0)
                    self.log_test(f"{engine.title()} Voice List", True, 
                                f"Total: {total} (Builtin: {builtin}, Custom: {custom})")
                    return True
                else:
                    self.log_test(f"{engine.title()} Voice List", False, data.get('error', 'Unknown error'))
                    return False
            else:
                self.log_test(f"{engine.title()} Voice List", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"{engine.title()} Voice List", False, str(e))
            return False
    
    def test_unauthorized_access(self) -> bool:
        """Test that requests without JWT are rejected"""
        try:
            payload = {
                "input": {
                    "text": "This should fail without JWT",
                    "engine": "chatterbox"
                }
            }
            
            response = requests.post(
                self.gateway_endpoint,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Should fail with auth error
                if not data.get('success') and 'AUTHENTICATION' in data.get('error', '').upper():
                    self.log_test("Unauthorized Access Block", True, "Properly rejected unauthorized request")
                    return True
                else:
                    self.log_test("Unauthorized Access Block", False, "Request should have been rejected")
                    return False
            else:
                self.log_test("Unauthorized Access Block", False, f"Unexpected HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Unauthorized Access Block", False, str(e))
            return False
    
    def run_comprehensive_tests(self):
        """Run all system tests"""
        print("🧪 TTS V3 Serverless System - Comprehensive Tests")
        print("=" * 60)
        
        # Basic connectivity tests
        if not self.test_gateway_health():
            print("❌ Gateway health failed - aborting tests")
            return False
        
        if not self.test_jwt_generation():
            print("❌ JWT generation failed - aborting tests")
            return False
        
        # Security tests
        self.test_unauthorized_access()
        
        # Engine tests
        engines_to_test = [
            {
                "name": "chatterbox",
                "text": "Hello! This is a test of the real Chatterbox TTS system with voice cloning.",
                "voice": "female_default",
                "exaggeration": 0.7
            },
            {
                "name": "kokkoro", 
                "text": "こんにちは！私はココロです！元気ですか？",
                "voice": "kokkoro_sweet",
                "speed": 1.0
            }
        ]
        
        for engine_test in engines_to_test:
            engine = engine_test.pop("name")
            
            # Test voice listing
            self.test_voice_listing(engine)
            
            # Test synthesis
            self.test_engine_synthesis(engine, **engine_test)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"   Passed: {passed}/{total}")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - System is fully operational!")
        else:
            print("⚠️ Some tests failed - check logs above")
            failed_tests = [r['test'] for r in self.test_results if not r['success']]
            print(f"   Failed tests: {', '.join(failed_tests)}")
        
        return passed == total

def main():
    """Main test execution"""
    if len(sys.argv) < 2:
        gateway_endpoint = input("Enter Gateway endpoint URL: ").strip()
    else:
        gateway_endpoint = sys.argv[1]
    
    if not gateway_endpoint:
        print("❌ Gateway endpoint required")
        sys.exit(1)
    
    if not gateway_endpoint.startswith(('http://', 'https://')):
        gateway_endpoint = f"https://{gateway_endpoint}"
    
    print(f"🎯 Testing TTS V3 Serverless System")
    print(f"📡 Gateway: {gateway_endpoint}")
    print()
    
    tester = TTSSystemTester(gateway_endpoint)
    success = tester.run_comprehensive_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
