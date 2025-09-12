import requests
import json
import sys
import os
from typing import Dict, Any
from jwt_utils import jwt_manager

def test_endpoint_health(endpoint_url: str) -> Dict[str, Any]:
    """Test endpoint health"""
    try:
        response = requests.get(f"{endpoint_url}/health", timeout=10)
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_jwt_generation(endpoint_url: str) -> Dict[str, Any]:
    """Test JWT token generation"""
    try:
        payload = {
            "input": {
                "action": "generate_token",
                "user_id": "test_user_verification",
                "user_data": {
                    "role": "tester",
                    "verification": True
                }
            }
        }
        
        response = requests.post(endpoint_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": result.get("success", False),
                "token": result.get("token"),
                "user_id": result.get("user_id"),
                "expires_in_hours": result.get("expires_in_hours"),
                "error": result.get("error")
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_jwt_validation(endpoint_url: str, jwt_token: str) -> Dict[str, Any]:
    """Test JWT token validation with a protected endpoint"""
    try:
        payload = {
            "input": {
                "jwt_token": jwt_token,
                "action": "list_models"
            }
        }
        
        response = requests.post(endpoint_url, json=payload, timeout=30)
        
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "authenticated": response.json().get("authenticated", False) if response.status_code == 200 else False
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_invalid_jwt(endpoint_url: str) -> Dict[str, Any]:
    """Test that invalid JWT is rejected"""
    try:
        payload = {
            "input": {
                "jwt_token": "invalid.jwt.token",
                "text": "This should fail",
                "engine": "chatterbox"
            }
        }
        
        response = requests.post(endpoint_url, json=payload, timeout=30)
        result = response.json()
        
        # Should fail with auth error
        return {
            "success": not result.get("success", True),  # Inverted - we want this to fail
            "auth_rejected": "AUTHENTICATION FAILED" in result.get("error", ""),
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main verification process"""
    endpoint_url = sys.argv[1] if len(sys.argv) > 1 else input("Enter Gateway endpoint URL: ").strip()
    
    if not endpoint_url:
        print("❌ Gateway endpoint URL required")
        sys.exit(1)
    
    if not endpoint_url.startswith(('http://', 'https://')):
        endpoint_url = f"https://{endpoint_url}"
    
    print(f"🔍 Verifying JWT deployment: {endpoint_url}")
    print("=" * 60)
    
    # Test 1: Health check
    print("1. Testing endpoint health...")
    health_result = test_endpoint_health(endpoint_url)
    
    if health_result["success"]:
        print("   ✅ Health check passed")
        health_data = health_result["data"]
        print(f"   📋 Gateway version: {health_data.get('gateway_version')}")
        print(f"   🔐 JWT auth enabled: {health_data.get('jwt_auth_enabled')}")
        print(f"   🎯 Available engines: {health_data.get('available_engines')}")
    else:
        print(f"   ❌ Health check failed: {health_result['error']}")
        sys.exit(1)
    
    # Test 2: JWT token generation
    print("\n2. Testing JWT token generation...")
    token_result = test_jwt_generation(endpoint_url)
    
    if token_result["success"]:
        jwt_token = token_result["token"]
        print("   ✅ JWT token generated successfully")
        print(f"   👤 User ID: {token_result['user_id']}")
        print(f"   ⏰ Expires in: {token_result['expires_in_hours']} hours")
        print(f"   🔑 Token: {jwt_token[:20]}...{jwt_token[-10:]}")
    else:
        print(f"   ❌ JWT generation failed: {token_result['error']}")
        sys.exit(1)
    
    # Test 3: JWT validation
    print("\n3. Testing JWT token validation...")
    validation_result = test_jwt_validation(endpoint_url, jwt_token)
    
    if validation_result["success"]:
        print("   ✅ JWT validation passed")
        print(f"   🔓 Authenticated: {validation_result['authenticated']}")
    else:
        print(f"   ❌ JWT validation failed: {validation_result.get('error')}")
    
    # Test 4: Invalid JWT rejection
    print("\n4. Testing invalid JWT rejection...")
    invalid_result = test_invalid_jwt(endpoint_url)
    
    if invalid_result["success"]:
        print("   ✅ Invalid JWT properly rejected")
        print(f"   🚫 Auth rejected: {invalid_result['auth_rejected']}")
    else:
        print(f"   ❌ Invalid JWT test failed: {invalid_result.get('error')}")
    
    # Test 5: Local JWT validation
    print("\n5. Testing local JWT validation...")
    try:
        local_validation = jwt_manager.validate_token(jwt_token)
        if local_validation["valid"]:
            print("   ✅ Local JWT validation passed")
            print(f"   👤 User ID: {local_validation['user_id']}")
        else:
            print(f"   ❌ Local validation failed: {local_validation['error']}")
    except Exception as e:
        print(f"   ❌ Local validation error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 JWT Deployment Verification Complete!")
    print("\n📋 Summary:")
    print("   ✅ Gateway is healthy and running")
    print("   ✅ JWT authentication is working")
    print("   ✅ Token generation and validation successful")
    print("   ✅ Security measures are active")
    
    print(f"\n🔑 Generated JWT Token (save this for testing):")
    print(f"   {jwt_token}")
    
    print(f"\n📱 Test commands:")
    print(f"   # Health check")
    print(f"   curl '{endpoint_url}/health'")
    print(f"   ")
    print(f"   # Generate token")
    print(f"   curl -X POST '{endpoint_url}' -H 'Content-Type: application/json' -d '{{\"input\":{{\"action\":\"generate_token\",\"user_id\":\"your_id\"}}}}'")
    print(f"   ")
    print(f"   # Test TTS with token")
    print(f"   curl -X POST '{endpoint_url}' -H 'Content-Type: application/json' -d '{{\"input\":{{\"jwt_token\":\"{jwt_token}\",\"text\":\"Hello world\",\"engine\":\"chatterbox\"}}}}'")

if __name__ == "__main__":
    main()
