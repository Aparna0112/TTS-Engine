# runpod_security_test.py - Test RunPod deployment security
import requests
import json
import time
from typing import Dict, Any, Optional

class RunPodSecurityTester:
    def __init__(self, endpoint_url: str, api_key: str):
        """
        Test RunPod TTS endpoint security
        
        Args:
            endpoint_url: Your RunPod endpoint URL
            api_key: Your RunPod API key
        """
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any], description: str) -> Dict[str, Any]:
        """Make a request to RunPod and return the result"""
        print(f"\n🧪 Testing: {description}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self.session.post(f"{self.endpoint_url}/{endpoint}", json=payload, timeout=30)
            
            print(f"📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                output = result.get('output', {})
                status_code = output.get('statusCode', 'unknown')
                
                print(f"🎯 TTS Gateway Status: {status_code}")
                
                if status_code == 401:
                    print("✅ GOOD: Request was properly rejected (401 Unauthorized)")
                    return {"security_status": "SECURE", "details": output.get('body', {})}
                elif status_code == 200:
                    body = output.get('body', {})
                    if 'access_token' in body:
                        print("✅ GOOD: Login successful")
                        return {"security_status": "LOGIN_SUCCESS", "token": body.get('access_token')}
                    else:
                        print("🚨 SECURITY BREACH: TTS request succeeded without JWT!")
                        return {"security_status": "BREACH", "details": body}
                else:
                    print(f"⚠️  Unexpected status: {status_code}")
                    return {"security_status": "UNEXPECTED", "status_code": status_code, "details": output.get('body', {})}
            else:
                print(f"❌ RunPod request failed: {response.text}")
                return {"security_status": "ERROR", "error": response.text}
                
        except Exception as e:
            print(f"🔥 Request error: {e}")
            return {"security_status": "ERROR", "error": str(e)}
    
    def test_unauthorized_tts_request(self) -> bool:
        """Test TTS request WITHOUT JWT token (should be rejected)"""
        payload = {
            "input": {
                "method": "POST",
                "path": "/tts",
                "body": {
                    "text": "This should be blocked!",
                    "model": "kokkoro"
                }
                # NO Authorization header - should be rejected
            }
        }
        
        result = self._make_request("runsync", payload, "TTS request WITHOUT JWT token")
        return result.get("security_status") == "SECURE"
    
    def test_invalid_jwt_token(self) -> bool:
        """Test TTS request with INVALID JWT token (should be rejected)"""
        payload = {
            "input": {
                "method": "POST",
                "path": "/tts",
                "headers": {
                    "Authorization": "Bearer invalid-token-12345"
                },
                "body": {
                    "text": "This should also be blocked!",
                    "model": "kokkoro"
                }
            }
        }
        
        result = self._make_request("runsync", payload, "TTS request with INVALID JWT token")
        return result.get("security_status") == "SECURE"
    
    def test_login_flow(self) -> Optional[str]:
        """Test login to get JWT token"""
        payload = {
            "input": {
                "method": "POST",
                "path": "/auth/login",
                "body": {
                    "username": "testuser",
                    "password": "secret"
                }
            }
        }
        
        result = self._make_request("runsync", payload, "Login to get JWT token")
        
        if result.get("security_status") == "LOGIN_SUCCESS":
            return result.get("token")
        else:
            print("❌ Login failed")
            return None
    
    def test_authorized_tts_request(self, jwt_token: str) -> bool:
        """Test TTS request WITH valid JWT token (should work)"""
        payload = {
            "input": {
                "method": "POST",
                "path": "/tts",
                "headers": {
                    "Authorization": f"Bearer {jwt_token}"
                },
                "body": {
                    "text": "This should work with valid JWT!",
                    "model": "kokkoro"
                }
            }
        }
        
        result = self._make_request("runsync", payload, "TTS request WITH valid JWT token")
        
        # This should either work (200) or fail due to TTS engine being unavailable (but auth should pass)
        return result.get("security_status") in ["LOGIN_SUCCESS", "UNEXPECTED"] and result.get("status_code") != 401
    
    def test_models_without_jwt(self) -> bool:
        """Test models endpoint without JWT (should be rejected)"""
        payload = {
            "input": {
                "method": "GET",
                "path": "/models"
                # No Authorization header
            }
        }
        
        result = self._make_request("runsync", payload, "Models list WITHOUT JWT token")
        return result.get("security_status") == "SECURE"
    
    def test_models_with_jwt(self, jwt_token: str) -> bool:
        """Test models endpoint with JWT (should work)"""
        payload = {
            "input": {
                "method": "GET",
                "path": "/models",
                "headers": {
                    "Authorization": f"Bearer {jwt_token}"
                }
            }
        }
        
        result = self._make_request("runsync", payload, "Models list WITH valid JWT token")
        return result.get("security_status") in ["LOGIN_SUCCESS", "UNEXPECTED"] and result.get("status_code") != 401
    
    def test_health_check(self) -> bool:
        """Test health check (should work without JWT - public endpoint)"""
        payload = {
            "input": {
                "method": "GET",
                "path": "/health"
            }
        }
        
        result = self._make_request("runsync", payload, "Health check (public endpoint)")
        return result.get("security_status") in ["LOGIN_SUCCESS", "UNEXPECTED"] and result.get("status_code") != 401
    
    def run_comprehensive_security_test(self):
        """Run complete security test suite"""
        print("🛡️  RUNPOD TTS SECURITY TEST SUITE")
        print("=" * 60)
        print(f"🎯 Testing endpoint: {self.endpoint_url}")
        print("=" * 60)
        
        results = []
        
        # Test 1: Health check (should work - public)
        print("\n📋 TEST 1: Health Check (Public)")
        health_ok = self.test_health_check()
        results.append(("Health Check", health_ok))
        
        # Test 2: TTS without JWT (should be rejected)
        print("\n📋 TEST 2: TTS without JWT (Should be REJECTED)")
        tts_no_jwt_blocked = self.test_unauthorized_tts_request()
        results.append(("TTS without JWT blocked", tts_no_jwt_blocked))
        
        # Test 3: TTS with invalid JWT (should be rejected)
        print("\n📋 TEST 3: TTS with invalid JWT (Should be REJECTED)")
        tts_invalid_jwt_blocked = self.test_invalid_jwt_token()
        results.append(("TTS with invalid JWT blocked", tts_invalid_jwt_blocked))
        
        # Test 4: Models without JWT (should be rejected)
        print("\n📋 TEST 4: Models without JWT (Should be REJECTED)")
        models_no_jwt_blocked = self.test_models_without_jwt()
        results.append(("Models without JWT blocked", models_no_jwt_blocked))
        
        # Test 5: Login flow
        print("\n📋 TEST 5: Login Flow")
        jwt_token = self.test_login_flow()
        login_works = jwt_token is not None
        results.append(("Login works", login_works))
        
        if jwt_token:
            print(f"🎫 JWT Token received: {jwt_token[:50]}...")
            
            # Test 6: TTS with valid JWT (should work or fail gracefully)
            print("\n📋 TEST 6: TTS with valid JWT (Should WORK)")
            tts_with_jwt_works = self.test_authorized_tts_request(jwt_token)
            results.append(("TTS with valid JWT works", tts_with_jwt_works))
            
            # Test 7: Models with valid JWT (should work)
            print("\n📋 TEST 7: Models with valid JWT (Should WORK)")
            models_with_jwt_works = self.test_models_with_jwt(jwt_token)
            results.append(("Models with valid JWT works", models_with_jwt_works))
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 SECURITY TEST SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status}: {test_name}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🛡️  ✅ ALL SECURITY TESTS PASSED!")
            print("🔒 Your RunPod TTS deployment is properly secured")
        else:
            print("🚨 ❌ SECURITY ISSUES DETECTED!")
            print("🔥 Your RunPod deployment may not be properly secured")
        
        print("\n🔑 SECURITY REQUIREMENTS:")
        print("   ✅ TTS endpoints should REJECT requests without JWT")
        print("   ✅ TTS endpoints should REJECT requests with invalid JWT")
        print("   ✅ TTS endpoints should ACCEPT requests with valid JWT")
        print("   ✅ Public endpoints (health) should work without JWT")
        print("   ✅ Login should provide valid JWT tokens")
        
        return all_passed

def main():
    """Main function to run security tests"""
    print("🔐 RunPod TTS Security Tester")
    print("=" * 40)
    
    # Configuration - UPDATE THESE WITH YOUR RUNPOD DETAILS
    ENDPOINT_URL = input("Enter your RunPod endpoint URL (e.g., https://api.runpod.ai/v2/your-endpoint-id): ").strip()
    API_KEY = input("Enter your RunPod API key: ").strip()
    
    if not ENDPOINT_URL or not API_KEY:
        print("❌ Both endpoint URL and API key are required!")
        return
    
    # Initialize tester
    tester = RunPodSecurityTester(ENDPOINT_URL, API_KEY)
    
    # Run security tests
    print(f"\n🚀 Starting security tests for: {ENDPOINT_URL}")
    
    try:
        all_secure = tester.run_comprehensive_security_test()
        
        if all_secure:
            print("\n🎉 CONGRATULATIONS!")
            print("🛡️  Your RunPod TTS deployment is SECURE!")
        else:
            print("\n⚠️  WARNING!")
            print("🚨 Your RunPod TTS deployment has SECURITY ISSUES!")
            print("\n💡 NEXT STEPS:")
            print("   1. Update your RunPod handler with the secure version")
            print("   2. Redeploy your RunPod endpoint")
            print("   3. Run this test again to verify")
        
    except Exception as e:
        print(f"\n🔥 Error during security testing: {e}")
        print("Please check your endpoint URL and API key")

# Quick test function for known endpoint
def quick_test():
    """Quick test with predefined values (for development)"""
    # REPLACE THESE WITH YOUR ACTUAL VALUES
    ENDPOINT_URL = "https://api.runpod.ai/v2/n89xd1t4pl71jf"  # Your endpoint from the logs
    API_KEY = "YOUR_RUNPOD_API_KEY_HERE"
    
    if API_KEY == "YOUR_RUNPOD_API_KEY_HERE":
        print("❌ Please update the API_KEY in quick_test() function")
        return
    
    print("🚀 Running quick security test...")
    
    tester = RunPodSecurityTester(ENDPOINT_URL, API_KEY)
    tester.run_comprehensive_security_test()

# Demonstration of what secure vs insecure responses look like
def show_expected_responses():
    """Show what responses should look like for secure vs insecure deployments"""
    print("\n📚 EXPECTED RESPONSES GUIDE")
    print("=" * 50)
    
    print("\n✅ SECURE Response (TTS without JWT):")
    secure_response = {
        "output": {
            "statusCode": 401,
            "body": {
                "error": "Authentication required",
                "message": "You must provide a valid JWT token to access TTS services"
            }
        }
    }
    print(json.dumps(secure_response, indent=2))
    
    print("\n🚨 INSECURE Response (TTS without JWT - THIS IS BAD!):")
    insecure_response = {
        "output": {
            "statusCode": 200,
            "body": {
                "audio_url": "some-audio-file.wav",
                "message": "Speech generated successfully",
                "model_used": "kokkoro"
            }
        }
    }
    print(json.dumps(insecure_response, indent=2))
    
    print("\n✅ SECURE Response (TTS with valid JWT):")
    secure_auth_response = {
        "output": {
            "statusCode": 200,
            "body": {
                "audio_url": "some-audio-file.wav",
                "message": "Speech generated successfully using kokkoro",
                "model_used": "kokkoro",
                "user": "testuser"
            }
        }
    }
    print(json.dumps(secure_auth_response, indent=2))

# Manual curl commands for testing
def show_curl_commands():
    """Show curl commands for manual testing"""
    print("\n🖥️  MANUAL CURL TESTING COMMANDS")
    print("=" * 50)
    
    print("\n1. Test TTS WITHOUT JWT (should return 401):")
    print('''curl -X POST "YOUR_RUNPOD_ENDPOINT/runsync" \\
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": {
      "method": "POST",
      "path": "/tts",
      "body": {
        "text": "This should be blocked",
        "model": "kokkoro"
      }
    }
  }' ''')
    
    print("\n2. Login to get JWT token:")
    print('''curl -X POST "YOUR_RUNPOD_ENDPOINT/runsync" \\
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": {
      "method": "POST",
      "path": "/auth/login",
      "body": {
        "username": "testuser",
        "password": "secret"
      }
    }
  }' ''')
    
    print("\n3. Test TTS WITH JWT (use token from step 2):")
    print('''curl -X POST "YOUR_RUNPOD_ENDPOINT/runsync" \\
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": {
      "method": "POST",
      "path": "/tts",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN_FROM_LOGIN"
      },
      "body": {
        "text": "This should work with JWT",
        "model": "kokkoro"
      }
    }
  }' ''')

if __name__ == "__main__":
    import sys
    
    print("🔐 RunPod TTS Security Testing Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            quick_test()
        elif command == "examples":
            show_expected_responses()
        elif command == "curl":
            show_curl_commands()
        else:
            print("Unknown command. Use: python runpod_security_test.py [quick|examples|curl]")
    else:
        main()
    
    print("\n🎯 SECURITY CHECKLIST:")
    print("   🔒 TTS requests without JWT should return 401")
    print("   🔒 TTS requests with invalid JWT should return 401") 
    print("   🔒 TTS requests with valid JWT should work (or fail gracefully)")
    print("   🔓 Health check should work without JWT")
    print("   🔓 Login should provide valid JWT tokens")
    
    print("\n💡 TROUBLESHOOTING:")
    print("   • If tests fail, update your RunPod handler with the secure version")
    print("   • Make sure you've redeployed your RunPod endpoint")
    print("   • Check RunPod logs for authentication errors")
    print("   • Verify your JWT_SECRET_KEY environment variable is set")

# Example usage and testing data
EXAMPLE_TESTS = {
    "secure_responses": {
        "tts_without_jwt": {"statusCode": 401, "body": {"error": "Authentication required"}},
        "tts_with_invalid_jwt": {"statusCode": 401, "body": {"error": "Authentication required"}},
        "models_without_jwt": {"statusCode": 401, "body": {"error": "Authentication required"}},
        "login_success": {"statusCode": 200, "body": {"access_token": "...", "token_type": "bearer"}},
        "tts_with_jwt": {"statusCode": 200, "body": {"audio_url": "...", "user": "testuser"}},
        "health_check": {"statusCode": 200, "body": {"status": "healthy"}}
    }
}
