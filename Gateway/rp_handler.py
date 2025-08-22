#!/usr/bin/env python3
"""
Correct RunPod Handler for TTS Gateway
Save this file as: gateway/rp_handler.py

This file fixes the "In Queue" issue by properly implementing the RunPod serverless handler.
"""

import runpod
import requests
import os
import time
import logging
import json
from typing import Dict, Any

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

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod handler function - this processes every request
    
    Args:
        job: RunPod job object containing 'input' and 'id'
        
    Returns:
        Dictionary response that gets sent back to the client
    """
    start_time = time.time()
    job_id = job.get('id', 'unknown')
    
    try:
        # Log that we're processing a request
        logger.info(f"🎯 TTS Gateway: Processing job {job_id}")
        
        # Get the input from the job
        job_input = job.get('input', {})
        logger.info(f"📝 Job input: {json.dumps(job_input, indent=2)}")
        
        # Handle health check requests
        if job_input.get('action') == 'health':
            logger.info(f"💊 Health check requested for job {job_id}")
            return {
                "status": "healthy",
                "gateway_version": "1.0.0",
                "available_engines": ["kokkoro", "chatterbox"],
                "endpoints": {
                    "kokkoro": KOKKORO_ENDPOINT,
                    "chatterbox": CHATTERBOX_ENDPOINT
                },
                "timestamp": time.time(),
                "job_id": job_id,
                "message": "TTS Gateway is running and ready to process requests!"
            }
        
        # Validate input for TTS requests
        if not job_input.get('text'):
            logger.error(f"❌ Job {job_id}: Missing 'text' parameter")
            return {
                "error": "Missing required parameter: 'text'",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        text = job_input['text']
        engine = job_input.get('engine', 'kokkoro').lower()
        
        # Validate engine
        if engine not in ['kokkoro', 'chatterbox']:
            logger.error(f"❌ Job {job_id}: Invalid engine '{engine}'")
            return {
                "error": f"Invalid engine '{engine}'. Available: kokkoro, chatterbox",
                "job_id": job_id,
                "processing_time": time.time() - start_time
            }
        
        logger.info(f"🎵 Job {job_id}: Processing TTS with {engine} engine")
        logger.info(f"📄 Job {job_id}: Text length: {len(text)} characters")
        
        # Prepare the TTS request
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
        
        # Select the appropriate endpoint
        endpoint_url = KOKKORO_ENDPOINT if engine == 'kokkoro' else CHATTERBOX_ENDPOINT
        
        # Call the TTS endpoint
        result = call_tts_endpoint(endpoint_url, tts_payload, job_id)
        
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
                "endpoint_used": endpoint_url
            }
        else:
            logger.error(f"❌ Job {job_id}: TTS processing failed")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "engine": engine,
                "processing_time": processing_time,
                "endpoint_used": endpoint_url
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 Job {job_id}: Unexpected error: {str(e)}")
        return {
            "error": f"Internal gateway error: {str(e)}",
            "job_id": job_id,
            "processing_time": processing_time
        }

def call_tts_endpoint(endpoint_url: str, payload: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    Call the TTS endpoint with retry logic
    """
    if not RUNPOD_API_KEY:
        logger.warning(f"⚠️ Job {job_id}: RUNPOD_API_KEY not set, using dummy response")
        return {
            "success": True,
            "data": {
                "message": "TTS Gateway is working! (API key not configured for actual TTS)",
                "payload_sent": payload,
                "endpoint": endpoint_url
            }
        }
    
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
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Job {job_id}: TTS endpoint responded successfully")
                return {
                    "success": True,
                    "data": result
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.error(f"❌ Job {job_id}: {error_msg}")
                
                if attempt == MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Job {job_id}: Timeout on attempt {attempt + 1}")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": f"Request timeout after {REQUEST_TIMEOUT}s"
                }
                
        except Exception as e:
            logger.error(f"💥 Job {job_id}: Error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Wait before retry
        if attempt < MAX_RETRIES - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.info(f"⏳ Job {job_id}: Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return {
        "success": False,
        "error": "Max retries exceeded"
    }

def test_handler():
    """Test function for local development"""
    print("🧪 Testing TTS Gateway Handler locally...")
    
    # Test health check
    health_job = {
        "id": "test_health",
        "input": {"action": "health"}
    }
    
    print("\n=== Testing Health Check ===")
    result = handler(health_job)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test TTS request
    tts_job = {
        "id": "test_tts",
        "input": {
            "text": "Hello, this is a test of the TTS gateway.",
            "engine": "kokkoro"
        }
    }
    
    print("\n=== Testing TTS Request ===")
    result = handler(tts_job)
    print(f"Result: {json.dumps(result, indent=2)}")

# This is the CRITICAL section that starts the RunPod serverless worker
if __name__ == "__main__":
    import sys
    
    # Check if running in test mode
    if "--test" in sys.argv:
        test_handler()
    else:
        # Start the RunPod serverless worker
        logger.info("🚀 Starting TTS Gateway RunPod Serverless Worker")
        logger.info(f"🔧 Configuration:")
        logger.info(f"   - Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"   - Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        logger.info(f"   - API key configured: {'Yes' if RUNPOD_API_KEY else 'No'}")
        logger.info(f"   - Request timeout: {REQUEST_TIMEOUT}s")
        logger.info(f"   - Max retries: {MAX_RETRIES}")
        
        # This line starts the RunPod serverless worker - CRITICAL!
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
