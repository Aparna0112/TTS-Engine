#!/usr/bin/env python3
"""
Filename: test_gateway.py
Test script for TTS Gateway on RunPod

Usage:
  python test_gateway.py

Environment Variables Required:
  - RUNPOD_API_KEY: Your RunPod API key
  - TTS_GATEWAY_ENDPOINT: Your gateway endpoint URL

Example:
  export RUNPOD_API_KEY="your_api_key_here"
  export TTS_GATEWAY_ENDPOINT="https://api.runpod.ai/v2/your_gateway_endpoint_id"
  python test_gateway.py
"""

import requests
import json
import time
import os
from typing import Dict, Any

class TTSGatewayTester:
    def __init__(self, endpoint_url: str, api_key: str):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        print("🏥 Testing health check...")
        
        payload = {
            "input": {
                "action": "health"
            }
        }
        
        try:
            response = requests.post(
                f"{self.endpoint_url}/runsync",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health check passed: {result}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_tts_request(self, engine: str, text: str) -> bool:
        """Test a TTS request"""
        print(f"🎵 Testing TTS with {engine} engine...")
        
        payload = {
            "input": {
                "text": text,
                "engine": engine,
                "voice": "default",
                "speed": 1.0
            }
        }
        
        try:
            response = requests.post(
                f"{self.endpoint_url}/runsync",
                json=payload,
                headers=self.headers,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result:
                    print(f"❌ TTS request failed: {result['error']}")
                    return False
                else:
                    print(f"✅ TTS request successful: {engine}")
                    print(f"   Response keys: {list(result.keys())}")
                    return True
            else:
                print(f"❌ TTS request failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ TTS request error: {e}")
            return False
    
    def test_async_request(self, engine: str, text: str) -> bool:
        """Test an async TTS request"""
        print(f"⚡ Testing async TTS with {engine} engine...")
        
        payload = {
            "input": {
                "text": text,
                "engine": engine,
                "voice": "default"
            }
        }
        
        try:
            # Submit async request
            response = requests.post(
                f"{self.endpoint_url}/run",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('id')
                print(f"   Job submitted: {job_id}")
                
                # Poll for results
                max_polls = 30
                for i in range(max_polls):
                    status_response = requests.get(
                        f"{self.endpoint_url}/status/{job_id}",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        status = status_result.get('status')
                        
                        if status == 'COMPLETED':
                            print(f"✅ Async TTS completed successfully")
                            return True
                        elif status == 'FAILED':
                            print(f"❌ Async TTS failed: {status_result}")
                            return False
                        elif status in ['IN_QUEUE', 'IN_PROGRESS']:
                            print(f"   Status: {status} (poll {i+1}/{max_polls})")
                            time.sleep(2)
                        else:
                            print(f"   Unknown status: {status}")
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        return False
                
                print(f"❌ Async request timed out after {max_polls} polls")
                return False
            else:
                print(f"❌ Async request failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Async request error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting TTS Gateway Tests")
        print("=" * 50)
        
        results = []
        
        # Test health check
        results.append(self.test_health_check())
        
        # Test sync TTS requests
        results.append(self.test_tts_request("kokkoro", "Hello from Kokkoro TTS engine"))
        results.append(self.test_tts_request("chatterbox", "Hello from Chatterbox TTS engine"))
        
        # Test async TTS requests
        results.append(self.test_async_request("kokkoro", "Async test with Kokkoro"))
        
        # Test error handling
        print("🧪 Testing error handling...")
        payload = {
            "input": {
                "engine": "invalid_engine",
                "text": "This should fail"
            }
        }
        
        try:
            response = requests.post(
                f"{self.endpoint_url}/runsync",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result:
                    print("✅ Error handling works correctly")
                    results.append(True)
                else:
                    print("❌ Error handling failed - should have returned error")
                    results.append(False)
            else:
                print(f"❌ Error handling test failed: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ Error handling test error: {e}")
            results.append(False)
        
        # Summary
        print("\n" + "=" * 50)
        passed = sum(results)
        total = len(results)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your TTS Gateway is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the logs above for details.")
        
        return passed == total

def main():
    # Configuration
    endpoint_url = os.getenv('TTS_GATEWAY_ENDPOINT', 'https://api.runpod.ai/v2/YOUR_GATEWAY_ENDPOINT_ID')
    api_key = os.getenv('RUNPOD_API_KEY')
    
    if not api_key:
        print("❌ Please set RUNPOD_API_KEY environment variable")
        return
    
    if 'YOUR_GATEWAY_ENDPOINT_ID' in endpoint_url:
        print("❌ Please update TTS_GATEWAY_ENDPOINT with your actual endpoint URL")
        return
    
    print(f"Testing endpoint: {endpoint_url}")
    
    # Run tests
    tester = TTSGatewayTester(endpoint_url, api_key)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
