from typing import Dict, List, Optional
from config import Config

class ModelsRegistry:
    def __init__(self):
        self.config = Config()
        self.models = {
            'kokkoro': {
                'name': 'Kokkoro TTS',
                'description': 'High-quality neural TTS model using Google TTS',
                'voices': ['default', 'female', 'male'],
                'languages': ['en', 'es', 'fr', 'de', 'it'],
                'features': ['fast_synthesis', 'natural_voice', 'multilingual']
            },
            'chatterbox': {
                'name': 'Chatterbox TTS',
                'description': 'Fast and efficient TTS model using gTTS',
                'voices': ['default', 'casual', 'formal'],
                'languages': ['en'],
                'features': ['fast_synthesis', 'lightweight']
            }
        }
    
    def get_available_models(self) -> List[str]:
        """Return list of available model names"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict:
        """Get detailed information about a model"""
        return self.models.get(model_name, {})
    
    def get_model_endpoint(self, model_name: str) -> Optional[str]:
        """Get the endpoint URL for a model"""
        return self.config.get_endpoint(model_name)
    
    def register_model(self, model_name: str, model_info: Dict, endpoint_url: str):
        """Register a new model dynamically"""
        self.models[model_name] = model_info
        self.config.set_endpoint(model_name, endpoint_url)
    
    def get_all_models_info(self) -> Dict:
        """Get information about all models"""
        return {
            model_name: {
                **model_info,
                'endpoint': self.get_model_endpoint(model_name),
                'available': self.get_model_endpoint(model_name) is not None
            }
            for model_name, model_info in self.models.items()
        }
