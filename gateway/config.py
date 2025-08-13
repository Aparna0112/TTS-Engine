import os
from typing import Dict, Optional

class Config:
    def __init__(self):
        self.model_endpoints = self._load_model_endpoints()
        self.api_key = os.getenv('RUNPOD_API_KEY')
    
    def _load_model_endpoints(self) -> Dict[str, Optional[str]]:
        """Load model endpoints from environment variables"""
        endpoints = {}
        
        # Load from environment variables
        endpoints['kokkoro'] = os.getenv('KOKKORO_ENDPOINT')
        endpoints['chatterbox'] = os.getenv('CHATTERBOX_ENDPOINT')
        
        return endpoints
    
    def get_endpoint(self, model_name: str) -> Optional[str]:
        return self.model_endpoints.get(model_name)
    
    def set_endpoint(self, model_name: str, endpoint_url: str):
        self.model_endpoints[model_name] = endpoint_url
