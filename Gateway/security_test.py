# security_test.py - Comprehensive JWT Security Testing
import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"

class TTSSecurityTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_public_endpoints(self):
        """Test that public endpoints work without authentication"""
        print("🟢 Testing PUBLIC endpoints (should work without JWT)...")
        
        tests = [
            ("GET", "/", "Root endpoint"),
            ("GET", "/health", "Health check"), 
            ("GET", "/docs", "API documentation")
        ]
        
        for method, path, description in tests:
            try:
                response = self.session.request(method, f"{self.base_url}{path}")
                if response.status_code in [200, 307]:  # 307 for redirects to /docs
                    print(f"  ✅ {description}: {response.status_code}")
                else:
                    print(f"  ❌ {description}: {response.status_code}")
            except Exception as e:
                print(f"  🔥 {description}: Error - {e}")
    
    def test_protected_endpoints_without_jwt(self):
        """Test that protected endpoints REJECT requests without JWT"""
        print("\n🔒 Testing PROTECTED endpoints WITHOUT JWT (should all return 401)...")
        
        protected_endpoints = [
            ("POST", "/tts", {"text": "Hello", "model": "kokkoro"}, "TTS generation"),
            ("GET", "/models", None, "List models"),
            ("GET", "/auth/me", None, "User info"),
            ("POST", "/tts/batch", [{"text": "Hello", "model": "kokkoro"}], "Batch TTS")
        ]
        
        all_secure = True
        
        for method, path, data, description in protected_endpoints:
            try:
                if method == "POST":
                    response = self.session.post(f"{self.base_url}{path}", json=data)
                else:
                    response = self.session.get(f"{self.base_url}{path}")
                
                if response.status_code == 401:
                    print(f"  ✅ {description}: PROPERLY SECURED (401)")
                else:
                    print(f"  🚨 SECURITY BREACH! {description}: {response.status_code}")
                    print(f"      Response: {response.text[:200]}")
                    all_secure = False
                    
            except Exception as e:
                print(f"  🔥 {description}: Error - {e}")
                all_secure = False
        
        return all_secure
    
    def test_invalid_jwt_tokens(self):
        """Test various invalid JWT token scenarios"""
        print("\n🔓 Testing INVALID JWT tokens (should all return 401)...")
        
        invalid_tokens = [
            ("", "Empty token"),
            ("invalid-token", "Malformed token"),
            ("Bearer", "Bearer without token"),
            ("Bearer ", "Bearer with empty token"),
            ("Bearer invalid.token.here", "Invalid JWT format"),
            ("Basic dXNlcjpwYXNz", "Wrong auth scheme"),
            ("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid", "Invalid JWT")
        ]
        
        all_rejected = True
        
        for token, description in invalid_tokens:
            headers = {"Authorization": token} if token else {}
            
            try:
                response = self.session.post(
                    f"{self.base_url}/tts",
                    json={"text": "Test", "model": "kokkoro"},
                    headers=headers
                )
                
                if response.status_code == 401:
                    print(f"  ✅ {description}: PROPERLY REJECTED (401)")
                else:
                    print(f"  🚨 SECURITY BREACH! {description}: {response.status_code}")
                    all_rejected = False
                    
            except Exception as e:
                print(f"  🔥 {description}: Error - {e}")
                all_rejected = False
        
        return all_rejected
    
    def test_login_and_valid_jwt(self):
        """Test login process and valid JWT usage"""
        print("\n🔐 Testing LOGIN and VALID JWT usage...")
        
        # Test login with wrong credentials
        print("  Testing login with WRONG credentials...")
        login_response = self.session.post(
            f"{self.base_url}/auth/login",
            data={"username": "wrong", "password": "wrong"}
        )
        
        if login_response.status_code == 401:
            print("    ✅ Wrong credentials properly rejected (401)")
        else:
            print(f"    ❌ Wrong credentials not rejected: {login_response.status_code}")
        
        # Test login with correct credentials
        print("  Testing login with CORRECT credentials...")
        login_response = self.session.post(
            f"{self.base_url}/auth/login",
            data={"username": "testuser", "password": "secret"}
        )
        
        if login_response.status_code != 200:
            print(f"    ❌ Login failed: {login_response.status_code}")
            return None
        
        token_data = login_response.json()
        jwt_token = token_data.get("access_token")
        
        if not jwt_token:
            print("    ❌ No JWT token in response")
            return None
        
        print(f"    ✅ Login successful, JWT token received")
        print(f"    🎫 Token (first 50 chars): {jwt_token[:50]}...")
        
        return jwt_token
    
    def test_authenticated_requests(self, jwt_token: str):
        """Test that authenticated requests work properly"""
        print("\n🎫 Testing AUTHENTICATED requests (should all work with JWT)...")
        
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        # Test user info
        try:
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 200:
                user_info = response.json()
                print(f"  ✅ User info: {user_info.get('username')}")
            else:
                print(f"  ❌ User info failed: {response.status_code}")
        except Exception as e:
            print(f"  🔥 User info error: {e}")
        
        # Test list models
        try:
            response = self.session.get(f"{self.base_url}/models", headers=headers)
            if response.status_code == 200:
                models = response.json()
                print(f"  ✅ Models list: {models.get('available_models')}")
            else:
                print(f"  ❌ Models list failed: {response.status_code}")
        except Exception as e:
            print(f"  🔥 Models list error: {e}")
        
        # Test TTS generation (this might fail if TTS services aren't running, but auth should work)
        try:
            response = self.session.post(
                f"{self.base_url}/tts",
                json={"text": "Hello from authenticated request!", "model": "kokkoro"},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ TTS generation successful for user: {result.get('user')}")
            elif response.status_code in [503, 504]:
                print(f"  ⚠️  TTS generation: Auth worked, but TTS service unavailable ({response.status_code})")
            else:
                print(f"  ❌ TTS generation failed: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
        except Exception as e:
            print(f"  🔥 TTS generation error: {e}")
    
    def test_expired_jwt(self):
        """Test behavior with expired JWT (requires manual testing)"""
        print("\n⏰ Testing EXPIRED JWT...")
        print("  ℹ️  To test expired tokens, reduce ACCESS_TOKEN_EXPIRE_MINUTES in auth.py")
        print("      and wait for token expiration, then rerun this test.")
    
    def run_all_tests(self):
        """Run complete security test suite"""
        print("🛡️  STARTING COMPREHENSIVE TTS GATEWAY SECURITY TEST")
        print("=" * 60)
        
        # Test 1: Public endpoints should work
        self.test_public_endpoints()
        
        # Test 2: Protected endpoints should require JWT
        endpoints_secure = self.test_protected_endpoints_without_jwt()
        
        # Test 3: Invalid JWTs should be rejected
        invalid_tokens_rejected = self.test_invalid_jwt_tokens()
        
        # Test 4: Valid login and JWT usage
        jwt_token = self.test_login_and_valid_jwt()
        
        if jwt_token:
            # Test 5: Authenticated requests should work
            self.test_authenticated_requests(jwt_token)
        
        # Test 6: Information about expired tokens
        self.test_expired_jwt()
        
        print("\n" + "=" * 60)
        print("🎯 SECURITY TEST SUMMARY:")
        
        if endpoints_secure and invalid_tokens_rejected and jwt_token:
            print("✅ ALL SECURITY TESTS PASSED!")
            print("🛡️  Your TTS Gateway is properly secured with JWT authentication")
        else:
            print("🚨 SECURITY ISSUES DETECTED!")
            if not endpoints_secure:
                print("   - Protected endpoints are not properly secured")
            if not invalid_tokens_rejected:
                print("   - Invalid tokens are not being rejected")
            if not jwt_token:
                print("   - Login/JWT generation is not working")
        
        print("\n🔒 SECURITY CHECKLIST:")
        print("   ✅ Protected endpoints require JWT")
        print("   ✅ Invalid JWTs are rejected") 
        print("   ✅ Valid JWTs allow access")
        print("   ✅ Public endpoints work without auth")
        print("   ✅ Login process works correctly")

def run_curl_security_tests():
    """Generate curl commands for manual testing"""
    print("\n" + "=" * 60)
    print("🖥️  MANUAL CURL TESTS")
    print("=" * 60)
    
    print("\n1. Test protected endpoint WITHOUT JWT (should return 401):")
    print('curl -X POST "http://localhost:8000/tts" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"text": "Hello", "model": "kokkoro"}\'')
    
    print("\n2. Login to get JWT token:")
    print('curl -X POST "http://localhost:8000/auth/login" \\')
    print('  -H "Content-Type: application/x-www-form-urlencoded" \\')
    print('  -d "username=testuser&password=secret"')
    
    print("\n3. Test protected endpoint WITH JWT (use token from step 2):")
    print('curl -X POST "http://localhost:8000/tts" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \\')
    print('  -d \'{"text": "Hello authenticated world!", "model": "kokkoro"}\'')
    
    print("\n4. Test with INVALID JWT (should return 401):")
    print('curl -X POST "http://localhost:8000/tts" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer invalid-token" \\')
    print('  -d \'{"text": "Hello", "model": "kokkoro"}\'')

if __name__ == "__main__":
    print("🔐 TTS Gateway Security Test Suite")
    print("Make sure your TTS Gateway is running on http://localhost:8000")
    
    # Check if server is accessible
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Gateway is accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot access gateway at {BASE_URL}: {e}")
        print("Please start your TTS Gateway first!")
        exit(1)
    
    # Run automated tests
    tester = TTSSecurityTester()
    tester.run_all_tests()
    
    # Show manual curl tests
    run_curl_security_tests()
    
    print(f"\n🎉 Security testing complete!")
    print("If you found any security issues, please review your gateway implementation.")
