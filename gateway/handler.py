import runpod
import requests
import os
import json
import time
from typing import Dict, Any

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    TTS Gateway Handler for RunPod Serverless
    Routes requests to appropriate TTS services (Kokkoro or Chatterbox)
    """
    print(f"Gateway received event: {event}")
    
    try:
        # Extract input data
        input_data = event.get('input', {})
        text = input_data.get('text', '').strip()
        model = input_data.get('model', 'kokkoro').lower()
        
        # Validation
        if not text:
            return {
                "error": "No text provided",
                "details": "Please provide 'text' in the input"
            }
        
        # Get environment variables
        kokkoro_endpoint = os.getenv('KOKKORO_ENDPOINT')
        chatterbox_endpoint = os.getenv('CHATTERBOX_ENDPOINT')
        
        print(f"Processing text: '{text}' with model: '{model}'")
        print(f"Kokkoro endpoint: {kokkoro_endpoint}")
        print(f"Chatterbox endpoint: {chatterbox_endpoint}")
        
        # Route to appropriate TTS service
        if model in ['kokkoro', 'kokoro']:
            if not kokkoro_endpoint:
                return {"error": "Kokkoro endpoint not configured"}
            
            endpoint = kokkoro_endpoint
            payload = {
                "input": {
                    "text": text,
                    "voice": input_data.get('voice', 'af_sarah'),
                    "speed": input_data.get('speed', 1.0),
                    "language": input_data.get('language', 'en-us')
                }
            }
            
        elif model in ['chatterbox', 'chat']:
            if not chatterbox_endpoint:
                return {"error": "Chatterbox endpoint not configured"}
            
            endpoint = chatterbox_endpoint
            payload = {
                "input": {
                    "text": text,
                    "voice_mode": input_data.get('voice_mode', 'predefined'),
                    "voice_id": input_data.get('voice_id', '1'),
                    "temperature": input_data.get('temperature', 0.7),
                    "speed_factor": input_data.get('speed_factor', 1.0)
                }
            }
            
        else:
            return {
                "error": f"Unknown model: {model}",
                "available_models": ["kokkoro", "chatterbox"]
            }
        
        print(f"Calling {model} endpoint: {endpoint}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Make request to TTS service
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("RUNPOD_API_KEY", "")}'
        }
        
        start_time = time.time()
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=300  # 5 minutes timeout
        )
        
        elapsed_time = time.time() - start_time
        print(f"TTS service responded in {elapsed_time:.2f} seconds")
        print(f"Response status: {response.status_code}")
        
        # Handle response
        if response.status_code == 200:
            result = response.json()
            print(f"TTS service response: {json.dumps(result, indent=2)}")
            
            # Return the result from TTS service
            return {
                "output": result.get('output', result),
                "model_used": model,
                "processing_time": elapsed_time,
                "status": "success"
            }
        else:
            print(f"TTS service error: {response.text}")
            return {
                "error": f"TTS service error: {response.status_code}",
                "details": response.text,
                "model": model
            }
            
    except requests.exceptions.Timeout:
        print("Request timeout")
        return {
            "error": "Request timeout",
            "details": "TTS service took too long to respond"
        }
        
    except requests.exceptions.ConnectionError:
        print("Connection error")
        return {
            "error": "Connection error",
            "details": "Could not connect to TTS service"
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "error": "Internal gateway error",
            "details": str(e)
        }

# Health check function
def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "gateway": "tts-gateway",
        "endpoints": {
            "kokkoro": os.getenv('KOKKORO_ENDPOINT') is not None,
            "chatterbox": os.getenv('CHATTERBOX_ENDPOINT') is not None
        }
    }

# Start the RunPod serverless handler
if __name__ == "__main__":
    print("Starting TTS Gateway...")
    print(f"Kokkoro endpoint: {os.getenv('KOKKORO_ENDPOINT')}")
    print(f"Chatterbox endpoint: {os.getenv('CHATTERBOX_ENDPOINT')}")
    
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": True
    })
