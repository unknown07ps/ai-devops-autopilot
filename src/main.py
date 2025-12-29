from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import redis
import json
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional

load_dotenv()

app = FastAPI(
    title="AI DevOps Autopilot",
    version="0.2.0",
    description="Autonomous incident detection, analysis, and response"
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "version": "0.2.0",
        "features": [
            "Real-time anomaly detection",
            "AI-powered root cause analysis",
            "Slack notifications",
            "Web dashboard"
        ]
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
    


# ============================================================================
# PHASE 2 API ENDPOINTS - ADD THESE
# ============================================================================

class ActionApproval(BaseModel):
    action_id: str
    approved_by: str
    notes: Optional[str] = None

@app.get("/api/v2/actions/pending")
async def get_pending_actions(limit: int = 20):
    """Get all pending actions awaiting approval"""
    try:
        action_ids = redis_client.lrange("actions:pending", 0, limit - 1)
        
        actions = []
        for action_id in action_ids:
            action_data = redis_client.get(f"action:{action_id.decode('utf-8')}")
            if action_data:
                action = json.loads(action_data)
                actions.append(action)
        
        return {"actions": actions, "total": len(actions)}
    except Exception as e:
        print(f"[API ERROR] get_pending_actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/actions/approve")
async def approve_action(approval: ActionApproval):
    """Approve an action for execution"""
    try:
        action_data = redis_client.get(f"action:{approval.action_id}")
        if not action_data:
            raise HTTPException(status_code=404, detail="Action not found")
        
        action = json.loads(action_data)
        
        if action['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve - action status is {action['status']}"
            )
        
        action['status'] = 'approved'
        action['approved_by'] = approval.approved_by
        action['approved_at'] = datetime.utcnow().isoformat()
        if approval.notes:
            action['approval_notes'] = approval.notes
        
        redis_client.setex(f"action:{approval.action_id}", 86400, json.dumps(action))
        redis_client.lrem("actions:pending", 0, approval.action_id)
        redis_client.lpush("actions:approved", approval.action_id)
        
        return {
            "status": "approved",
            "action_id": approval.action_id,
            "message": "Action approved and queued for execution"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] approve_action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/actions/history")
async def get_action_history(
    service: Optional[str] = None,
    limit: int = 50
):
    """Get action execution history"""
    try:
        actions = []
        
        if service:
            action_ids = redis_client.lrange(f"actions:history:{service}", 0, limit - 1)
        else:
            action_keys = redis_client.keys("action:*")
            action_ids = [key.decode('utf-8').split(':')[1] for key in action_keys[:limit]]
        
        for action_id in action_ids:
            if isinstance(action_id, bytes):
                action_id = action_id.decode('utf-8')
            
            action_data = redis_client.get(f"action:{action_id}")
            if action_data:
                actions.append(json.loads(action_data))
        
        actions.sort(key=lambda x: x.get('proposed_at', ''), reverse=True)
        
        return {"actions": actions[:limit], "total": len(actions)}
    except Exception as e:
        print(f"[API ERROR] get_action_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/learning/stats")
async def get_learning_stats():
    """Get overall learning statistics"""
    try:
        services = set()
        for key in redis_client.scan_iter("incident_history:*"):
            service = key.decode('utf-8').split(':')[1]
            services.add(service)
        
        total_incidents = 0
        total_actions = 0
        
        for service in services:
            incident_ids = redis_client.lrange(f"incident_history:{service}", 0, -1)
            total_incidents += len(incident_ids)
            
            for incident_id in incident_ids:
                incident_data = redis_client.get(f"incident_memory:{incident_id.decode('utf-8')}")
                if incident_data:
                    incident = json.loads(incident_data)
                    total_actions += len(incident.get('actions_taken', []))
        
        return {
            "total_incidents_learned": total_incidents,
            "total_actions_recorded": total_actions,
            "services_monitored": len(services),
            "learning_enabled": True
        }
    except Exception as e:
        print(f"[API ERROR] get_learning_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/learning/insights/{service}")
async def get_service_insights(service: str):
    """Get learning insights for a service"""
    try:
        incident_ids = redis_client.lrange(f"incident_history:{service}", 0, 99)
        
        if not incident_ids:
            return {
                "service": service,
                "message": "No incident history available",
                "total_incidents": 0
            }
        
        incidents = []
        for incident_id in incident_ids:
            incident_data = redis_client.get(f"incident_memory:{incident_id.decode('utf-8')}")
            if incident_data:
                incidents.append(json.loads(incident_data))
        
        total = len(incidents)
        successful = sum(1 for i in incidents if i.get('was_successful', False))
        
        return {
            "service": service,
            "total_incidents": total,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_resolution_time_minutes": 8.5,
            "top_root_causes": [],
            "most_effective_actions": []
        }
    except Exception as e:
        print(f"[API ERROR] get_service_insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/recommendations/{service}")
async def get_recommendations(service: str):
    """Get action recommendations for a service"""
    try:
        return {
            "service": service,
            "recommendations": [],
            "message": "No recommendations yet - need more incident history"
        }
    except Exception as e:
        print(f"[API ERROR] get_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/learning/similar-incidents")
async def find_similar_incidents(
    service: str,
    incident_id: Optional[str] = None,
    limit: int = 3
):
    """Find similar past incidents"""
    try:
        return {
            "service": service,
            "similar_incidents": [],
            "message": "No similar incidents found yet"
        }
    except Exception as e:
        print(f"[API ERROR] find_similar_incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/config")
async def get_config():
    """Get Phase 2 configuration"""
    return {
        "auto_approve_low_risk": os.getenv("AUTO_APPROVE_LOW_RISK", "false").lower() == "true",
        "dry_run_mode": os.getenv("DRY_RUN_MODE", "true").lower() == "true",
        "learning_enabled": True,
        "action_cooldown_seconds": 300,
        "max_concurrent_actions": 3
    }


# Background processing functions
async def check_for_anomalies(metrics: List[MetricPoint]):
    """
    Check metrics for anomalies - placeholder for now
    """
    print(f"[DETECTION] Checking {len(metrics)} metrics for anomalies...")

async def investigate_error_spike(logs: List[LogEntry]):
    """
    Investigate error log spikes
    """
    print(f"[ALERT] Error spike detected, investigating...")

async def monitor_deployment(deployment: DeploymentEvent):
    """
    Monitor deployment health post-deploy
    """
    print(f"[MONITOR] Tracking deployment {deployment.service}:{deployment.version}")


# ============================================================================
# DASHBOARD API ENDPOINTS (Inline to avoid import issues)
# ============================================================================

from datetime import timedelta

@app.get("/api/stats")
async def get_dashboard_stats():
    """
    Get high-level dashboard statistics
    """
    try:
        # Count active incidents
        active_incidents = 0
        services = redis_client.keys("incidents:*")
        
        for service_key in services:
            incidents = redis_client.lrange(service_key, 0, -1)
            for incident_json in incidents:
                incident = json.loads(incident_json)
                # Check if incident is recent (last 24h) and not resolved
                incident_time = datetime.fromisoformat(incident['timestamp'].replace('Z', '+00:00'))
                if (datetime.utcnow() - incident_time.replace(tzinfo=None)) < timedelta(hours=24):
                    if incident.get('status', 'active') == 'active':
                        active_incidents += 1
        
        # Count critical anomalies (last 24h)
        critical_anomalies = 0
        anomaly_keys = redis_client.keys("recent_anomalies:*")
        
        for key in anomaly_keys:
            anomalies = redis_client.lrange(key, 0, -1)
            for anomaly_json in anomalies:
                anomaly = json.loads(anomaly_json)
                if anomaly.get('severity') in ['critical', 'high']:
                    anomaly_time = datetime.fromisoformat(anomaly['detected_at'].replace('Z', '+00:00'))
                    if (datetime.utcnow() - anomaly_time.replace(tzinfo=None)) < timedelta(hours=24):
                        critical_anomalies += 1
        
        # Count healthy services
        all_services = set()
        for key in redis_client.keys("baseline:*"):
            service = key.decode('utf-8').split(':')[1]
            all_services.add(service)
        
        degraded_services = set()
        for key in redis_client.keys("recent_anomalies:*"):
            service = key.decode('utf-8').split(':')[1]
            degraded_services.add(service)
        
        healthy_services = len(all_services - degraded_services)
        total_services = len(all_services) if all_services else 1
        
        # Calculate average resolution time (mock for now)
        avg_resolution_minutes = 8.5
        
        return {
            "active_incidents": active_incidents,
            "critical_anomalies": critical_anomalies,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "avg_resolution_time_minutes": avg_resolution_minutes,
            "uptime_percent": round((healthy_services / total_services) * 100, 1) if total_services > 0 else 100
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/incidents")
async def get_incidents(
    status: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 50
):
    """
    Get all incidents with optional filtering
    """
    try:
        all_incidents = []
        
        # Get incidents from all services
        incident_keys = redis_client.keys("incidents:*")
        
        for key in incident_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            # Filter by service if specified
            if service and service_name != service:
                continue
            
            incidents_json = redis_client.lrange(key, 0, limit - 1)
            
            for incident_json in incidents_json:
                incident = json.loads(incident_json)
                
                # Add ID if not present
                if 'id' not in incident:
                    incident['id'] = f"{service_name}_{incident['timestamp']}"
                
                # Add status if not present
                if 'status' not in incident:
                    # Check if incident is old enough to be considered resolved
                    incident_time = datetime.fromisoformat(incident['timestamp'].replace('Z', '+00:00'))
                    time_since = datetime.utcnow() - incident_time.replace(tzinfo=None)
                    incident['status'] = 'resolved' if time_since > timedelta(hours=1) else 'active'
                
                # Filter by status if specified
                if status and incident['status'] != status:
                    continue
                
                # Extract key information
                analysis = incident.get('analysis', {})
                root_cause = analysis.get('root_cause', {})
                
                formatted_incident = {
                    'id': incident['id'],
                    'service': incident['service'],
                    'timestamp': incident['timestamp'],
                    'status': incident['status'],
                    'severity': analysis.get('severity', 'unknown'),
                    'root_cause': root_cause.get('description', 'Unknown'),
                    'confidence': root_cause.get('confidence', 0),
                    'reasoning': root_cause.get('reasoning', ''),
                    'anomaly_count': len(incident.get('anomalies', [])),
                    'customer_impact': analysis.get('estimated_customer_impact', 'Unknown'),
                    'recommended_actions': analysis.get('recommended_actions', []),
                    'resolved_at': incident.get('resolved_at')
                }
                
                all_incidents.append(formatted_incident)
        
        # Sort by timestamp (most recent first)
        all_incidents.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            "incidents": all_incidents[:limit],
            "total": len(all_incidents)
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anomalies")
async def get_anomalies(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100
):
    """
    Get recent anomalies with optional filtering
    """
    try:
        all_anomalies = []
        
        # Get anomalies from all services
        anomaly_keys = redis_client.keys("recent_anomalies:*")
        
        for key in anomaly_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            # Filter by service if specified
            if service and service_name != service:
                continue
            
            anomalies_json = redis_client.lrange(key, 0, limit - 1)
            
            for anomaly_json in anomalies_json:
                anomaly = json.loads(anomaly_json)
                
                # Filter by severity if specified
                if severity and anomaly.get('severity') != severity:
                    continue
                
                # Add ID if not present
                if 'id' not in anomaly:
                    anomaly['id'] = f"{service_name}_{anomaly.get('metric_name')}_{anomaly.get('detected_at')}"
                
                all_anomalies.append({
                    'id': anomaly['id'],
                    'service': anomaly.get('service', service_name),
                    'metric_name': anomaly.get('metric_name', 'unknown'),
                    'current_value': anomaly.get('current_value', 0),
                    'baseline_mean': anomaly.get('baseline_mean', 0),
                    'baseline_std_dev': anomaly.get('baseline_std_dev', 0),
                    'z_score': anomaly.get('z_score', 0),
                    'deviation_percent': anomaly.get('deviation_percent', 0),
                    'severity': anomaly.get('severity', 'unknown'),
                    'detected_at': anomaly.get('detected_at', datetime.utcnow().isoformat())
                })
        
        # Sort by timestamp (most recent first)
        all_anomalies.sort(key=lambda x: x['detected_at'], reverse=True)
        
        return {
            "anomalies": all_anomalies[:limit],
            "total": len(all_anomalies)
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/services")
async def get_services():
    """
    Get status of all monitored services
    """
    try:
        services_data = {}
        
        # Get all services from baselines
        baseline_keys = redis_client.keys("baseline:*")
        
        for key in baseline_keys:
            parts = key.decode('utf-8').split(':')
            if len(parts) >= 2:
                service_name = parts[1]
                
                if service_name not in services_data:
                    services_data[service_name] = {
                        'name': service_name,
                        'status': 'healthy',
                        'metrics': {},
                        'incident_count': 0,
                        'anomaly_count': 0
                    }
        
        # Check for recent anomalies to determine health
        anomaly_keys = redis_client.keys("recent_anomalies:*")
        
        for key in anomaly_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            if service_name in services_data:
                anomalies = redis_client.lrange(key, 0, 9)  # Last 10
                critical_count = 0
                
                for anomaly_json in anomalies:
                    anomaly = json.loads(anomaly_json)
                    if anomaly.get('severity') in ['critical', 'high']:
                        critical_count += 1
                
                services_data[service_name]['anomaly_count'] = len(anomalies)
                
                if critical_count > 0:
                    services_data[service_name]['status'] = 'degraded'
        
        # Get latest metrics for each service
        for service_name in services_data.keys():
            # Get latency baseline
            latency_key = f"baseline:{service_name}:api_latency_ms"
            latency_data = redis_client.get(latency_key)
            
            if latency_data:
                baseline = json.loads(latency_data)
                services_data[service_name]['metrics']['latency_ms'] = round(baseline.get('mean', 0), 2)
            
            # Get error rate baseline
            error_key = f"baseline:{service_name}:error_rate"
            error_data = redis_client.get(error_key)
            
            if error_data:
                baseline = json.loads(error_data)
                services_data[service_name]['metrics']['error_rate_percent'] = round(baseline.get('mean', 0), 2)
            
            # Count recent incidents
            incident_key = f"incidents:{service_name}"
            incidents = redis_client.lrange(incident_key, 0, -1)
            
            recent_incidents = 0
            for incident_json in incidents:
                incident = json.loads(incident_json)
                incident_time = datetime.fromisoformat(incident['timestamp'].replace('Z', '+00:00'))
                if (datetime.utcnow() - incident_time.replace(tzinfo=None)) < timedelta(hours=24):
                    recent_incidents += 1
            
            services_data[service_name]['incident_count'] = recent_incidents
        
        return {
            "services": list(services_data.values()),
            "total": len(services_data)
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve dashboard HTML (optional - for standalone deployment)

    
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """
    Serve the interactive dashboard UI directly from localhost:8000/dashboard
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI DevOps Autopilot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes spin { to { transform: rotate(360deg); } }
        .animate-spin { animation: spin 1s linear infinite; }
    </style>
</head>
<body class="bg-gray-100">
    <div id="app"></div>

    <script>
        const API_BASE = window.location.origin; // Uses same host automatically
        let currentTab = 'overview';
        let autoRefresh = false;
        let refreshInterval = null;

        async function fetchData() {
            try {
                const [stats, incidents, anomalies, services] = await Promise.all([
                    fetch(`${API_BASE}/api/stats`).then(r => r.ok ? r.json() : null),
                    fetch(`${API_BASE}/api/incidents`).then(r => r.ok ? r.json() : { incidents: [] }),
                    fetch(`${API_BASE}/api/anomalies`).then(r => r.ok ? r.json() : { anomalies: [] }),
                    fetch(`${API_BASE}/api/services`).then(r => r.ok ? r.json() : { services: [] })
                ]);

                render({ stats, incidents: incidents.incidents, anomalies: anomalies.anomalies, services: services.services });
            } catch (error) {
                renderError(error.message);
            }
        }

        function renderError(message) {
            document.getElementById('app').innerHTML = `
                <div class="min-h-screen flex items-center justify-center p-6">
                    <div class="bg-white rounded-xl shadow-lg p-8 max-w-2xl w-full">
                        <div class="text-center">
                            <div class="text-6xl mb-4">⚠️</div>
                            <h2 class="text-2xl font-bold text-gray-900 mb-4">Error Loading Dashboard</h2>
                            <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-left">
                                <p class="text-sm text-red-800">${message}</p>
                            </div>
                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6 text-left">
                                <p class="font-semibold text-gray-900 mb-3">Quick Fix:</p>
                                <ol class="space-y-2 text-sm text-gray-700">
                                    <li><strong>1. Check Worker:</strong> <code class="bg-gray-200 px-2 py-1 rounded">python src/worker.py</code></li>
                                    <li><strong>2. Generate Test Data:</strong> <code class="bg-gray-200 px-2 py-1 rounded">python test_dashboard.py</code></li>
                                    <li><strong>3. Refresh this page</strong></li>
                                </ol>
                            </div>
                            <button onclick="fetchData()" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700">
                                Retry Connection
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }

        function render(data) {
            const { stats, incidents, anomalies, services } = data;
            
            const app = document.getElementById('app');
            app.innerHTML = `
                <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
                    <!-- Header -->
                    <div class="bg-white border-b border-gray-200 shadow-sm">
                        <div class="max-w-7xl mx-auto px-6 py-6">
                            <div class="flex items-center justify-between mb-6">
                                <div>
                                    <h1 class="text-3xl font-bold text-gray-900 flex items-center gap-3">
                                        <span class="bg-gradient-to-br from-blue-600 to-purple-600 p-3 rounded-xl text-white">🧠</span>
                                        AI DevOps Autopilot
                                    </h1>
                                    <p class="text-gray-600 mt-1">Autonomous incident detection and response</p>
                                </div>
                                <div class="flex gap-3">
                                    <button onclick="toggleAutoRefresh()" class="${autoRefresh ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'} px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-opacity">
                                        ${autoRefresh ? '🔄' : '⏸️'} Auto-refresh ${autoRefresh ? 'ON' : 'OFF'}
                                    </button>
                                    <button onclick="fetchData()" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
                                        🔄 Refresh
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Tabs -->
                            <div class="flex gap-2 border-b border-gray-200">
                                <button onclick="switchTab('overview')" class="${currentTab === 'overview' ? 'bg-white text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-gray-600 hover:text-gray-900'} px-6 py-3 font-medium transition-colors">
                                    📊 Overview
                                </button>
                                <button onclick="switchTab('incidents')" class="${currentTab === 'incidents' ? 'bg-white text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-gray-600 hover:text-gray-900'} px-6 py-3 font-medium transition-colors">
                                    🚨 Incidents
                                </button>
                                <button onclick="switchTab('anomalies')" class="${currentTab === 'anomalies' ? 'bg-white text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-gray-600 hover:text-gray-900'} px-6 py-3 font-medium transition-colors">
                                    📈 Anomalies
                                </button>
                                <button onclick="switchTab('services')" class="${currentTab === 'services' ? 'bg-white text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-gray-600 hover:text-gray-900'} px-6 py-3 font-medium transition-colors">
                                    🖥️ Services
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Content -->
                    <div class="max-w-7xl mx-auto px-6 py-8">
                        ${currentTab === 'overview' ? renderOverview(stats, incidents) : ''}
                        ${currentTab === 'incidents' ? renderIncidents(incidents) : ''}
                        ${currentTab === 'anomalies' ? renderAnomalies(anomalies) : ''}
                        ${currentTab === 'services' ? renderServices(services) : ''}
                        
                        <div class="text-center text-sm text-gray-500 mt-8">
                            ⏰ Last updated: ${new Date().toLocaleTimeString()} • 
                            <a href="/docs" target="_blank" class="text-blue-600 hover:underline">API Docs</a> • 
                            <a href="https://github.com/unknown07ps/ai-devops-autopilot" target="_blank" class="text-blue-600 hover:underline">GitHub</a>
                        </div>
                    </div>
                </div>
            `;
        }

        function renderOverview(stats, incidents) {
            if (!stats) return '<div class="text-center py-12 text-gray-600">⏳ Loading...</div>';
            
            return `
                <div class="space-y-6">
                    <!-- Stats Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                            <div class="text-gray-600 text-sm font-medium mb-2">🚨 Active Incidents</div>
                            <div class="text-4xl font-bold ${stats.active_incidents > 0 ? 'text-red-600' : 'text-green-600'}">${stats.active_incidents}</div>
                            <div class="text-sm text-gray-500 mt-1">Requiring attention</div>
                        </div>
                        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                            <div class="text-gray-600 text-sm font-medium mb-2">⚠️ Critical Anomalies</div>
                            <div class="text-4xl font-bold text-orange-600">${stats.critical_anomalies}</div>
                            <div class="text-sm text-gray-500 mt-1">Last 24 hours</div>
                        </div>
                        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                            <div class="text-gray-600 text-sm font-medium mb-2">💚 Healthy Services</div>
                            <div class="text-4xl font-bold text-green-600">${stats.healthy_services}/${stats.total_services}</div>
                            <div class="text-sm text-gray-500 mt-1">${stats.uptime_percent}% uptime</div>
                        </div>
                        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                            <div class="text-gray-600 text-sm font-medium mb-2">⏱️ Avg Resolution</div>
                            <div class="text-4xl font-bold text-blue-600">${stats.avg_resolution_time_minutes}m</div>
                            <div class="text-sm text-gray-500 mt-1">Time to resolve</div>
                        </div>
                    </div>

                    <!-- Recent Incidents -->
                    <div>
                        <h2 class="text-2xl font-bold text-gray-900 mb-4">Recent Incidents</h2>
                        ${incidents && incidents.length > 0 ? `
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                ${incidents.slice(0, 6).map(inc => `
                                    <div class="bg-white rounded-lg border-2 border-gray-200 p-5 hover:shadow-xl hover:border-blue-400 transition-all cursor-pointer" onclick="showIncidentDetails('${inc.id}')">
                                        <div class="flex items-start justify-between mb-3">
                                            <div>
                                                <div class="font-bold text-lg text-gray-900">${inc.service}</div>
                                                <div class="text-sm text-gray-500">${formatTime(inc.timestamp)}</div>
                                            </div>
                                            <div class="flex flex-col items-end gap-2">
                                                <span class="px-3 py-1 rounded-full text-xs font-bold ${getSeverityClass(inc.severity)}">
                                                    ${getSeverityEmoji(inc.severity)} ${inc.severity.toUpperCase()}
                                                </span>
                                                <span class="text-xs px-2 py-1 rounded ${inc.status === 'active' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}">
                                                    ${inc.status}
                                                </span>
                                            </div>
                                        </div>
                                        <div class="text-sm text-gray-700 mb-3 leading-relaxed">${inc.root_cause}</div>
                                        <div class="flex items-center justify-between text-xs">
                                            <div class="flex gap-3 text-gray-600">
                                                <span>📊 ${inc.anomaly_count} anomalies</span>
                                                <span>🎯 ${inc.confidence}% confidence</span>
                                            </div>
                                            <span class="text-blue-600 font-medium">View Details →</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div class="bg-white rounded-lg border-2 border-gray-200 p-16 text-center">
                                <div class="text-7xl mb-4">✅</div>
                                <p class="text-xl text-gray-600 font-semibold mb-2">No incidents detected</p>
                                <p class="text-gray-500 mb-6">All systems operating normally</p>
                                <button onclick="window.open('/docs', '_blank')" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
                                    View API Docs
                                </button>
                            </div>
                        `}
                    </div>
                </div>
            `;
        }

        function renderIncidents(incidents) {
            return `
                <div>
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl font-bold text-gray-900">All Incidents</h2>
                        <span class="px-4 py-2 bg-blue-100 text-blue-800 rounded-lg font-semibold">
                            ${incidents ? incidents.length : 0} Total
                        </span>
                    </div>
                    ${incidents && incidents.length > 0 ? `
                        <div class="space-y-3">
                            ${incidents.map(inc => `
                                <div class="bg-white rounded-lg border-2 border-gray-200 p-6 hover:shadow-xl hover:border-blue-400 transition-all cursor-pointer" onclick="showIncidentDetails('${inc.id}')">
                                    <div class="flex items-center justify-between">
                                        <div class="flex items-center gap-4 flex-1">
                                            <div class="text-4xl">${getSeverityEmoji(inc.severity)}</div>
                                            <div class="flex-1">
                                                <div class="flex items-center gap-3 mb-2">
                                                    <div class="font-bold text-xl text-gray-900">${inc.service}</div>
                                                    <span class="px-3 py-1 rounded-full text-xs font-bold ${getSeverityClass(inc.severity)}">
                                                        ${inc.severity.toUpperCase()}
                                                    </span>
                                                </div>
                                                <div class="text-gray-700 mb-2">${inc.root_cause}</div>
                                                <div class="flex gap-4 text-sm text-gray-600">
                                                    <span>🕐 ${formatTime(inc.timestamp)}</span>
                                                    <span>📊 ${inc.anomaly_count} anomalies</span>
                                                    <span>🎯 ${inc.confidence}% confidence</span>
                                                    <span class="font-semibold ${inc.status === 'active' ? 'text-red-600' : 'text-green-600'}">
                                                        ${inc.status === 'active' ? '🔴' : '✅'} ${inc.status}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="text-blue-600 font-medium text-lg">→</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<div class="bg-white rounded-lg border-2 border-gray-200 p-16 text-center"><div class="text-6xl mb-4">✅</div><p class="text-xl text-gray-600">No incidents</p></div>'}
                </div>
            `;
        }

        function renderAnomalies(anomalies) {
            return `
                <div>
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl font-bold text-gray-900">Recent Anomalies</h2>
                        <span class="px-4 py-2 bg-orange-100 text-orange-800 rounded-lg font-semibold">
                            ${anomalies ? anomalies.length : 0} Detected
                        </span>
                    </div>
                    ${anomalies && anomalies.length > 0 ? `
                        <div class="bg-white rounded-lg border-2 border-gray-200 overflow-hidden shadow-sm">
                            <div class="overflow-x-auto">
                                <table class="w-full">
                                    <thead class="bg-gradient-to-r from-gray-50 to-gray-100 border-b-2 border-gray-300">
                                        <tr>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Service</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Metric</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Current</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Baseline</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Deviation</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Severity</th>
                                            <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Time</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-gray-200">
                                        ${anomalies.map((a, idx) => `
                                            <tr class="hover:bg-blue-50 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}">
                                                <td class="px-6 py-4 text-sm font-bold text-gray-900">${a.service}</td>
                                                <td class="px-6 py-4 text-sm text-gray-700">${a.metric_name}</td>
                                                <td class="px-6 py-4 text-sm font-bold text-red-600">${a.current_value.toFixed(2)}</td>
                                                <td class="px-6 py-4 text-sm text-gray-600">${a.baseline_mean.toFixed(2)}</td>
                                                <td class="px-6 py-4">
                                                    <span class="font-bold text-sm ${a.deviation_percent > 0 ? 'text-red-600' : 'text-green-600'}">
                                                        ${a.deviation_percent > 0 ? '🔺' : '🔻'} ${Math.abs(a.deviation_percent).toFixed(1)}%
                                                    </span>
                                                </td>
                                                <td class="px-6 py-4">
                                                    <span class="px-3 py-1 rounded-full text-xs font-bold ${getSeverityClass(a.severity)}">
                                                        ${a.severity}
                                                    </span>
                                                </td>
                                                <td class="px-6 py-4 text-sm text-gray-600">${formatTime(a.detected_at)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : '<div class="bg-white rounded-lg border-2 border-gray-200 p-16 text-center"><div class="text-6xl mb-4">📊</div><p class="text-xl text-gray-600">No anomalies detected</p></div>'}
                </div>
            `;
        }

        function renderServices(services) {
            return `
                <div>
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl font-bold text-gray-900">Service Health</h2>
                        <span class="px-4 py-2 bg-green-100 text-green-800 rounded-lg font-semibold">
                            ${services ? services.length : 0} Services
                        </span>
                    </div>
                    ${services && services.length > 0 ? `
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            ${services.map(s => `
                                <div class="bg-white rounded-lg border-2 border-gray-200 p-6 hover:shadow-xl transition-all">
                                    <div class="flex items-center justify-between mb-4">
                                        <div>
                                            <h3 class="font-bold text-xl text-gray-900">${s.name}</h3>
                                            <div class="flex items-center gap-2 mt-2">
                                                <div class="w-3 h-3 rounded-full ${s.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-orange-500'}"></div>
                                                <span class="text-sm font-semibold ${s.status === 'healthy' ? 'text-green-700' : 'text-orange-700'}">${s.status.toUpperCase()}</span>
                                            </div>
                                        </div>
                                        <div class="text-4xl">🖥️</div>
                                    </div>
                                    ${s.metrics ? `
                                        <div class="grid grid-cols-2 gap-3 mb-4">
                                            ${s.metrics.latency_ms !== undefined ? `
                                                <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
                                                    <div class="text-xs text-gray-600 mb-1">⚡ Latency</div>
                                                    <div class="text-xl font-bold text-blue-700">${s.metrics.latency_ms}<span class="text-sm">ms</span></div>
                                                </div>
                                            ` : ''}
                                            ${s.metrics.error_rate_percent !== undefined ? `
                                                <div class="bg-red-50 rounded-lg p-3 border border-red-200">
                                                    <div class="text-xs text-gray-600 mb-1">❌ Errors</div>
                                                    <div class="text-xl font-bold text-red-700">${s.metrics.error_rate_percent}<span class="text-sm">%</span></div>
                                                </div>
                                            ` : ''}
                                        </div>
                                    ` : ''}
                                    <div class="flex justify-between pt-3 border-t border-gray-200">
                                        <div class="text-center flex-1">
                                            <div class="text-2xl font-bold text-orange-600">${s.anomaly_count}</div>
                                            <div class="text-xs text-gray-600">Anomalies</div>
                                        </div>
                                        <div class="text-center flex-1 border-l border-gray-200">
                                            <div class="text-2xl font-bold text-red-600">${s.incident_count}</div>
                                            <div class="text-xs text-gray-600">Incidents</div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<div class="bg-white rounded-lg border-2 border-gray-200 p-16 text-center"><div class="text-6xl mb-4">🖥️</div><p class="text-xl text-gray-600">No services monitored</p><p class="text-sm text-gray-500 mt-2">Run test_dashboard.py to generate data</p></div>'}
                </div>
            `;
        }

        function getSeverityClass(severity) {
            const classes = {
                critical: 'bg-red-100 text-red-800 border border-red-300',
                high: 'bg-orange-100 text-orange-800 border border-orange-300',
                medium: 'bg-yellow-100 text-yellow-800 border border-yellow-300',
                low: 'bg-blue-100 text-blue-800 border border-blue-300'
            };
            return classes[severity] || classes.medium;
        }

        function getSeverityEmoji(severity) {
            const emojis = {
                critical: '🔴',
                high: '🟠',
                medium: '🟡',
                low: '🔵'
            };
            return emojis[severity] || '⚪';
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = Math.floor((now - date) / 60000);
            if (diff < 1) return 'Just now';
            if (diff < 60) return `${diff}m ago`;
            if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }

        function switchTab(tab) {
            currentTab = tab;
            fetchData();
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            if (autoRefresh) {
                refreshInterval = setInterval(fetchData, 10000);
            } else {
                clearInterval(refreshInterval);
            }
            fetchData();
        }

        function showIncidentDetails(id) {
            alert('Incident details modal coming in Phase 2!\\n\\nIncident ID: ' + id + '\\n\\nFeatures:\\n- Full root cause analysis\\n- Recommended actions\\n- One-click remediation');
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', fetchData);
        fetchData();
    </script>
</body>
</html>
    """
    
@app.get("/dashboard/phase2", response_class=HTMLResponse)
async def get_phase2_dashboard():
    """
    Serve Phase 2 dashboard with enhanced features
    """
    try:
        # Explicitly use UTF-8 encoding to handle emojis and special characters
        with open('dashboard_phase2.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <body style="font-family: sans-serif; padding: 40px; text-align: center;">
                <h1>❌ Phase 2 Dashboard Not Found</h1>
                <p>Please ensure <code>dashboard_phase2.html</code> exists in the project root.</p>
                <p><a href="/dashboard">← Back to Phase 1 Dashboard</a></p>
            </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: sans-serif; padding: 40px; text-align: center;">
                <h1>❌ Error Loading Dashboard</h1>
                <p>Error: {str(e)}</p>
                <p><a href="/dashboard">← Back to Phase 1 Dashboard</a></p>
            </body>
        </html>
        """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)