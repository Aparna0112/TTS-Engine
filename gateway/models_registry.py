from typing import Dict, List
from config import Config

class ModelsRegistry:
    def __init__(self):
        self.config = Config()
        self.models = {
            'kokkoro': {
                'name': 'Kokkoro TTS',
                'description': 'High-quality neural TTS model',
                'voices': ['default', 'female1', 'male1'],
                'languages': ['en', 'ja']
            },
            'chatterbox': {
                'name': 'Chatterbox TTS',
                'description': 'Fast and efficient TTS model',
                'voices': ['default', 'casual', 'formal'],
                'languages': ['en']
            }
        }
    
    def get_available_models(self) -> List[str]:
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict:
        return self.models.get(model_name, {})
    
    def get_model_endpoint(self, model_name: str) -> str:
        return self.config.get_endpoint(model_name)
    
    def register_model(self, model_name: str, model_info: Dict):
        """Register a new model - for dynamic model addition"""
        self.models[model_name] = model_info
