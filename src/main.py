from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime
import redis
import json
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI DevOps Autopilot", version="0.1.0")

# Redis connection for event streaming
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

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
    status: str  # success, failed, in_progress
    metadata: Dict[str, Any] = {}

# Health check
@app.get("/")
async def root():
    return {
        "status": "operational",
        "service": "AI DevOps Autopilot",
        "version": "0.1.0"
    }

@app.get("/health")
async def health():
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except:
        return {"status": "degraded", "redis": "disconnected"}

# Ingestion endpoints
@app.post("/ingest/metrics")
async def ingest_metrics(metrics: List[MetricPoint], background_tasks: BackgroundTasks):
    """
    Ingest metrics in Prometheus-compatible format
    """
    try:
        # Store in Redis for processing
        for metric in metrics:
            event = {
                "type": "metric",
                "data": metric.model_dump_json(),
                "timestamp": metric.timestamp.isoformat()
            }
            try:
                # Try using streams first
                redis_client.xadd("events:metrics", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    # Fallback to simple list if streams not available
                    metric_key = f"metric:{metric.labels.get('service', 'unknown')}:{metric.timestamp.timestamp()}"
                    redis_client.setex(metric_key, 3600, metric.model_dump_json())
                else:
                    raise
        
        # Trigger anomaly detection in background
        background_tasks.add_task(check_for_anomalies, metrics)
        
        return {
            "status": "accepted",
            "count": len(metrics),
            "message": "Metrics queued for analysis"
        }
    except Exception as e:
        print(f"[ERROR] Metrics ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/logs")
async def ingest_logs(logs: List[LogEntry], background_tasks: BackgroundTasks):
    """
    Ingest application logs
    """
    try:
        error_count = 0
        for log in logs:
            event = {
                "type": "log",
                "data": log.model_dump_json(),
                "timestamp": log.timestamp.isoformat()
            }
            try:
                redis_client.xadd("events:logs", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    # Fallback - just store in a simple list
                    redis_client.lpush(f"logs:{log.service}", log.model_dump_json())
                    redis_client.ltrim(f"logs:{log.service}", 0, 999)
                else:
                    raise
            
            if log.level in ["ERROR", "CRITICAL"]:
                error_count += 1
        
        # If we see error spikes, trigger investigation
        if error_count > 5:
            background_tasks.add_task(investigate_error_spike, logs)
        
        return {
            "status": "accepted",
            "count": len(logs),
            "errors_detected": error_count
        }
    except Exception as e:
        print(f"[ERROR] Log ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/deployment")
async def ingest_deployment(deployment: DeploymentEvent, background_tasks: BackgroundTasks):
    """
    Track deployment events
    """
    try:
        event = {
            "type": "deployment",
            "data": deployment.model_dump_json(),
            "timestamp": deployment.timestamp.isoformat()
        }
        try:
            redis_client.xadd("events:deployments", event)
        except redis.exceptions.ResponseError as e:
            if 'unknown command' not in str(e).lower():
                raise
        
        # Store deployment in a sorted set for quick lookups
        redis_client.zadd(
            f"deployments:{deployment.service}",
            {deployment.version: deployment.timestamp.timestamp()}
        )
        
        # Monitor the deployment
        background_tasks.add_task(monitor_deployment, deployment)
        
        return {
            "status": "tracked",
            "service": deployment.service,
            "version": deployment.version
        }
    except Exception as e:
        print(f"[ERROR] Deployment ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background processing functions
async def check_for_anomalies(metrics: List[MetricPoint]):
    """
    Check metrics for anomalies - placeholder for now
    """
    print(f"[DETECTION] Checking {len(metrics)} metrics for anomalies...")
    # TODO: Implement statistical anomaly detection

async def investigate_error_spike(logs: List[LogEntry]):
    """
    Investigate error log spikes
    """
    print(f"[ALERT] Error spike detected, investigating...")
    # TODO: Trigger AI analysis

async def monitor_deployment(deployment: DeploymentEvent):
    """
    Monitor deployment health post-deploy
    """
    print(f"[MONITOR] Tracking deployment {deployment.service}:{deployment.version}")
    # TODO: Compare metrics before/after deployment

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)