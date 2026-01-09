"""
Encryption utilities for secure credential storage
Uses AES-256 encryption with server-side key

Version History:
- v1: Fixed salt (legacy) - still supported for decryption
- v2: Unique salt per credential - used for all new encryption
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Encryption format version prefix
ENCRYPTION_VERSION_V2 = b'v2:'
LEGACY_SALT = b'deployr_cloud_salt_v1'  # Keep for backward compatibility
SALT_LENGTH = 16  # 128-bit salt for v2


def get_encryption_key():
    """Get or derive encryption key from environment - REQUIRED"""
    key = os.getenv('CLOUD_CREDENTIAL_KEY')
    if not key:
        raise ValueError(
            "CLOUD_CREDENTIAL_KEY environment variable is required.\n"
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "Set this in your .env file before storing cloud credentials."
        )
    # Check if it's already a valid Fernet key (44 chars base64)
    if len(key) == 44:
        return key.encode()
    else:
        # Derive key from password using a unique salt
        # Note: This path should be avoided - use a proper Fernet key
        return derive_key_v2(key, os.urandom(SALT_LENGTH))[0]


def derive_key_legacy(password: str) -> bytes:
    """
    Derive key using legacy fixed salt (v1).
    ONLY used for decrypting old data - not for new encryption.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=LEGACY_SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def derive_key_v2(password: str, salt: bytes) -> tuple:
    """
    Derive key using unique salt (v2).
    Returns: (derived_key, salt) - salt must be stored with encrypted data
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_credentials(credentials: dict) -> str:
    """
    Encrypt credentials dictionary to a secure string.
    Uses v2 format with unique salt per credential.
    
    Args:
        credentials: Dictionary containing cloud provider credentials
        
    Returns:
        Base64 encoded encrypted string (v2 format with embedded salt)
    """
    try:
        key_env = os.getenv('CLOUD_CREDENTIAL_KEY')
        if not key_env:
            raise ValueError("CLOUD_CREDENTIAL_KEY environment variable is required")
        
        # Check if it's a direct Fernet key or password
        if len(key_env) == 44:
            # Direct Fernet key - use as-is
            key = key_env.encode()
            salt = b''  # No salt needed for direct key
        else:
            # Password - derive with unique salt
            salt = os.urandom(SALT_LENGTH)
            key, salt = derive_key_v2(key_env, salt)
        
        f = Fernet(key)
        json_data = json.dumps(credentials)
        encrypted = f.encrypt(json_data.encode())
        
        # v2 format: "v2:" + base64(salt) + ":" + base64(encrypted)
        if salt:
            salt_b64 = base64.urlsafe_b64encode(salt).decode()
            encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode()
            return f"v2:{salt_b64}:{encrypted_b64}"
        else:
            # Direct Fernet key - simple format
            return base64.urlsafe_b64encode(encrypted).decode()
            
    except Exception as e:
        raise Exception(f"Failed to encrypt credentials: {e}")


def decrypt_credentials(encrypted_data: str) -> dict:
    """
    Decrypt credentials string back to dictionary.
    Supports both v2 (unique salt) and v1 (legacy fixed salt) formats.
    
    Args:
        encrypted_data: Base64 encoded encrypted string
        
    Returns:
        Dictionary containing cloud provider credentials
    """
    try:
        key_env = os.getenv('CLOUD_CREDENTIAL_KEY')
        if not key_env:
            raise ValueError("CLOUD_CREDENTIAL_KEY environment variable is required")
        
        # Check for v2 format: "v2:<salt_b64>:<encrypted_b64>"
        if encrypted_data.startswith('v2:'):
            parts = encrypted_data.split(':', 2)
            if len(parts) != 3:
                raise ValueError("Invalid v2 encryption format")
            
            _, salt_b64, encrypted_b64 = parts
            salt = base64.urlsafe_b64decode(salt_b64.encode())
            encrypted = base64.urlsafe_b64decode(encrypted_b64.encode())
            
            # Derive key with the stored salt
            if len(key_env) == 44:
                key = key_env.encode()
            else:
                key, _ = derive_key_v2(key_env, salt)
            
            f = Fernet(key)
            decrypted = f.decrypt(encrypted)
            return json.loads(decrypted.decode())
        
        else:
            # Legacy v1 format - try direct Fernet key first
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            
            if len(key_env) == 44:
                key = key_env.encode()
            else:
                # Legacy: use fixed salt
                key = derive_key_legacy(key_env)
            
            f = Fernet(key)
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


def is_legacy_encryption(encrypted_data: str) -> bool:
    """
    Check if encrypted data uses legacy v1 format.
    Useful for migration scripts to identify data that needs re-encryption.
    """
    return not encrypted_data.startswith('v2:')

