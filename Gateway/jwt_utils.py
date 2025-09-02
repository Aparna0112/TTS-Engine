#!/usr/bin/env python3
"""
JWT Utilities for TTS Gateway
Save this file as: gateway/jwt_utils.py

Helper utilities for JWT token management, validation, and testing
"""

import jwt
import json
import time
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

class JWTManager:
    """JWT Token Manager for TTS Gateway"""
    
    def __init__(self, 
                 secret_key: str = None,
                 algorithm: str = "HS256",
                 expiration_hours: int = 24):
        """
        Initialize JWT Manager
        
        Args:
            secret_key: JWT secret key (defaults to env variable)
            algorithm: JWT algorithm (default: HS256)
            expiration_hours: Token expiration in hours (default: 24)
        """
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'default-secret-change-in-production')
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
        
        if self.secret_key == 'default-secret-change-in-production':
            print("⚠️  WARNING: Using default JWT secret key. Change this in production!")
    
    def generate_token(self, 
                      user_id: str, 
                      role: str = "user",
                      permissions: List[str] = None,
                      custom_claims: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a JWT token with user information
        
        Args:
            user_id: Unique user identifier
            role: User role (user, admin, premium, etc.)
            permissions: List of permissions
            custom_claims: Additional custom claims
            
        Returns:
            Dictionary with token info
        """
        now = datetime.utcnow()
        exp_time = now + timedelta(hours=self.expiration_hours)
        
        payload = {
            'user_id': user_id,
            'role': role,
            'permissions': permissions or [],
            'iat': now,
            'exp': exp_time,
            'iss': 'tts-gateway',  # Issuer
            'sub': user_id,        # Subject
        }
        
        # Add custom claims if provided
        if custom_claims:
            payload.update(custom_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            'token': token,
            'user_id': user_id,
            'role': role,
            'expires_at': exp_time.isoformat(),
            'expires_in_seconds': int(self.expiration_hours * 3600),
            'issued_at': now.isoformat()
        }
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Validation result with payload or error
        """
        try:
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode and validate
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_iat': True,
                    'require_exp': True,
                    'require_iat': True
                }
            )
            
            return {
                'valid': True,
                'payload': payload,
                'user_id': payload.get('user_id'),
                'role': payload.get('role'),
                'permissions': payload.get('permissions', []),
                'expires_at': datetime.fromtimestamp(payload['exp']).isoformat()
            }
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': f'Invalid token: {str(e)}'}
        except Exception as e:
            return {'valid': False, 'error': f'Token validation failed: {str(e)}'}
    
    def refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Refresh an existing token (if still valid or recently expired)
        
        Args:
            token: Current JWT token
            
        Returns:
            New token information or error
        """
        try:
            # Decode without verifying expiration
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}
            )
            
            # Check if token expired more than 1 hour ago
            exp_time = datetime.fromtimestamp(payload['exp'])
            if datetime.utcnow() - exp_time > timedelta(hours=1):
                return {'success': False, 'error': 'Token too old to refresh'}
            
            # Generate new token with same claims
            return self.generate_token(
                user_id=payload['user_id'],
                role=payload.get('role', 'user'),
                permissions=payload.get('permissions', []),
                custom_claims={k: v for k, v in payload.items() 
                             if k not in ['user_id', 'role', 'permissions', 'iat', 'exp', 'iss', 'sub']}
            )
            
        except Exception as e:
            return {'success': False, 'error': f'Token refresh failed: {str(e)}'}
    
    def decode_token_info(self, token: str) -> Dict[str, Any]:
        """
        Decode token without validation (for debugging)
        
        Args:
            token: JWT token
            
        Returns:
            Token payload information
        """
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            
            return {
                'success': True,
                'payload': payload,
                'user_id': payload.get('user_id'),
                'role': payload.get('role'),
                'issued_at': datetime.fromtimestamp(payload['iat']).isoformat() if 'iat' in payload else None,
                'expires_at': datetime.fromtimestamp(payload['exp']).isoformat() if 'exp' in payload else None,
                'is_expired': datetime.fromtimestamp(payload['exp']) < datetime.utcnow() if 'exp' in payload else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class TTSGatewayClient:
    """Client for interacting with JWT-enabled TTS Gateway"""
    
    def __init__(self, 
                 gateway_url: str,
                 runpod_api_key: str,
                 jwt_manager: JWTManager = None):
        """
        Initialize TTS Gateway Client
        
        Args:
            gateway_url: RunPod gateway endpoint URL
            runpod_api_key: RunPod API key for authentication
            jwt_manager: JWT manager instance (optional)
        """
        self.gateway_url = gateway_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {runpod_api_key}'
        }
        self.jwt_manager = jwt_manager or JWTManager()
        self._cached_token = None
        self._token_user_id = None
    
    def health_check(self) -> Dict[str, Any]:
        """Check gateway health status"""
        payload = {"input": {"action": "health"}}
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        return response.json()
    
    def generate_token(self, user_id: str, user_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate JWT token via gateway
        
        Args:
            user_id: User identifier
            user_data: Additional user data
            
        Returns:
            Token generation response
        """
        payload = {
            "input": {
                "action": "generate_token",
                "user_id": user_id,
                "user_data": user_data or {}
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        result = response.json()
        
        # Cache the token for future use
        if result.get('success') and result.get('token'):
            self._cached_token = result['token']
            self._token_user_id = user_id
        
        return result
    
    def text_to_speech(self, 
                      text: str,
                      engine: str = "kokkoro",
                      jwt_token: str = None,
                      voice: str = "default",
                      speed: float = 1.0,
                      **kwargs) -> Dict[str, Any]:
        """
        Convert text to speech
        
        Args:
            text: Text to convert
            engine: TTS engine (kokkoro/chatterbox)
            jwt_token: JWT token (uses cached if not provided)
            voice: Voice to use
            speed: Speech speed
            **kwargs: Additional engine-specific parameters
            
        Returns:
            TTS conversion response
        """
        # Use provided token or cached token
        token = jwt_token or self._cached_token
        
        if not token:
            return {
                'error': 'No JWT token provided. Generate a token first.',
                'help': 'Call generate_token() first or provide jwt_token parameter'
            }
        
        payload = {
            "input": {
                "jwt_token": token,
                "text": text,
                "engine": engine,
                "voice": voice,
                "speed": speed,
                **kwargs
            }
        }
        
        response = requests.post(self.gateway_url, json=payload, headers=self.headers)
        return response.json()
    
    def batch_text_to_speech(self, 
                           texts: List[str],
                           engine: str = "kokkoro",
                           jwt_token: str = None,
                           **kwargs) -> List[Dict[str, Any]]:
        """
        Convert multiple texts to speech
        
        Args:
            texts: List of texts to convert
            engine: TTS engine
            jwt_token: JWT token
            **kwargs: Additional parameters
            
        Returns:
            List of TTS conversion responses
        """
        results = []
        for i, text in enumerate(texts):
            print(f"Processing text {i+1}/{len(texts)}: {text[:50]}...")
            result = self.text_to_speech(text, engine, jwt_token, **kwargs)
            results.append(result)
            
            # Add small delay to avoid overwhelming the service
            time.sleep(0.1)
        
        return results
    
    def validate_cached_token(self) -> Dict[str, Any]:
        """Validate the currently cached token"""
        if not self._cached_token:
            return {'valid': False, 'error': 'No cached token'}
        
        return self.jwt_manager.validate_token(self._cached_token)

def create_test_tokens():
    """Create test tokens for different user types"""
    jwt_manager = JWTManager()
    
    # Different user types
    users = [
        {
            'user_id': 'admin_user',
            'role': 'admin',
            'permissions': ['tts_generate', 'user_manage', 'system_config'],
            'custom_claims': {'department': 'engineering', 'level': 'senior'}
        },
        {
            'user_id': 'premium_user',
            'role': 'premium',
            'permissions': ['tts_generate', 'priority_queue'],
            'custom_claims': {'subscription': 'premium', 'credits': 1000}
        },
        {
            'user_id': 'basic_user',
            'role': 'user',
            'permissions': ['tts_generate'],
            'custom_claims': {'subscription': 'basic', 'credits': 100}
        }
    ]
    
    tokens = {}
    
    print("🔑 Creating test JWT tokens...\n")
    
    for user in users:
        token_info = jwt_manager.generate_token(
            user_id=user['user_id'],
            role=user['role'],
            permissions=user['permissions'],
            custom_claims=user['custom_claims']
        )
        
        tokens[user['user_id']] = token_info
        
        print(f"👤 {user['user_id']} ({user['role']}):")
        print(f"   Token: {token_info['token'][:50]}...")
        print(f"   Expires: {token_info['expires_at']}")
        print(f"   Permissions: {user['permissions']}")
        print()
    
    return tokens

def test_client_functionality():
    """Test the TTS Gateway Client"""
    # Configuration (replace with your actual values)
    gateway_url = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
    runpod_api_key = "YOUR_RUNPOD_API_KEY"
    
    print("🧪 Testing TTS Gateway Client...")
    print("=" * 50)
    
    # Initialize client
    client = TTSGatewayClient(gateway_url, runpod_api_key)
    
    # Test health check
    print("\n1. Health Check:")
    health = client.health_check()
    print(f"   Status: {health.get('status', 'unknown')}")
    print(f"   JWT Auth: {health.get('jwt_auth_enabled', False)}")
    
    # Test token generation
    print("\n2. Token Generation:")
    token_result = client.generate_token(
        user_id="test_client_user",
        user_data={"plan": "premium", "credits": 500}
    )
    
    if token_result.get('success'):
        print(f"   ✅ Token generated for user: {token_result['user_id']}")
        print(f"   Token: {token_result['token'][:50]}...")
    else:
        print(f"   ❌ Token generation failed: {token_result.get('error')}")
        return
    
    # Test TTS
    print("\n3. Text-to-Speech:")
    tts_result = client.text_to_speech(
        text="Hello from the TTS Gateway client test!",
        engine="kokkoro"
    )
    
    if tts_result.get('success'):
        print(f"   ✅ TTS successful for user: {tts_result.get('user_id')}")
        print(f"   Engine: {tts_result.get('engine')}")
        print(f"   Processing time: {tts_result.get('processing_time', 0):.2f}s")
    else:
        print(f"   ❌ TTS failed: {tts_result.get('error')}")
    
    # Test batch processing
    print("\n4. Batch Processing:")
    texts = [
        "First test sentence.",
        "Second test sentence.",
        "Third test sentence."
    ]
    
    batch_results = client.batch_text_to_speech(texts, engine="kokkoro")
    successful = sum(1 for r in batch_results if r.get('success'))
    print(f"   ✅ {successful}/{len(texts)} batch requests successful")

if __name__ == "__main__":
    import sys
    
    if "--create-tokens" in sys.argv:
        create_test_tokens()
    elif "--test-client" in sys.argv:
        test_client_functionality()
    else:
        print("JWT Utilities for TTS Gateway")
        print("Usage:")
        print("  python jwt_utils.py --create-tokens    # Create test tokens")
        print("  python jwt_utils.py --test-client      # Test client functionality")
        print()
        
        # Demo JWT manager
        jwt_manager = JWTManager()
        
        # Generate a test token
        token_info = jwt_manager.generate_token(
            user_id="demo_user",
            role="admin",
            permissions=["tts_generate", "admin_access"]
        )
        
        print("Demo JWT Token:")
        print(f"  Token: {token_info['token'][:50]}...")
        print(f"  User ID: {token_info['user_id']}")
        print(f"  Role: {token_info['role']}")
        print(f"  Expires: {token_info['expires_at']}")
        
        # Validate the token
        validation = jwt_manager.validate_token(token_info['token'])
        print(f"\nValidation: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
        
        if validation['valid']:
            print(f"  User ID: {validation['user_id']}")
            print(f"  Role: {validation['role']}")
            print(f"  Permissions: {validation['permissions']}")
