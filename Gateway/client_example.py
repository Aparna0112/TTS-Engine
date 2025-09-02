# client_example.py
import requests
import json
from typing import Optional

class TTSClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def login(self, username: str, password: str) -> bool:
        """Login and store JWT token."""
        login_data = {
            "username": username,
            "password": password
        }
        
        response = self.session.post(
            f"{self.base_url}/auth/login",
            data=login_data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            # Set authorization header for future requests
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
            print(f"✅ Login successful for user: {username}")
            return True
        else:
            print(f"❌ Login failed: {response.text}")
            return False
    
    def get_user_info(self):
        """Get current user information."""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        response = self.session.get(f"{self.base_url}/auth/me")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"👤 Current user: {user_info}")
            return user_info
        else:
            print(f"❌ Failed to get user info: {response.text}")
            return None
    
    def generate_speech(self, text: str, model: str, voice: Optional[str] = None, speed: float = 1.0):
        """Generate speech using TTS."""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        tts_data = {
            "text": text,
            "model": model,
            "voice": voice or "default",
            "speed": speed
        }
        
        response = self.session.post(
            f"{self.base_url}/tts",
            json=tts_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"🎵 TTS Generation successful:")
            print(f"   Model: {result['model_used']}")
            print(f"   Audio URL: {result['audio_url']}")
            print(f"   Message: {result['message']}")
            return result
        else:
            print(f"❌ TTS generation failed: {response.text}")
            return None
    
    def list_models(self):
        """List available TTS models."""
        if not self.token:
            print("❌ Not authenticated. Please login first.")
            return None
        
        response = self.session.get(f"{self.base_url}/models")
        
        if response.status_code == 200:
            models = response.json()
            print(f"📋 Available models: {models}")
            return models
        else:
            print(f"❌ Failed to get models: {response.text}")
            return None
    
    def health_check(self):
        """Check system health (no authentication required)."""
        response = requests.get(f"{self.base_url}/health")
        
        if response.status_code == 200:
            health = response.json()
            print(f"🏥 System Health: {health}")
            return health
        else:
            print(f"❌ Health check failed: {response.text}")
            return None

# Example usage and testing
def main():
    print("🚀 TTS Gateway Client Example")
    print("=" * 40)
    
    # Initialize client
    client = TTSClient("http://localhost:8000")
    
    # Test 1: Health check (no auth required)
    print("\n1. Testing health check (no auth required):")
    client.health_check()
    
    # Test 2: Try TTS without authentication (should fail)
    print("\n2. Testing TTS without authentication (should fail):")
    client.generate_speech("Hello world", "kokkoro")
    
    # Test 3: Login
    print("\n3. Testing login:")
    success = client.login("testuser", "secret")
    
    if success:
        # Test 4: Get user info
        print("\n4. Getting user info:")
        client.get_user_info()
        
        # Test 5: List models
        print("\n5. Listing available models:")
        client.list_models()
        
        # Test 6: Generate speech with Kokkoro
        print("\n6. Testing TTS with Kokkoro model:")
        client.generate_speech(
            text="Hello, this is a test using Kokkoro TTS engine!",
            model="kokkoro",
            voice="default",
            speed=1.0
        )
        
        # Test 7: Generate speech with Chatterbox
        print("\n7. Testing TTS with Chatterbox model:")
        client.generate_speech(
            text="Hello, this is a test using Chatterbox TTS engine!",
            model="chatterbox",
            voice="female",
            speed=0.8
        )
        
        # Test 8: Try invalid model (should fail)
        print("\n8. Testing invalid model (should fail):")
        client.generate_speech(
            text="This should fail",
            model="invalid_model"
        )
    
    print("\n✨ Testing completed!")

if __name__ == "__main__":
    main()

# test_authentication.py
import requests
import pytest

BASE_URL = "http://localhost:8000"

def test_login_success():
    """Test successful login."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "testuser", "password": "secret"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    return data["access_token"]

def test_login_failure():
    """Test login with wrong credentials."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 401

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    response = requests.post(
        f"{BASE_URL}/tts",
        json={"text": "test", "model": "kokkoro"}
    )
    assert response.status_code == 401

def test_protected_endpoint_with_token():
    """Test accessing protected endpoint with valid token."""
    # First login to get token
    token = test_login_success()
    
    # Use token to access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/tts",
        json={"text": "Hello world", "model": "kokkoro"},
        headers=headers
    )
    # Note: This might fail if TTS service is not running, but authentication should work
    assert response.status_code != 401  # Should not be unauthorized

def test_health_endpoint_public():
    """Test that health endpoint is public."""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200

if __name__ == "__main__":
    print("Running authentication tests...")
    try:
        test_login_success()
        print("✅ Login success test passed")
        
        test_login_failure()
        print("✅ Login failure test passed")
        
        test_protected_endpoint_without_token()
        print("✅ Protected endpoint without token test passed")
        
        test_health_endpoint_public()
        print("✅ Public health endpoint test passed")
        
        print("🎉 All authentication tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

# curl_examples.sh
#!/bin/bash

echo "🚀 TTS Gateway JWT Authentication Examples"
echo "=========================================="

BASE_URL="http://localhost:8000"

echo ""
echo "1. Health Check (No auth required):"
curl -X GET "$BASE_URL/health" | jq .

echo ""
echo "2. Try TTS without token (Should fail with 401):"
curl -X POST "$BASE_URL/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "model": "kokkoro"}' | jq .

echo ""
echo "3. Login to get JWT token:"
TOKEN=$(curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=secret" | jq -r .access_token)

echo "Token obtained: $TOKEN"

echo ""
echo "4. Get user info with token:"
curl -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo ""
echo "5. List models with token:"
curl -X GET "$BASE_URL/models" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo ""
echo "6. Generate TTS with token:"
curl -X POST "$BASE_URL/tts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text": "Hello from authenticated TTS!", "model": "kokkoro", "voice": "default", "speed": 1.0}' | jq .
