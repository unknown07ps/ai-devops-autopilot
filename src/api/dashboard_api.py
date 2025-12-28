from fastapi import APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import redis
import json
import os

router = APIRouter(prefix="/api", tags=["dashboard"])

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

@router.get("/stats")
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


@router.get("/incidents")
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


@router.get("/anomalies")
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


@router.get("/services")
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


@router.get("/incident/{incident_id}")
async def get_incident_details(incident_id: str):
    """
    Get detailed information about a specific incident
    """
    try:
        # Parse service from incident_id
        service_name = incident_id.split('_')[0]
        
        incident_key = f"incidents:{service_name}"
        incidents = redis_client.lrange(incident_key, 0, -1)
        
        for incident_json in incidents:
            incident = json.loads(incident_json)
            if incident.get('id', f"{service_name}_{incident['timestamp']}") == incident_id:
                return incident
        
        raise HTTPException(status_code=404, detail="Incident not found")
    
    except Exception as e:
        print(f"[API ERROR] Failed to get incident details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incident/{incident_id}/resolve")
async def resolve_incident(incident_id: str):
    """
    Mark an incident as resolved
    """
    try:
        # Parse service from incident_id
        service_name = incident_id.split('_')[0]
        
        incident_key = f"incidents:{service_name}"
        incidents = redis_client.lrange(incident_key, 0, -1)
        
        updated = False
        for i, incident_json in enumerate(incidents):
            incident = json.loads(incident_json)
            if incident.get('id', f"{service_name}_{incident['timestamp']}") == incident_id:
                incident['status'] = 'resolved'
                incident['resolved_at'] = datetime.utcnow().isoformat()
                
                # Update in Redis
                redis_client.lset(incident_key, i, json.dumps(incident))
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        return {"status": "success", "message": "Incident marked as resolved"}
    
    except Exception as e:
        print(f"[API ERROR] Failed to resolve incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/timeseries")
async def get_metrics_timeseries(
    service: str,
    metric: str,
    hours: int = 24
):
    """
    Get time-series data for a specific metric
    """
    try:
        # Get baseline history
        key = f"baseline:{service}:{metric}"
        baseline_data = redis_client.get(key)
        
        if not baseline_data:
            return {"data": [], "service": service, "metric": metric}
        
        baseline = json.loads(baseline_data)
        values = baseline.get('values', [])
        
        # Create time series (mock timestamps for now)
        timeseries = []
        now = datetime.utcnow()
        
        for i, value in enumerate(values[-100:]):  # Last 100 values
            timestamp = (now - timedelta(minutes=100-i)).isoformat()
            timeseries.append({
                'timestamp': timestamp,
                'value': value
            })
        
        return {
            "data": timeseries,
            "service": service,
            "metric": metric,
            "mean": baseline.get('mean', 0),
            "std_dev": baseline.get('std_dev', 0)
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get timeseries: {e}")
        raise HTTPException(status_code=500, detail=str(e))