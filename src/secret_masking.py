"""
Secret Masking & Leakage Prevention Module
Automatically redacts sensitive values from logs and responses
"""

import re
from typing import Any, Dict, List, Optional
import functools
import json


# ============================================================================
# Secret Patterns to Detect and Mask
# ============================================================================

SECRET_PATTERNS = {
    # AWS
    r'AKIA[0-9A-Z]{16}': 'AWS_ACCESS_KEY',
    r'(?i)aws[_-]?secret[_-]?access[_-]?key["\s:=]+[A-Za-z0-9/+=]{40}': 'AWS_SECRET_KEY',
    
    # Azure
    r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}': 'UUID_OR_AZURE_ID',
    
    # GCP
    r'(?i)private[_-]?key["\s:=]+-----BEGIN': 'GCP_PRIVATE_KEY',
    
    # Generic tokens
    r'(?i)(bearer\s+)[A-Za-z0-9\-_\.]{20,}': 'BEARER_TOKEN',
    r'(?i)(api[_-]?key|apikey)["\s:=]+[A-Za-z0-9\-_]{20,}': 'API_KEY',
    r'(?i)(secret|password|passwd|pwd)["\s:=]+[^\s"\']{8,}': 'SECRET_VALUE',
    r'(?i)(token)["\s:=]+[A-Za-z0-9\-_\.]{20,}': 'TOKEN',
    
    # JWT tokens
    r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+': 'JWT_TOKEN',
    
    # Credit cards (basic pattern)
    r'\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b': 'CREDIT_CARD',
}

# Fields that should always be redacted
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'access_token',
    'refresh_token', 'api_key', 'apikey', 'secret_key', 'secret_access_key',
    'private_key', 'client_secret', 'authorization', 'auth', 'credential',
    'credentials', 'hashed_password', 'key_hash', 'service_account_json',
    'access_key_id', 'secret_access_key', 'tenant_id', 'client_id',
    'subscription_id'
}


# ============================================================================
# Masking Functions
# ============================================================================

def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Mask a secret value, showing only first few characters
    
    Args:
        value: The secret string to mask
        show_chars: Number of characters to show at start
        
    Returns:
        Masked string like "eyJh...***MASKED***"
    """
    if not value or len(value) < show_chars + 4:
        return "***MASKED***"
    
    return f"{value[:show_chars]}...***MASKED***"


def mask_string(text: str) -> str:
    """
    Scan a string for secret patterns and mask them
    
    Args:
        text: Input string that may contain secrets
        
    Returns:
        String with secrets masked
    """
    if not text:
        return text
    
    result = text
    for pattern, label in SECRET_PATTERNS.items():
        result = re.sub(pattern, f"***{label}_MASKED***", result)
    
    return result


def mask_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """
    Recursively mask sensitive fields in a dictionary
    
    Args:
        data: Dictionary that may contain sensitive values
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Dictionary with sensitive values masked
    """
    if depth > max_depth:
        return data
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if this is a sensitive field
        if any(sf in key_lower for sf in SENSITIVE_FIELDS):
            if isinstance(value, str):
                result[key] = mask_secret(value)
            else:
                result[key] = "***MASKED***"
        elif isinstance(value, dict):
            result[key] = mask_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                mask_dict(item, depth + 1, max_depth) if isinstance(item, dict) 
                else mask_string(str(item)) if isinstance(item, str) 
                else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = mask_string(value)
        else:
            result[key] = value
    
    return result


def safe_log(message: str, data: Optional[Dict] = None) -> str:
    """
    Create a safe log message with secrets masked
    
    Args:
        message: Log message that may contain secrets
        data: Optional dictionary to include in log
        
    Returns:
        Safe log string with secrets masked
    """
    safe_message = mask_string(message)
    
    if data:
        safe_data = mask_dict(data)
        return f"{safe_message} | Data: {json.dumps(safe_data)}"
    
    return safe_message


# ============================================================================
# Decorator for Safe Logging in Functions
# ============================================================================

def mask_return_secrets(func):
    """
    Decorator that masks secrets in function return values
    Useful for API responses that might contain sensitive data
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            return mask_dict(result)
        elif isinstance(result, str):
            return mask_string(result)
        return result
    return wrapper


def mask_log_arguments(func):
    """
    Decorator that masks secrets in function arguments when logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Mask kwargs for any logging
        masked_kwargs = mask_dict(kwargs) if kwargs else {}
        return func(*args, **kwargs)
    return wrapper


# ============================================================================
# Safe Print Function
# ============================================================================

def safe_print(message: str, *args, **kwargs):
    """
    Print with automatic secret masking
    Use instead of print() when logging potentially sensitive data
    """
    safe_message = mask_string(str(message))
    print(safe_message, *args, **kwargs)


# ============================================================================
# Token Masking Helper
# ============================================================================

def mask_token_for_log(token: str) -> str:
    """
    Mask a token for safe logging - shows only first 8 chars
    
    Usage:
        print(f"[PASSWORD RESET] Token issued: {mask_token_for_log(token)}")
    """
    if not token:
        return "***NO_TOKEN***"
    
    if len(token) <= 12:
        return "***TOKEN_MASKED***"
    
    return f"{token[:8]}...***"


# ============================================================================
# Response Sanitizer for API
# ============================================================================

def sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize API response to remove sensitive data
    Call before returning responses that might contain secrets
    """
    return mask_dict(response)


# ============================================================================
# Validation that Secrets Aren't in Logs
# ============================================================================

def check_for_secrets(text: str) -> List[str]:
    """
    Check if text contains potential secrets (for testing/auditing)
    
    Returns:
        List of detected secret types
    """
    detected = []
    for pattern, label in SECRET_PATTERNS.items():
        if re.search(pattern, text):
            detected.append(label)
    return detected
