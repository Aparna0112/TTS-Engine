# secure_client_example.py - Properly handles JWT authentication
import requests
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class SecureTTSClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.token_expires_at = None
        self.session = requests.Session()
        self.username = None
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired"""
        if not self.token or not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at
    
    def _clear_auth(self):
        """Clear authentication data"""
        self.token = None
        self.token_expires_at = None
        self.username = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def login(self, username: str, password: str) -> bool:
        """Login and store JWT token with expiration tracking"""
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            print(f"🔐 Attempting login for user: {username}")
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                self.username = username
                
                # Estimate token expiration (30 minutes minus 1 minute buffer)
                self.token_expires_at = datetime.now() + timedelta(minutes=29)
                
                # Set authorization header for all future requests
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                
                print(f"✅ Login successful for user: {username}")
                print(f"🎫 Token expires at: {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                print(f"❌ Login failed ({response.status_code}): {error_data}")
                self._clear_auth()
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"🔥 Network error during login: {e}")
            self._clear_auth()
            return False
        except Exception as e:
            print(f"🔥 Unexpected error during login: {e}")
            self._clear_auth()
            return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid, non-expired token"""
        if self._is_token_expired():
            print("⚠️  Token expired or missing. Please login again.")
            self._clear_auth()
            return False
        return True
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        if not self._ensure_authenticated():
            return None
        
        try:
            response = self.session.get(f"{self.base_url}/auth/me", timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"👤 Current user: {user_info}")
                return user_info
            elif response.status_code == 401:
                print("❌ Authentication failed - token may be invalid or expired")
                self._clear_auth()
                return None
            else:
                print(f"❌ Failed to get user info ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"🔥 Error getting user info: {e}")
            return None
    
    def generate_speech(self, text: str, model: str, voice: Optional[str] = None, speed: float = 1.0) -> Optional[Dict[str, Any]]:
        """Generate speech using TTS - REQUIRES AUTHENTICATION"""
        if not self._ensure_authenticated():
            print("🚨 Cannot generate speech: Authentication required!")
            print("💡 Please call login(username, password) first")
            return None
        
        tts_data = {
            "text": text,
            "model": model,
            "voice": voice or "default",
            "speed": speed
        }
        
        try:
            print(f"🎵 Generating speech for '{text[:50]}...' using {model}")
            
            response = self.session.post(
                f"{self.base_url}/tts",
                json=tts_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ TTS Generation successful:")
                print(f"   👤 User: {result.get('user')}")
                print(f"   🤖 Model: {result['model_used']}")
                print(f"   🎧 Audio URL: {result['audio_url']}")
                print(f"   💬 Message: {result['message']}")
                return result
            elif response.status_code == 401:
                print("🚨 Authentication failed - your JWT token is invalid or expired")
                print("💡 Please login again")
                self._clear_auth()
                return None
            elif response.status_code == 400:
                error_data = response.json()
                print(f"❌ Invalid request ({response.status_code}): {error_data.get('detail')}")
                return None
            elif response.status_code in [503, 504]:
                print(f"⚠️  TTS service unavailable ({response.status_code})")
                print("🔧 The authentication worked, but the TTS engine is not responding")
                return None
            else:
                print(f"❌ TTS generation failed ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"🔥 Error during TTS generation: {e}")
            return None
    
    def list_models(self) -> Optional[Dict[str, Any]]:
        """List available TTS models - REQUIRES AUTHENTICATION"""
        if not self._ensure_authenticated():
            print("🚨 Cannot list models: Authentication required!")
            return None
        
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=10)
            
            if response.status_code == 200:
                models = response.json()
                print(f"📋 Available models: {models['available_models']}")
                print(f"📊 Total models: {models['total_models']}")
                print(f"👤 User: {models['user']}")
                return models
            elif response.status_code == 401:
                print("🚨 Authentication failed - token may be invalid or expired")
                self._clear_auth()
                return None
            else:
                print(f"❌ Failed to get models ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"🔥 Error listing models: {e}")
            return None
    
    def batch_generate_speech(self, requests: list) -> Optional[Dict[str, Any]]:
        """Generate speech for multiple texts - REQUIRES AUTHENTICATION"""
        if not self._ensure_authenticated():
            print("🚨 Cannot generate batch speech: Authentication required!")
            return None
        
        try:
            print(f"🎵 Generating batch speech for {len(requests)} items")
            
            response = self.session.post(
                f"{self.base_url}/tts/batch",
                json=requests,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Batch TTS completed:")
                print(f"   📊 Total requested: {result['total_requested']}")
                print(f"   ✅ Successful: {result['successful']}")
                print(f"   ❌ Failed: {result['failed']}")
                print(f"   👤 User: {result['user']}")
                return result
            elif response.status_code == 401:
                print("🚨 Authentication failed - token may be invalid or expired")
                self._clear_auth()
                return None
            else:
                print(f"❌ Batch TTS failed ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"🔥 Error during batch TTS: {e}")
            return None
    
    def health_check(self) -> Optional[Dict[str, Any]]:
        """Check system health (PUBLIC endpoint - no authentication required)"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health = response.json()
                print(f"🏥 System Health: {health['status']}")
                print(f"🔒 Authentication required: {health['authentication_required']}")
                
                for model_name, model_status in health['models'].items():
                    status_emoji = "✅" if model_status['status'] == 'healthy' else "❌"
                    print(f"   {status_emoji} {model_name}: {model_status['status']}")
                    
                return health
            else:
                print(f"❌ Health check failed ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            print(f"🔥 Error during health check: {e}")
            return None
    
    def test_security(self):
        """Test security by attempting unauthorized access"""
        print("\n🛡️  TESTING SECURITY...")
        print("=" * 50)
        
        # Save current auth state
        saved_token = self.token
        saved_headers = dict(self.session.headers)
        
        # Remove authentication
        self._clear_auth()
        print("🔓 Removed authentication credentials")
        
        # Try to access protected endpoints
        print("\n🚨 Attempting unauthorized access to TTS endpoint...")
        result = self.generate_speech("Unauthorized test", "kokkoro")
        if result is None:
            print("✅ GOOD: TTS endpoint properly rejected unauthorized access")
        else:
            print("🚨 SECURITY ISSUE: TTS endpoint allowed unauthorized access!")
        
        print("\n🚨 Attempting unauthorized access to models endpoint...")
        result = self.list_models()
        if result is None:
            print("✅ GOOD: Models endpoint properly rejected unauthorized access")
        else:
            print("🚨 SECURITY ISSUE: Models endpoint allowed unauthorized access!")
        
        # Restore authentication
        self.token = saved_token
        self.session.headers.update(saved_headers)
        if saved_token:
            self.token_expires_at = datetime.now() + timedelta(minutes=29)
            print("\n🔐 Restored authentication credentials")
        
        print("🛡️  Security test completed\n")

def demonstrate_secure_usage():
    """Demonstrate proper secure usage of the TTS client"""
    print("🚀 TTS Gateway Secure Client Demonstration")
    print("=" * 60)
    
    # Initialize client
    client = SecureTTSClient("http://localhost:8000")
    
    # Test 1: Health check (public endpoint)
    print("\n1. 🏥 Testing health check (PUBLIC - no auth required):")
    client.health_check()
    
    # Test 2: Try TTS without authentication (should fail)
    print("\n2. 🚨 Testing TTS without authentication (should fail):")
    client.generate_speech("Hello world", "kokkoro")
    
    # Test 3: Login
    print("\n3. 🔐 Testing login:")
    success = client.login("testuser", "secret")
    
    if not success:
        print("❌ Login failed - cannot continue with authenticated tests")
        return
    
    # Test 4: Get user info
    print("\n4. 👤 Getting user info:")
    client.get_user_info()
    
    # Test 5: List models
    print("\n5. 📋 Listing available models:")
    client.list_models()
    
    # Test 6: Generate speech with authentication
    print("\n6. 🎵 Testing TTS with authentication:")
    client.generate_speech(
        text="Hello, this is a secure TTS request!",
        model="kokkoro",
        voice="default",
        speed=1.0
    )
    
    # Test 7: Batch generation
    print("\n7. 🎵 Testing batch TTS:")
    batch_requests = [
        {"text": "First message", "model": "kokkoro"},
        {"text": "Second message", "model": "chatterbox"}
    ]
    client.batch_generate_speech(batch_requests)
    
    # Test 8: Security testing
    print("\n8. 🛡️  Testing security:")
    client.test_security()
    
    # Test 9: Try with wrong credentials
    print("\n9. 🚨 Testing wrong credentials:")
    wrong_client = SecureTTSClient("http://localhost:8000")
    wrong_client.login("wrong_user", "wrong_pass")
    
    print("\n✨ Demonstration completed!")
    print("\n🔒 SECURITY SUMMARY:")
    print("   ✅ Public endpoints work without authentication")
    print("   ✅ Protected endpoints require valid JWT tokens") 
    print("   ✅ Invalid credentials are rejected")
    print("   ✅ Authentication state is properly managed")

def create_production_client_example():
    """Example for production usage"""
    print("\n" + "=" * 60)
    print("🏭 PRODUCTION CLIENT EXAMPLE")
    print("=" * 60)
    
    production_example = '''
# production_tts_client.py
from secure_client_example import SecureTTSClient
import os
from typing import Optional

class ProductionTTSService:
    def __init__(self):
        self.client = SecureTTSClient(
            base_url=os.getenv("TTS_GATEWAY_URL", "https://your-tts-api.com")
        )
        self.is_authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with stored credentials"""
        username = os.getenv("TTS_USERNAME")
        password = os.getenv("TTS_PASSWORD")
        
        if not username or not password:
            raise ValueError("TTS_USERNAME and TTS_PASSWORD environment variables required")
        
        self.is_authenticated = self.client.login(username, password)
        return self.is_authenticated
    
    def generate_speech_safe(self, text: str, model: str = "kokkoro") -> Optional[str]:
        """Generate speech with automatic authentication"""
        if not self.is_authenticated:
            if not self.authenticate():
                return None
        
        result = self.client.generate_speech(text, model)
        
        if result is None and not self.is_authenticated:
            # Try re-authenticating once
            if self.authenticate():
                result = self.client.generate_speech(text, model)
        
        return result.get("audio_url") if result else None

# Usage in your application:
if __name__ == "__main__":
    tts_service = ProductionTTSService()
    
    audio_url = tts_service.generate_speech_safe(
        "Welcome to our application!", 
        "kokkoro"
    )
    
    if audio_url:
        print(f"Speech generated: {audio_url}")
    else:
        print("Failed to generate speech")
'''
    
    print(production_example)

if __name__ == "__main__":
    # Check if server is accessible
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ TTS Gateway is accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot access TTS Gateway at http://localhost:8000: {e}")
        print("Please start your TTS Gateway first with: python gateway/main.py")
        exit(1)
    
    # Run demonstration
    demonstrate_secure_usage()
    
    # Show production example
    create_production_client_example()
    
    print("\n🎉 Secure client demonstration completed!")
    print("🔐 Remember: ALWAYS authenticate before using TTS endpoints!")
