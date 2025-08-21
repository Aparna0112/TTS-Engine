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
    print(f"[Gateway] Received event: {event}")
    try:
        # Extract input data
        input_data = event.get('input', {})
        text = input_data.get('text', '').strip()
        model = input_data.get('model', 'kokkoro').lower()

        # Validation
        if not text:
            print("[Gateway] Error: No text provided")
            return {
                "error": "No text provided",
                "details": "Please provide 'text' in the input"
            }

        # Get environment variables
        kokkoro_endpoint = os.getenv('KOKKORO_ENDPOINT')
        chatterbox_endpoint = os.getenv('CHATTERBOX_ENDPOINT')

        if not kokkoro_endpoint and not chatterbox_endpoint:
            print("[Gateway] Error: No TTS endpoints configured")
            return {
                "error": "No TTS endpoints configured",
                "details": "Check KOKKORO_ENDPOINT and CHATTERBOX_ENDPOINT environment variables"
            }

        print(f"[Gateway] Processing text: '{text}' with model: '{model}'")
        print(f"[Gateway] KOKKORO_ENDPOINT: {kokkoro_endpoint}")
        print(f"[Gateway] CHATTERBOX_ENDPOINT: {chatterbox_endpoint}")

        # Route to appropriate TTS service
        if model in ['kokkoro', 'kokoro']:
            if not kokkoro_endpoint:
                print("[Gateway] Error: Kokkoro endpoint not configured")
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
                print("[Gateway] Error: Chatterbox endpoint not configured")
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
            print(f"[Gateway] Error: Unknown model '{model}'")
            return {
                "error": f"Unknown model: {model}",
                "available_models": ["kokkoro", "chatterbox"]
            }

        print(f"[Gateway] Calling endpoint: {endpoint}")
        print(f"[Gateway] Payload: {json.dumps(payload, indent=2)}")

        # Make request to TTS service
        headers = {
            'Content-Type': 'application/json'
        }
        api_key = os.getenv("RUNPOD_API_KEY", "")
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        start_time = time.time()
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=300  # 5 minutes timeout
            )
        except requests.exceptions.Timeout:
            print("[Gateway] Error: Request timeout")
            return {
                "error": "Request timeout",
                "details": "TTS service took too long to respond"
            }
        except requests.exceptions.ConnectionError:
            print("[Gateway] Error: Connection error")
            return {
                "error": "Connection error",
                "details": "Could not connect to TTS service"
            }

        elapsed_time = time.time() - start_time
        print(f"[Gateway] TTS service responded in {elapsed_time:.2f} seconds")
        print(f"[Gateway] Response status: {response.status_code}")

        # Handle response
        if response.status_code == 200:
            try:
                result = response.json()
            except Exception as e:
                print(f"[Gateway] Error parsing JSON: {str(e)}")
                return {
                    "error": "Invalid JSON from TTS service",
                    "details": str(e),
                    "response_text": response.text
                }
            print(f"[Gateway] TTS service response: {json.dumps(result, indent=2)}")
            return {
                "output": result.get('output', result),
                "model_used": model,
                "processing_time": elapsed_time,
                "status": "success"
            }
        else:
            print(f"[Gateway] TTS service error: {response.text}")
            return {
                "error": f"TTS service error: {response.status_code}",
                "details": response.text,
                "model": model
            }

    except Exception as e:
        print(f"[Gateway] Unexpected error: {str(e)}")
        return {
            "error": "Internal gateway error",
            "details": str(e)
        }

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

if __name__ == "__main__":
    print("[Gateway] Starting TTS Gateway...")
    print(f"[Gateway] KOKKORO_ENDPOINT: {os.getenv('KOKKORO_ENDPOINT')}")
    print(f"[Gateway] CHATTERBOX_ENDPOINT: {os.getenv('CHATTERBOX_ENDPOINT')}")
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": True
    })
