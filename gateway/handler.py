import runpod
import requests
import os
import time
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
KOKKORO_ENDPOINT = os.getenv('KOKKORO_ENDPOINT', 'https://api.runpod.ai/v2/2bmvfn2g610d9a/runsync')
CHATTERBOX_ENDPOINT = os.getenv('CHATTERBOX_ENDPOINT', 'https://api.runpod.ai/v2/w3m6egp1cicw6n/runsync')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# Timeout settings
REQUEST_TIMEOUT = 300  # 5 minutes
RETRY_ATTEMPTS = 3

class TTSGateway:
    def __init__(self):
        self.endpoints = {
            'kokkoro': KOKKORO_ENDPOINT,
            'chatterbox': CHATTERBOX_ENDPOINT
        }
        logger.info(f"Initialized TTS Gateway with endpoints: {list(self.endpoints.keys())}")
        
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for RunPod"""
        return {
            "status": "healthy",
            "endpoints": list(self.endpoints.keys()),
            "timestamp": time.time()
        }
    
    def validate_input(self, job_input: Dict[str, Any]) -> tuple[bool, str]:
        """Validate input parameters"""
        if not job_input.get('text'):
            return False, "Missing 'text' parameter"
        
        engine = job_input.get('engine', 'kokkoro').lower()
        if engine not in self.endpoints:
            return False, f"Unsupported engine: {engine}. Available: {list(self.endpoints.keys())}"
        
        return True, ""
    
    def call_tts_endpoint(self, endpoint_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call the specific TTS endpoint with retry logic"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {RUNPOD_API_KEY}'
        }
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                logger.info(f"Calling endpoint {endpoint_url}, attempt {attempt + 1}")
                
                response = requests.post(
                    endpoint_url,
                    json={"input": payload},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully received response from {endpoint_url}")
                    return {
                        "success": True,
                        "data": result,
                        "endpoint": endpoint_url,
                        "attempt": attempt + 1
                    }
                else:
                    logger.error(f"HTTP {response.status_code} from {endpoint_url}: {response.text}")
                    if attempt == RETRY_ATTEMPTS - 1:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}: {response.text}",
                            "endpoint": endpoint_url
                        }
                    
            except requests.exceptions.Timeout:
                logger.error(f"Timeout calling {endpoint_url} (attempt {attempt + 1})")
                if attempt == RETRY_ATTEMPTS - 1:
                    return {
                        "success": False,
                        "error": "Request timeout",
                        "endpoint": endpoint_url
                    }
                    
            except Exception as e:
                logger.error(f"Error calling {endpoint_url}: {str(e)}")
                if attempt == RETRY_ATTEMPTS - 1:
                    return {
                        "success": False,
                        "error": str(e),
                        "endpoint": endpoint_url
                    }
            
            # Wait before retry
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "error": "Max retries exceeded"}

# Initialize gateway
gateway = TTSGateway()

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """Main RunPod handler function"""
    try:
        job_input = job.get('input', {})
        job_id = job.get('id', 'unknown')
        
        logger.info(f"Processing job {job_id} with input: {job_input}")
        
        # Handle health check requests
        if job_input.get('action') == 'health':
            return gateway.health_check()
        
        # Validate input
        is_valid, error_msg = gateway.validate_input(job_input)
        if not is_valid:
            logger.error(f"Invalid input for job {job_id}: {error_msg}")
            return {
                "error": error_msg,
                "job_id": job_id
            }
        
        # Get parameters
        text = job_input['text']
        engine = job_input.get('engine', 'kokkoro').lower()
        voice = job_input.get('voice', 'default')
        speed = job_input.get('speed', 1.0)
        
        # Prepare payload for TTS endpoint
        tts_payload = {
            'text': text,
            'voice': voice,
            'speed': speed
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
        
        # Call the appropriate TTS endpoint
        endpoint_url = gateway.endpoints[engine]
        result = gateway.call_tts_endpoint(endpoint_url, tts_payload)
        
        if result['success']:
            logger.info(f"Successfully processed job {job_id} with {engine}")
            return {
                "job_id": job_id,
                "engine": engine,
                "text": text,
                "result": result['data'],
                "processing_time": time.time()
            }
        else:
            logger.error(f"Failed to process job {job_id}: {result['error']}")
            return {
                "error": f"TTS processing failed: {result['error']}",
                "job_id": job_id,
                "engine": engine
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in handler: {str(e)}")
        return {
            "error": f"Internal error: {str(e)}",
            "job_id": job.get('id', 'unknown')
        }

# Health check function for container health
def health():
    """Simple health check for container readiness"""
    return {"status": "ready", "timestamp": time.time()}

if __name__ == "__main__":
    # Check if we're running a test
    if "--test" in os.sys.argv:
        # Test the handler locally
        test_job = {
            "id": "test_job",
            "input": {
                "text": "Hello, this is a test.",
                "engine": "kokkoro",
                "voice": "default"
            }
        }
        result = handler(test_job)
        print(f"Test result: {result}")
    else:
        # Start the RunPod serverless handler
        logger.info("Starting TTS Gateway RunPod Handler")
        logger.info(f"Available endpoints: {list(gateway.endpoints.keys())}")
        logger.info(f"Kokkoro endpoint: {KOKKORO_ENDPOINT}")
        logger.info(f"Chatterbox endpoint: {CHATTERBOX_ENDPOINT}")
        
        runpod.serverless.start({
            "handler": handler,
            "return_aggregate_stream": True
        })
