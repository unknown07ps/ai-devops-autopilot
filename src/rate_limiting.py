"""
API Rate Limiting Module
Protects against abuse and denial-of-service attacks using slowapi
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from typing import Optional
import os


# ============================================================================
# Rate Limit Configuration
# ============================================================================

# Default rate limits (can be overridden via environment variables)
DEFAULT_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "100/minute")
DEFAULT_BURST_LIMIT = os.getenv("API_BURST_LIMIT", "20/second")

# Tiered rate limits based on subscription
RATE_LIMITS = {
    "anonymous": "30/minute",      # Unauthenticated requests
    "free": "60/minute",           # Free tier users
    "trial": "100/minute",         # Trial users
    "pro": "500/minute",           # Pro subscribers
    "enterprise": "2000/minute",   # Enterprise (practically unlimited)
}

# Sensitive endpoints with stricter limits
SENSITIVE_ENDPOINTS = {
    "/api/auth/login": "5/minute",      # Prevent brute force
    "/api/auth/register": "3/minute",   # Prevent spam registrations
    "/api/auth/password-reset-request": "3/minute",  # Prevent email spam
    "/api/cloud/connect": "10/minute",  # Cloud credential operations
}


# ============================================================================
# Rate Limiter Setup
# ============================================================================

def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses user_id if authenticated, otherwise IP address.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return f"user:{user.user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


def get_subscription_tier(request: Request) -> str:
    """Get the user's subscription tier for dynamic rate limiting"""
    user = getattr(request.state, "user", None)
    if not user:
        return "anonymous"
    
    subscription = getattr(request.state, "subscription", None)
    if not subscription:
        return "free"
    
    plan = getattr(subscription, "plan", None)
    if plan:
        return plan.value.lower()
    
    return "free"


def get_dynamic_rate_limit(request: Request) -> str:
    """
    Get rate limit based on user's subscription tier.
    Returns a rate limit string like "100/minute"
    """
    tier = get_subscription_tier(request)
    return RATE_LIMITS.get(tier, DEFAULT_RATE_LIMIT)


# Create the limiter with IP-based identification by default
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Use Redis if available
    strategy="fixed-window",  # or "moving-window" for stricter control
)


# ============================================================================
# Rate Limit Decorators for Endpoints
# ============================================================================

def rate_limit_login():
    """Decorator for login endpoints with strict limits"""
    return limiter.limit("5/minute")


def rate_limit_register():
    """Decorator for registration with anti-spam limits"""
    return limiter.limit("3/minute")


def rate_limit_sensitive():
    """Decorator for sensitive operations"""
    return limiter.limit("10/minute")


def rate_limit_standard():
    """Decorator for standard API endpoints"""
    return limiter.limit(DEFAULT_RATE_LIMIT)


def rate_limit_by_tier():
    """Decorator that applies limits based on subscription tier"""
    return limiter.limit(get_dynamic_rate_limit)


# ============================================================================
# Integration Helper
# ============================================================================

def setup_rate_limiting(app):
    """
    Setup rate limiting for a FastAPI application.
    Call this in main.py after creating the app.
    
    Usage:
        from src.rate_limiting import setup_rate_limiting, limiter
        app = FastAPI()
        setup_rate_limiting(app)
    """
    # Add the limiter to app state
    app.state.limiter = limiter
    
    # Add rate limit exceeded exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)
    
    print("[SECURITY] ✓ API rate limiting enabled")
    print(f"[SECURITY]   Default limit: {DEFAULT_RATE_LIMIT}")
    print(f"[SECURITY]   Burst limit: {DEFAULT_BURST_LIMIT}")
    
    return limiter


# ============================================================================
# Response Headers Helper
# ============================================================================

def add_rate_limit_headers(response, request: Request):
    """Add rate limit info to response headers for client visibility"""
    # These headers are automatically added by slowapi, but you can customize
    # X-RateLimit-Limit: Maximum requests allowed
    # X-RateLimit-Remaining: Requests remaining in window
    # X-RateLimit-Reset: Time when limit resets
    pass
