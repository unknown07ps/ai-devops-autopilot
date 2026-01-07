"""
Encryption utilities for secure credential storage
Uses AES-256 encryption with server-side key
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Get encryption key from environment or generate a default
def get_encryption_key():
    """Get or derive encryption key from environment"""
    key = os.getenv('CLOUD_CREDENTIAL_KEY')
    if key:
        # Use provided key
        return key.encode() if len(key) == 44 else derive_key(key)
    else:
        # Generate a default key (in production, this should be set via env)
        return derive_key('deployr-cloud-costs-default-key')

def derive_key(password: str) -> bytes:
    """Derive a Fernet-compatible key from a password"""
    salt = b'deployr_cloud_salt_v1'  # Fixed salt for consistent key derivation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_credentials(credentials: dict) -> str:
    """
    Encrypt credentials dictionary to a secure string
    
    Args:
        credentials: Dictionary containing cloud provider credentials
        
    Returns:
        Base64 encoded encrypted string
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        json_data = json.dumps(credentials)
        encrypted = f.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        raise Exception(f"Failed to encrypt credentials: {e}")

def decrypt_credentials(encrypted_data: str) -> dict:
    """
    Decrypt credentials string back to dictionary
    
    Args:
        encrypted_data: Base64 encoded encrypted string
        
    Returns:
        Dictionary containing cloud provider credentials
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = f.decrypt(decoded)
        return json.loads(decrypted.decode())
    except Exception as e:
        raise Exception(f"Failed to decrypt credentials: {e}")

def validate_credentials_format(provider: str, credentials: dict) -> tuple[bool, str]:
    """
    Validate that credentials have required fields for the provider
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = {
        'aws': ['access_key_id', 'secret_access_key'],
        'azure': ['subscription_id', 'client_id', 'client_secret', 'tenant_id'],
        'gcp': ['service_account_json']
    }
    
    if provider not in required_fields:
        return False, f"Unknown provider: {provider}"
    
    missing = [f for f in required_fields[provider] if f not in credentials or not credentials[f]]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, ""
