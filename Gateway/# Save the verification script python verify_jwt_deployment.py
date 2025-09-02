#!/usr/bin/env python3
"""
JWT Deployment Verification Script
This will test if your RunPod deployment actually enforces JWT authentication
"""

import requests
import json
import os

def test_jwt_enforcement(endpoint_url, api_key):
    """Test if JWT authentication is properly enforced"""
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    print("🔍 Testing JWT Authentication Enforcement")
    print("=" * 50)
    
    # Test 1: Health check (should work without JWT)
    print("\n1. Health Check (should work without JWT):")
    health_payload = {"input": {"action": "health"}}
    
    try:
        response = requests.post(endpoint_url, json=health_payload, headers=headers)
        result = response.json()
        
        if result.get('status') == 'healthy':
            print("   ✅ Health check works")
            print(f"   JWT Auth Enabled: {result.get('jwt_auth_enabled', 'Unknown')}")
            print(f"   JWT Strict Mode: {result.get('jwt_auth_strict', 'Unknown')}")
            print(f"   Version: {result.get('gateway_version', 'Unknown')}")
        else:
            print(f"   ❌ Health check failed: {result}")
            
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: TTS WITHOUT JWT (should FAIL if JWT is enforced)
    print("\n2. TTS Request WITHOUT JWT (should FAIL if JWT is enforced):")
    no_jwt_payload = {
        "input": {
            "text": "This should fail if JWT is enforced",
            "engine": "kokkoro"
        }
    }
    
    try:
        response = requests.post(endpoint_url, json=no_jwt_payload, headers=headers)
        result = response.json()
        
        if result.get('error') and 'token' in result.get('error', '').lower():
            print("   ✅ CORRECTLY REJECTED - JWT is enforced!")
            print(f"   Error: {result['error']}")
            jwt_enforced = True
        elif result.get('success') or result.get('result'):
            print("   ❌ INCORRECTLY ALLOWED - JWT is NOT enforced!")
            print("   🚨 Your deployment is generating speech without authentication!")
            jwt_enforced = False
        else:
            print(f"   ⚠️ Unexpected response: {result}")
            jwt_enforced = False
            
    except Exception as e:
        print(f"   ❌ TTS request error: {e}")
        return False
    
    # Test 3: Generate JWT token
    print("\n3. Generate JWT Token:")
    token_payload = {
        "input": {
            "action": "generate_token",
            "user_id": "verification_test_user"
        }
    }
    
    jwt_token = None
    try:
        response = requests.post(endpoint_url, json=token_payload, headers=headers)
        result = response.json()
        
        if result.get('success') and result.get('token'):
            jwt_token = result['token']
            print("   ✅ Token generated successfully")
            print(f"   Token: {jwt_token[:50]}...")
        else:
            print(f"   ❌ Token generation failed: {result}")
            
    except Exception as e:
        print(f"   ❌ Token generation error: {e}")
    
    # Test 4: TTS WITH JWT (should work if JWT is properly implemented)
    if jwt_token:
        print("\n4. TTS Request WITH JWT (should work):")
        with_jwt_payload = {
            "input": {
                "jwt_token": jwt_token,
                "text": "This should work with valid JWT token",
                "engine": "kokkoro"
            }
        }
        
        try:
            response = requests.post(endpoint_url, json=with_jwt_payload, headers=headers)
            result = response.json()
            
            if result.get('success') or result.get('result'):
                print("   ✅ TTS with JWT works correctly")
                print(f"   User ID: {result.get('user_id', 'Unknown')}")
                print(f"   Authenticated: {result.get('authenticated', 'Unknown')}")
            else:
                print(f"   ❌ TTS with JWT failed: {result}")
                
        except Exception as e:
            print(f"   ❌ TTS with JWT error: {e}")
    
    # Final assessment
    print("\n" + "=" * 50)
    if jwt_enforced:
        print("🎉 JWT AUTHENTICATION IS PROPERLY ENFORCED!")
        print("✅ Your deployment is secure - TTS requires valid JWT tokens")
    else:
        print("🚨 JWT AUTHENTICATION IS NOT ENFORCED!")
        print("❌ Your deployment is NOT secure - anyone can generate speech")
        print("🔧 You need to replace your rp_handler.py with the corrected version")
    
    return jwt_enforced

def main():
    print("🔐 JWT Authentication Verification")
    print("=" * 50)
    
    # Get configuration
    endpoint_url = input("Enter your RunPod endpoint URL: ").strip()
    if not endpoint_url:
        endpoint_url = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
    
    api_key = input("Enter your RunPod API key: ").strip()
    if not api_key:
        print("❌ RunPod API key is required")
        return
    
    # Run verification
    is_secure = test_jwt_enforcement(endpoint_url, api_key)
    
    if not is_secure:
        print("\n🔧 HOW TO FIX:")
        print("1. Replace your current rp_handler.py with the corrected version")
        print("2. Rebuild and redeploy your Docker image")
        print("3. Update your RunPod endpoint with the new image")
        print("4. Make sure JWT_SECRET_KEY environment variable is set")
        
        print("\n📋 Quick Fix Commands:")
        print("# Replace the handler file")
        print("cp corrected_rp_handler.py rp_handler.py")
        print("")
        print("# Rebuild and push")
        print("docker build -t your-image-name .")
        print("docker push your-image-name")
        print("")
        print("# Update RunPod endpoint with new image")

if __name__ == "__main__":
    main()
