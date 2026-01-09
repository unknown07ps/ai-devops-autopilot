"""
Distributed Trace ID Propagation

Provides optional trace ID generation and propagation across API requests,
background workers, and external service calls.

Usage:
    # In middleware (already integrated via setup_tracing)
    from src.tracing import setup_tracing
    setup_tracing(app)
    
    # In any code to get/set trace ID
    from src.tracing import get_trace_id, set_trace_id
    trace_id = get_trace_id()  # Returns current trace or generates new
    
    # For logging with trace context
    from src.tracing import trace_context
    logger.info("Processing request", extra=trace_context())
"""

import uuid
import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any
from functools import wraps

# Context variable for trace ID propagation across async calls
_trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)

logger = logging.getLogger(__name__)

# Header names for trace propagation
TRACE_ID_HEADER = "X-Trace-ID"
SPAN_ID_HEADER = "X-Span-ID"
PARENT_SPAN_HEADER = "X-Parent-Span-ID"


def generate_trace_id() -> str:
    """Generate a new trace ID (UUID4 format)"""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a new span ID (shorter for readability)"""
    return uuid.uuid4().hex[:16]


def get_trace_id() -> str:
    """
    Get current trace ID or generate new one.
    Safe to call anywhere - returns existing or creates new.
    """
    trace_id = _trace_id_var.get()
    if trace_id is None:
        trace_id = generate_trace_id()
        _trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context"""
    _trace_id_var.set(trace_id)


def get_span_id() -> Optional[str]:
    """Get current span ID"""
    return _span_id_var.get()


def set_span_id(span_id: str) -> None:
    """Set span ID for current context"""
    _span_id_var.set(span_id)


def clear_trace_context() -> None:
    """Clear trace context (call at end of request)"""
    _trace_id_var.set(None)
    _span_id_var.set(None)


def trace_context() -> Dict[str, Any]:
    """
    Get trace context as dict for logging.
    
    Usage:
        logger.info("Message", extra=trace_context())
    """
    return {
        "trace_id": get_trace_id(),
        "span_id": get_span_id()
    }


def with_trace_context(func):
    """
    Decorator to propagate trace context into async function.
    Creates new span for the function execution.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Create new span for this function
        parent_span = get_span_id()
        new_span = generate_span_id()
        set_span_id(new_span)
        
        try:
            return await func(*args, **kwargs)
        finally:
            # Restore parent span
            if parent_span:
                set_span_id(parent_span)
    
    return wrapper


class TracingMiddleware:
    """
    FastAPI middleware for trace ID propagation.
    
    - Extracts trace ID from incoming X-Trace-ID header
    - Generates new trace ID if not present
    - Adds trace ID to response headers
    - Logs request with trace context
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract trace ID from headers
        headers = dict(scope.get("headers", []))
        trace_id = headers.get(TRACE_ID_HEADER.lower().encode(), b"").decode() or None
        
        if not trace_id:
            trace_id = generate_trace_id()
        
        # Set in context
        set_trace_id(trace_id)
        span_id = generate_span_id()
        set_span_id(span_id)
        
        # Add trace ID to response headers
        async def send_with_trace(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((TRACE_ID_HEADER.encode(), trace_id.encode()))
                headers.append((SPAN_ID_HEADER.encode(), span_id.encode()))
                message["headers"] = headers
            await send(message)
        
        try:
            await self.app(scope, receive, send_with_trace)
        finally:
            clear_trace_context()


def setup_tracing(app) -> None:
    """
    Setup tracing middleware for FastAPI application.
    
    This is NON-BREAKING - adds optional trace headers without
    affecting existing request/response behavior.
    
    Usage:
        from src.tracing import setup_tracing
        setup_tracing(app)
    """
    app.add_middleware(TracingMiddleware)
    logger.info("[TRACING] ✓ Distributed tracing middleware enabled")


def get_headers_for_propagation() -> Dict[str, str]:
    """
    Get headers to propagate trace context to external services.
    
    Usage:
        headers = get_headers_for_propagation()
        response = await client.post(url, headers=headers, ...)
    """
    return {
        TRACE_ID_HEADER: get_trace_id(),
        SPAN_ID_HEADER: get_span_id() or generate_span_id()
    }


class TraceLogger(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes trace context.
    
    Usage:
        from src.tracing import TraceLogger
        logger = TraceLogger(logging.getLogger(__name__))
        logger.info("Processing payment")  # Automatically includes trace_id
    """
    
    def process(self, msg, kwargs):
        # Add trace context to extra
        extra = kwargs.get('extra', {})
        extra.update(trace_context())
        kwargs['extra'] = extra
        return msg, kwargs
