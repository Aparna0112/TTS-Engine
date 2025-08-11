import os
from typing import Dict

class Config:
    def __init__(self):
        self.model_endpoints = self._load_model_endpoints()
    
    def _load_model_endpoints(self) -> Dict[str, str]:
        """Load model endpoints from environment or config"""
        endpoints = {}
        
        # Default endpoints for local development
        endpoints['kokkoro'] = os.getenv('KOKKORO_ENDPOINT', 'http://kokkoro:8001')
        endpoints['chatterbox'] = os.getenv('CHATTERBOX_ENDPOINT', 'http://chatterbox:8002')
        
        # RunPod endpoints (if deployed separately)
        if os.getenv('RUNPOD_KOKKORO_ENDPOINT'):
            endpoints['kokkoro'] = os.getenv('RUNPOD_KOKKORO_ENDPOINT')
        if os.getenv('RUNPOD_CHATTERBOX_ENDPOINT'):
            endpoints['chatterbox'] = os.getenv('RUNPOD_CHATTERBOX_ENDPOINT')
        
        return endpoints
    
    def get_endpoint(self, model_name: str) -> str:
        return self.model_endpoints.get(model_name)
