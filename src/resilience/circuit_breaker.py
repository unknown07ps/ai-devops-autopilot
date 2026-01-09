"""
Circuit Breaker Pattern Implementation

Provides fault isolation for external service calls (AI inference, webhooks, cloud APIs).
Non-intrusive wrapper that can be optionally applied to any async function.

Usage:
    from src.resilience.circuit_breaker import CircuitBreaker, circuit_breaker
    
    # Option 1: Decorator
    @circuit_breaker(name="ollama", failure_threshold=3, recovery_timeout=30)
    async def call_ollama(prompt):
        ...
    
    # Option 2: Instance
    breaker = CircuitBreaker("slack", failure_threshold=5)
    result = await breaker.call(send_slack_message, msg)
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from functools import wraps
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service protection.
    
    - CLOSED: Normal operation, counts failures
    - OPEN: Blocks calls, returns fallback immediately
    - HALF_OPEN: Allows one test request to check recovery
    
    Attributes:
        name: Identifier for logging and metrics
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
        timeout: Max seconds to wait for call completion
    """
    
    # Global registry of all circuit breakers
    _registry: Dict[str, 'CircuitBreaker'] = {}
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        timeout: float = 60.0,
        fallback: Optional[Callable] = None
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.timeout = timeout
        self.fallback = fallback
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0
        self.total_calls = 0
        
        # Register for monitoring
        CircuitBreaker._registry[name] = self
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _record_success(self):
        """Record successful call"""
        self.failure_count = 0
        self.success_count += 1
        self.total_calls += 1
        
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"[CIRCUIT:{self.name}] ✅ Recovery successful, closing circuit")
            self.state = CircuitState.CLOSED
    
    def _record_failure(self, error: Exception):
        """Record failed call"""
        self.failure_count += 1
        self.total_calls += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"[CIRCUIT:{self.name}] ⚠️ Failure #{self.failure_count}: {type(error).__name__}")
        
        if self.failure_count >= self.failure_threshold:
            logger.error(f"[CIRCUIT:{self.name}] 🔴 Opening circuit after {self.failure_count} failures")
            self.state = CircuitState.OPEN
    
    async def call(
        self,
        func: Callable[..., Any],
        *args,
        fallback_value: Any = None,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Positional arguments for func
            fallback_value: Value to return if circuit is open
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result or fallback value
        """
        self.total_calls += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"[CIRCUIT:{self.name}] 🟡 Attempting recovery (half-open)")
                self.state = CircuitState.HALF_OPEN
            else:
                logger.debug(f"[CIRCUIT:{self.name}] Circuit open, returning fallback")
                if self.fallback:
                    return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
                return fallback_value
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
            self._record_success()
            return result
            
        except asyncio.TimeoutError as e:
            logger.warning(f"[CIRCUIT:{self.name}] Timeout after {self.timeout}s")
            self._record_failure(e)
            if self.fallback:
                return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
            return fallback_value
            
        except Exception as e:
            self._record_failure(e)
            if self.fallback:
                return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "last_failure": datetime.fromtimestamp(self.last_failure_time, tz=timezone.utc).isoformat() if self.last_failure_time else None,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }
    
    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered circuit breakers"""
        return {name: cb.get_status() for name, cb in cls._registry.items()}


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    timeout: float = 60.0,
    fallback: Optional[Callable] = None
):
    """
    Decorator to wrap async function with circuit breaker.
    
    Example:
        @circuit_breaker(name="ollama", failure_threshold=3)
        async def call_ai(prompt):
            return await ollama_client.generate(prompt)
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        timeout=timeout,
        fallback=fallback
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        # Attach breaker for testing/inspection
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator


# Pre-configured circuit breakers for common services
OLLAMA_BREAKER = CircuitBreaker(
    name="ollama_ai",
    failure_threshold=3,
    recovery_timeout=60.0,
    timeout=90.0  # AI inference can be slow
)

SLACK_BREAKER = CircuitBreaker(
    name="slack_webhook",
    failure_threshold=5,
    recovery_timeout=30.0,
    timeout=10.0
)

CLOUD_BREAKER = CircuitBreaker(
    name="cloud_api",
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout=30.0
)

PAYMENT_BREAKER = CircuitBreaker(
    name="razorpay",
    failure_threshold=3,
    recovery_timeout=30.0,
    timeout=15.0
)
