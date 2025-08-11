import requests
import json

def test_gateway(base_url):
    print(f"Testing gateway at {base_url}")
    
    # Test health
    response = requests.get(f"{base_url}/health")
    print(f"Health check: {response.json()}")
    
    # Test models list
    response = requests.get(f"{base_url}/models")
    print(f"Available models: {response.json()}")
    
    # Test TTS synthesis
    tts_request = {
        "text": "Hello, this is a test of the TTS system.",
        "model": "kokkoro",
        "voice": "default",
        "speed": 1.0
    }
    
    response = requests.post(f"{base_url}/synthesize", json=tts_request)
    if response.status_code == 200:
        print("TTS synthesis successful!")
        print(response.json())
    else:
        print(f"TTS synthesis failed: {response.text}")

if __name__ == "__main__":
    # Test local deployment
    test_gateway("http://localhost:8000")
    
    # Test RunPod endpoint (replace with your actual endpoint)
    # test_gateway("https://your-runpod-endpoint.runpod.net")
