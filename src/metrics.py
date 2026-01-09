"""
Prometheus-Compatible Metrics Collection

Provides counters, histograms, and gauges for observability.
Non-blocking, optional integration - does not affect business logic.

Usage:
    from src.metrics import (
        REQUEST_COUNT, REQUEST_LATENCY, QUEUE_DEPTH,
        increment_counter, observe_latency, setup_metrics
    )
    
    # In middleware
    setup_metrics(app)
    
    # In code
    REQUEST_COUNT.labels(endpoint="/api/health", method="GET", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/api/health").observe(0.025)
"""

import time
import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Optional Prometheus client - graceful degradation if not installed
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
    from prometheus_client import CollectorRegistry, multiprocess
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("[METRICS] prometheus_client not installed - metrics disabled")


# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

if PROMETHEUS_AVAILABLE:
    # Request metrics
    REQUEST_COUNT = Counter(
        'deployr_http_requests_total',
        'Total HTTP requests',
        ['endpoint', 'method', 'status']
    )
    
    REQUEST_LATENCY = Histogram(
        'deployr_http_request_duration_seconds',
        'HTTP request latency in seconds',
        ['endpoint'],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    
    # AI inference metrics
    AI_INFERENCE_COUNT = Counter(
        'deployr_ai_inference_total',
        'Total AI inference requests',
        ['model', 'status']  # status: success, failure, timeout
    )
    
    AI_INFERENCE_LATENCY = Histogram(
        'deployr_ai_inference_duration_seconds',
        'AI inference latency in seconds',
        ['model'],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
    )
    
    # Queue metrics
    QUEUE_DEPTH = Gauge(
        'deployr_queue_depth',
        'Current queue depth',
        ['queue_name']  # pending_actions, processed_actions
    )
    
    # Incident metrics
    INCIDENT_COUNT = Counter(
        'deployr_incidents_total',
        'Total incidents detected',
        ['service', 'severity']
    )
    
    ACTION_COUNT = Counter(
        'deployr_actions_total',
        'Total actions taken',
        ['action_type', 'status']  # status: approved, rejected, executed, failed
    )
    
    # Circuit breaker metrics
    CIRCUIT_BREAKER_STATE = Gauge(
        'deployr_circuit_breaker_state',
        'Circuit breaker state (0=closed, 1=half_open, 2=open)',
        ['service']
    )
    
    CIRCUIT_BREAKER_FAILURES = Counter(
        'deployr_circuit_breaker_failures_total',
        'Circuit breaker failure count',
        ['service']
    )
    
    # Application info
    APP_INFO = Info(
        'deployr_app',
        'Application information'
    )
    APP_INFO.info({
        'version': '0.3.0',
        'environment': os.getenv('ENVIRONMENT', 'development')
    })

else:
    # Dummy metrics when prometheus_client not available
    class DummyMetric:
        def labels(self, **kwargs): return self
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def set(self, value): pass
        def observe(self, value): pass
        def info(self, info): pass
    
    REQUEST_COUNT = DummyMetric()
    REQUEST_LATENCY = DummyMetric()
    AI_INFERENCE_COUNT = DummyMetric()
    AI_INFERENCE_LATENCY = DummyMetric()
    QUEUE_DEPTH = DummyMetric()
    INCIDENT_COUNT = DummyMetric()
    ACTION_COUNT = DummyMetric()
    CIRCUIT_BREAKER_STATE = DummyMetric()
    CIRCUIT_BREAKER_FAILURES = DummyMetric()
    APP_INFO = DummyMetric()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def increment_counter(counter, labels: Dict[str, str], amount: int = 1):
    """Safely increment a counter with labels"""
    try:
        counter.labels(**labels).inc(amount)
    except Exception as e:
        logger.debug(f"[METRICS] Failed to increment counter: {e}")


def observe_latency(histogram, labels: Dict[str, str], duration: float):
    """Safely record latency observation"""
    try:
        histogram.labels(**labels).observe(duration)
    except Exception as e:
        logger.debug(f"[METRICS] Failed to observe latency: {e}")


def set_gauge(gauge, labels: Dict[str, str], value: float):
    """Safely set a gauge value"""
    try:
        gauge.labels(**labels).set(value)
    except Exception as e:
        logger.debug(f"[METRICS] Failed to set gauge: {e}")


@contextmanager
def timed_operation(histogram, labels: Dict[str, str]):
    """Context manager for timing operations"""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        observe_latency(histogram, labels, duration)


def track_request(endpoint: str, method: str):
    """Decorator to track request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            status = "200"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start
                increment_counter(REQUEST_COUNT, {
                    "endpoint": endpoint,
                    "method": method,
                    "status": status
                })
                observe_latency(REQUEST_LATENCY, {"endpoint": endpoint}, duration)
        return wrapper
    return decorator


# ============================================================================
# FASTAPI INTEGRATION
# ============================================================================

class MetricsMiddleware:
    """ASGI middleware for automatic request metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        status_code = "200"
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 200))
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time
            path = scope.get("path", "/unknown")
            method = scope.get("method", "GET")
            
            # Skip metrics endpoint itself
            if path != "/metrics":
                increment_counter(REQUEST_COUNT, {
                    "endpoint": path,
                    "method": method,
                    "status": status_code
                })
                observe_latency(REQUEST_LATENCY, {"endpoint": path}, duration)


def setup_metrics(app) -> None:
    """
    Setup metrics middleware and /metrics endpoint for FastAPI.
    
    Non-breaking - adds metrics collection without affecting behavior.
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("[METRICS] prometheus_client not available - skipping setup")
        return
    
    # Add middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add /metrics endpoint
    from fastapi import Response
    
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    
    logger.info("[METRICS] ✓ Prometheus metrics enabled at /metrics")
