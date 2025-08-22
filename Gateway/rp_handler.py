#!/usr/bin/env python3
"""
RunPod Handler for TTS Gateway
This file should be named: rp_handler.py

Based on your repository structure, this replaces your existing gateway handler
to properly work with RunPod serverless.
"""

import runpod
import requests
import os
import time
import logging
import json
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/h38h5e6h89x9rv/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/q9z7mo11f4vnq4/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# Request settings
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))

class TTSGateway:
    def __init__(self):
        self.endpoints = {
            'kokkoro': KOKKORO_ENDPOINT,
            'chatterbox': CHATTERBOX_ENDPOINT
        }
        
        # Validate configuration
        if not RUNPOD_API_KEY:
            logger.error("RUNPOD_API_KEY not set!")
            raise ValueError("RUNPOD_API_KEY environment variable is required")
        
        logger.info("🚀 TTS Gateway initialized")
        logger.info(f"📍 Available engines: {list(self.endpoints.keys())}")
        logger.info(f"🔗 Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"🔗 Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        
    def validate_input(self, job_input: Dict[str, Any]) -> tuple[bool, str]:
        """Validate input parameters"""
        if not isinstance(job_input, dict):
            return False, "Input must be a dictionary"
        
        # Handle health check
        if job_input.get('action') == 'health':
            return True, ""
        
        # Validate required fields
        if not job_input.get('text'):
            return False, "Missing required parameter: 'text'"
        
        text = job_input['text']
        if not isinstance(text, str) or len(text.strip()) == 0:
            return False, "Text must be a non-empty string"
        
        if len(text) > 10000:
            return False, "Text too long (max 10000 characters)"
        
        # Validate engine
        engine = job_input.get('engine', 'kokkoro').lower()
        if engine not in self.endpoints:
            return False, f"Unsupported engine: {engine}. Available: {list(self.endpoints.keys())}"
        
        return True, ""
    
    def call_tts_endpoint(self, endpoint_url: str, payload: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Call TTS endpoint with retry logic"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {RUNPOD_API_KEY}'
        }
        
        request_payload = {"input": payload}
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"🔄 Job {job_id}: Calling {endpoint_url} (attempt {attempt + 1}/{MAX_RETRIES})")
                
                response = requests.post(
                    endpoint_url,
                    json=request_payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                logger.info(f"📊 Job {job_id}: Response status {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"✅ Job {job_id}: Successfully received response")
                        return {
                            "success": True,
                            "data": result,
                            "endpoint": endpoint_url,
                            "attempt": attempt + 1
                        }
                    except json.JSONDecodeError:
                        logger.error(f"❌ Job {job_id}: Invalid JSON response")
                        if attempt == MAX_RETRIES - 1:
                            return {
                                "success": False,
                                "error": "Invalid JSON response from TTS endpoint",
                                "raw_response": response.text[:500]
                            }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                    logger.error(f"❌ Job {job_id}: {error_msg}")
                    
                    if attempt == MAX_RETRIES - 1:
                        return {
                            "success": False,
                            "error": error_msg,
                            "status_code": response.status_code
                        }
                    
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Job {job_id}: Timeout on attempt {attempt + 1}")
                if attempt == MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": f"Request timeout after {REQUEST_TIMEOUT}s",
                        "endpoint": endpoint_url
                    }
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"🔌 Job {job_id}: Connection error on attempt {attempt + 1}")
                if attempt == MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": "Connection error to TTS endpoint",
                        "endpoint": endpoint_url
                    }
                    
            except Exception as e:
                logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": f"Unexpected error: {str(e)}",
                        "endpoint": endpoint_url
                    }
            
            # Wait before retry (exponential backoff)
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.info(f"⏳ Job {job_id}: Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }

# Initialize gateway instance
gateway = TTSGateway()

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod handler function
    This is the entry point for all requests
    """
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        logger.info(f"🎯 Processing job {job_id}")
        
        job_input = job.get('input', {})
        
        # Log the input for debugging
        logger.info(f"📝 Job {job_id} input: {json.dumps(job_input, indent=2)}")
        
        # Handle health check
        if job_input.get('action') == 'health':
            logger.info(f"💊 Job {job_id}: Health check requested")
            return {
                "status": "healthy",
                "gateway_version": "1.0.0",
                "endpoints": list(gateway.endpoints.keys()),
                "timestamp": time.time(),
                "job_id": job_id
            }
        
        # Validate input
        is_valid, error_msg = gateway.validate_input(job_input)
        if not is_valid:
            logger.error(f"❌ Job {job_id}: Validation failed: {error_msg}")
            return {
                "error": error_msg,
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        # Extract parameters
        text = job_input['text']
        engine = job_input.get('engine', 'kokkoro').lower()
        
        logger.info(f"🎵 Job {job_id}: Processing with {engine} engine")
        logger.info(f"📄 Job {job_id}: Text length: {len(text)} characters")
        
        # Prepare payload for TTS endpoint
        tts_payload = {
            'text': text,
            'voice': job_input.get('voice', 'default'),
            'speed': job_input.get('speed', 1.0)
        }
        
        # Add engine-specific parameters
        if engine == 'kokkoro':
            tts_payload.update({
                'language': job_input.get('language', 'en'),
                'speaker_id': job_input.get('speaker_id', 0)
            })
        elif engine == 'chatterbox':
            tts_payload.update({
                'model': job_input.get('model', 'default'),
                'format': job_input.get('format', 'wav')
            })
        
        # Call the TTS endpoint
        endpoint_url = gateway.endpoints[engine]
        result = gateway.call_tts_endpoint(endpoint_url, tts_payload, job_id)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            logger.info(f"✅ Job {job_id}: Completed successfully in {processing_time:.2f}s")
            return {
                "success": True,
                "job_id": job_id,
                "engine": engine,
                "text_length": len(text),
                "processing_time": processing_time,
                "result": result['data'],
                "endpoint_used": endpoint_url,
                "attempts": result.get('attempt', 1)
            }
        else:
            logger.error(f"❌ Job {job_id}: TTS processing failed: {result['error']}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "engine": engine,
                "processing_time": processing_time,
                "endpoint_used": endpoint_url,
                "details": result
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Internal gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time
        }

# Test function for local development
def test_handler():
    """Test the handler locally"""
    print("🧪 Testing TTS Gateway Handler locally...")
    
    # Test health check
    health_job = {
        "id": "test_health",
        "input": {"action": "health"}
    }
    
    print("Testing health check...")
    result = handler(health_job)
    print(f"Health check result: {json.dumps(result, indent=2)}")
    
    # Test TTS request
    tts_job = {
        "id": "test_tts",
        "input": {
            "text": "Hello, this is a test of the TTS gateway.",
            "engine": "kokkoro",
            "voice": "default"
        }
    }
    
    print("\nTesting TTS request...")
    result = handler(tts_job)
    print(f"TTS result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    # Check if running in test mode
    import sys
    
    if "--test" in sys.argv:
        test_handler()
    else:
        # Start RunPod serverless worker
        logger.info("🚀 Starting TTS Gateway RunPod Serverless Worker")
        logger.info(f"🔧 Configuration:")
        logger.info(f"   - Request timeout: {REQUEST_TIMEOUT}s")
        logger.info(f"   - Max retries: {MAX_RETRIES}")
        logger.info(f"   - Available engines: {list(gateway.endpoints.keys())}")
        
        # This is the critical line that starts the RunPod serverless worker
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
