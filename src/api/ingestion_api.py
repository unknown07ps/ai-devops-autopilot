"""
Ingestion API Router - Data ingestion endpoints for metrics, logs, and deployments
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import redis

from src.rate_limiting import limiter

router = APIRouter(tags=["Ingestion"])

# These will be injected from main.py
_redis_client = None


def configure(redis_client):
    """Configure router with shared dependencies from main.py"""
    global _redis_client
    _redis_client = redis_client


# Data Models
class MetricPoint(BaseModel):
    timestamp: datetime
    metric_name: str
    value: float
    labels: Dict[str, str] = {}


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    service: str
    labels: Dict[str, str] = {}


class DeploymentEvent(BaseModel):
    timestamp: datetime
    service: str
    version: str
    status: str
    metadata: Dict[str, Any] = {}


# Background task placeholders - will be overridden by main.py
def check_for_anomalies(metrics: List[MetricPoint]):
    """Check metrics for anomalies"""
    pass


def investigate_error_spike(logs: List[LogEntry]):
    """Investigate error log spikes"""
    pass


def monitor_deployment(deployment: DeploymentEvent):
    """Monitor deployment health post-deploy"""
    pass


# Allow main.py to set these functions
_check_for_anomalies = check_for_anomalies
_investigate_error_spike = investigate_error_spike
_monitor_deployment = monitor_deployment


def set_background_tasks(check_anomalies_fn, investigate_errors_fn, monitor_deploy_fn):
    """Set background task functions from main.py"""
    global _check_for_anomalies, _investigate_error_spike, _monitor_deployment
    _check_for_anomalies = check_anomalies_fn
    _investigate_error_spike = investigate_errors_fn
    _monitor_deployment = monitor_deploy_fn


@router.post("/ingest/metrics")
@limiter.limit("200/minute")  # High-volume data ingestion
async def ingest_metrics(request: Request, metrics: List[MetricPoint], background_tasks: BackgroundTasks):
    """Ingest metrics in Prometheus-compatible format"""
    try:
        for metric in metrics:
            event = {
                "type": "metric",
                "data": metric.model_dump_json(),
                "timestamp": metric.timestamp.isoformat()
            }
            try:
                _redis_client.xadd("events:metrics", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    metric_key = f"metric:{metric.labels.get('service', 'unknown')}:{metric.timestamp.timestamp()}"
                    _redis_client.setex(metric_key, 3600, metric.model_dump_json())
                else:
                    raise
        
        background_tasks.add_task(_check_for_anomalies, metrics)
        
        return {
            "status": "accepted",
            "count": len(metrics),
            "message": "Metrics queued for analysis"
        }
    except Exception as e:
        print(f"[ERROR] Metrics ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/logs")
@limiter.limit("200/minute")  # High-volume data ingestion
async def ingest_logs(request: Request, logs: List[LogEntry], background_tasks: BackgroundTasks):
    """Ingest application logs"""
    try:
        error_count = 0
        for log in logs:
            event = {
                "type": "log",
                "data": log.model_dump_json(),
                "timestamp": log.timestamp.isoformat()
            }
            try:
                _redis_client.xadd("events:logs", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    _redis_client.lpush(f"logs:{log.service}", log.model_dump_json())
                    _redis_client.ltrim(f"logs:{log.service}", 0, 999)
                else:
                    raise
            
            if log.level in ["ERROR", "CRITICAL"]:
                error_count += 1
        
        if error_count > 5:
            background_tasks.add_task(_investigate_error_spike, logs)
        
        return {
            "status": "accepted",
            "count": len(logs),
            "errors_detected": error_count
        }
    except Exception as e:
        print(f"[ERROR] Log ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/deployment")
@limiter.limit("60/minute")  # Deployment tracking
async def ingest_deployment(request: Request, deployment: DeploymentEvent, background_tasks: BackgroundTasks):
    """Track deployment events"""
    try:
        event = {
            "type": "deployment",
            "data": deployment.model_dump_json(),
            "timestamp": deployment.timestamp.isoformat()
        }
        try:
            _redis_client.xadd("events:deployments", event)
        except redis.exceptions.ResponseError as e:
            if 'unknown command' not in str(e).lower():
                raise
        
        _redis_client.zadd(
            f"deployments:{deployment.service}",
            {deployment.version: deployment.timestamp.timestamp()}
        )
        
        background_tasks.add_task(_monitor_deployment, deployment)
        
        return {
            "status": "tracked",
            "service": deployment.service,
            "version": deployment.version
        }
    except Exception as e:
        print(f"[ERROR] Deployment ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prometheus/write")
async def prometheus_write_handler(request: Request):
    """
    Receive metrics from Prometheus remote_write
    """
    try:
        import snappy
        from prometheus_client.parser import text_string_to_metric_families
        
        body = await request.body()
        
        # Decompress
        decompressed = snappy.decompress(body)
        
        # Convert to your format and ingest
        # Note: parse_prometheus_metrics and ingest_metric need to be implemented
        # metrics = parse_prometheus_metrics(decompressed)
        # for metric in metrics:
        #     await ingest_metric(metric)
        
        return {"status": "success"}
    except ImportError:
        raise HTTPException(status_code=501, detail="Prometheus remote_write not supported - snappy not installed")
    except Exception as e:
        print(f"[ERROR] Prometheus write failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
