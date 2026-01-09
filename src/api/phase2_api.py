"""
Phase 2 API Endpoints
Action management, approval workflow, and learning insights
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timezone
import redis
import json
import os

from src.rate_limiting import limiter

router = APIRouter(prefix="/api/v2", tags=["phase2"])

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Pydantic models
class ActionApproval(BaseModel):
    action_id: str
    approved_by: str
    notes: Optional[str] = None

class ActionExecution(BaseModel):
    action_id: str
    dry_run: bool = True

# ============================================================================
# ACTION MANAGEMENT
# ============================================================================

@router.get("/actions/pending")
async def get_pending_actions(limit: int = 20):
    """
    Get all pending actions awaiting approval
    """
    try:
        action_ids = redis_client.lrange("actions:pending", 0, limit - 1)
        
        actions = []
        for action_id in action_ids:
            action_data = redis_client.get(f"action:{action_id.decode('utf-8')}")
            if action_data:
                action = json.loads(action_data)
                actions.append(action)
        
        return {
            "actions": actions,
            "total": len(actions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/approve")
@limiter.limit("30/minute")  # Action approval rate limit
async def approve_action(request: Request, approval: ActionApproval, background_tasks: BackgroundTasks):
    """
    Approve an action for execution
    """
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
        
        # Update action
        action['status'] = 'approved'
        action['approved_by'] = approval.approved_by
        action['approved_at'] = datetime.now(timezone.utc).isoformat()
        if approval.notes:
            action['approval_notes'] = approval.notes
        
        redis_client.setex(f"action:{approval.action_id}", 86400, json.dumps(action))
        
        # Move to approved queue
        redis_client.lrem("actions:pending", 0, approval.action_id)
        redis_client.lpush("actions:approved", approval.action_id)
        
        # Trigger execution in background
        # background_tasks.add_task(execute_action, approval.action_id)
        
        return {
            "status": "approved",
            "action_id": approval.action_id,
            "message": "Action approved and queued for execution"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/reject")
@limiter.limit("30/minute")  # Action rejection rate limit
async def reject_action(request: Request, approval: ActionApproval):
    """
    Reject a proposed action
    """
    try:
        action_data = redis_client.get(f"action:{approval.action_id}")
        if not action_data:
            raise HTTPException(status_code=404, detail="Action not found")
        
        action = json.loads(action_data)
        action['status'] = 'rejected'
        action['rejected_by'] = approval.approved_by
        action['rejected_at'] = datetime.now(timezone.utc).isoformat()
        if approval.notes:
            action['rejection_reason'] = approval.notes
        
        redis_client.setex(f"action:{approval.action_id}", 86400, json.dumps(action))
        redis_client.lrem("actions:pending", 0, approval.action_id)
        
        return {
            "status": "rejected",
            "action_id": approval.action_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/history")
async def get_action_history(
    service: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Get action execution history
    """
    try:
        actions = []
        
        if service:
            # Get history for specific service
            action_ids = redis_client.lrange(f"actions:history:{service}", 0, limit - 1)
        else:
            # Get all action keys
            action_keys = redis_client.keys("action:*")
            action_ids = [key.decode('utf-8').split(':')[1] for key in action_keys[:limit]]
        
        for action_id in action_ids:
            if isinstance(action_id, bytes):
                action_id = action_id.decode('utf-8')
            
            action_data = redis_client.get(f"action:{action_id}")
            if action_data:
                action = json.loads(action_data)
                
                # Filter by status if specified
                if status and action.get('status') != status:
                    continue
                
                actions.append(action)
        
        # Sort by timestamp
        actions.sort(key=lambda x: x.get('proposed_at', ''), reverse=True)
        
        return {
            "actions": actions[:limit],
            "total": len(actions)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{action_id}")
async def get_action_details(action_id: str):
    """
    Get detailed information about a specific action
    """
    try:
        action_data = redis_client.get(f"action:{action_id}")
        if not action_data:
            raise HTTPException(status_code=404, detail="Action not found")
        
        action = json.loads(action_data)
        
        # Get related incident
        incident_data = None
        if action.get('incident_id'):
            service = action.get('service')
            incidents = redis_client.lrange(f"incidents:{service}", 0, -1)
            
            for incident_json in incidents:
                incident = json.loads(incident_json)
                if incident['id'] == action['incident_id']:
                    incident_data = incident
                    break
        
        return {
            "action": action,
            "related_incident": incident_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LEARNING & INSIGHTS
# ============================================================================

@router.get("/learning/stats")
async def get_learning_stats():
    """
    Get overall learning statistics
    """
    try:
        # Count incidents across all services
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/insights/{service}")
async def get_service_insights(service: str):
    """
    Get learning insights for a specific service
    """
    try:
        incident_ids = redis_client.lrange(f"incident_history:{service}", 0, 99)
        
        if not incident_ids:
            return {
                "service": service,
                "message": "No incident history available"
            }
        
        incidents = []
        for incident_id in incident_ids:
            incident_data = redis_client.get(f"incident_memory:{incident_id.decode('utf-8')}")
            if incident_data:
                incidents.append(json.loads(incident_data))
        
        # Calculate insights
        total = len(incidents)
        successful = sum(1 for i in incidents if i.get('was_successful'))
        
        resolution_times = [i.get('resolution_time_seconds', 0) for i in incidents]
        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Top root causes
        causes = {}
        for incident in incidents:
            cause = incident['root_cause'].get('description', 'Unknown')
            causes[cause] = causes.get(cause, 0) + 1
        
        top_causes = sorted(causes.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Most effective actions
        action_stats = {}
        for incident in incidents:
            if incident.get('was_successful'):
                for action in incident.get('actions_taken', []):
                    action_type = action.get('action_type', 'unknown')
                    if action_type not in action_stats:
                        action_stats[action_type] = {"success": 0, "total": 0}
                    action_stats[action_type]["total"] += 1
                    action_stats[action_type]["success"] += 1
        
        effective_actions = [
            {
                "action_type": action_type,
                "success_rate": (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                "usage_count": stats["total"]
            }
            for action_type, stats in action_stats.items()
        ]
        effective_actions.sort(key=lambda x: x['success_rate'], reverse=True)
        
        return {
            "service": service,
            "total_incidents": total,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_resolution_time_minutes": avg_resolution / 60,
            "top_root_causes": [{"cause": cause, "count": count} for cause, count in top_causes],
            "most_effective_actions": effective_actions[:3]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/similar-incidents")
async def find_similar_incidents(
    service: str,
    incident_id: Optional[str] = None,
    limit: int = 5
):
    """
    Find similar past incidents for pattern matching
    """
    try:
        # Get the reference incident
        if incident_id:
            incident_data = redis_client.get(f"incident_memory:{incident_id}")
            if not incident_data:
                raise HTTPException(status_code=404, detail="Incident not found")
            reference = json.loads(incident_data)
        else:
            # Get latest incident for service
            incident_ids = redis_client.lrange(f"incident_history:{service}", 0, 0)
            if not incident_ids:
                return {"similar_incidents": [], "message": "No reference incident"}
            
            incident_data = redis_client.get(f"incident_memory:{incident_ids[0].decode('utf-8')}")
            reference = json.loads(incident_data)
        
        # Find similar incidents (simplified version)
        all_incidents = redis_client.lrange(f"incident_history:{service}", 0, 49)
        
        similar = []
        for inc_id in all_incidents:
            inc_data = redis_client.get(f"incident_memory:{inc_id.decode('utf-8')}")
            if inc_data:
                incident = json.loads(inc_data)
                if incident['id'] != reference['id']:
                    # Simple similarity based on root cause matching
                    if reference['root_cause'].get('description') in incident['root_cause'].get('description', ''):
                        incident['similarity_score'] = 0.8
                        similar.append(incident)
        
        return {
            "reference_incident": reference['id'],
            "similar_incidents": similar[:limit]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ACTION RECOMMENDATIONS
# ============================================================================

@router.get("/recommendations/{service}")
async def get_action_recommendations(service: str):
    """
    Get recommended actions based on learning for a service
    """
    try:
        # Get recent anomalies
        anomalies = []
        anomaly_data = redis_client.lrange(f"recent_anomalies:{service}", 0, 9)
        
        for anomaly_json in anomaly_data:
            anomalies.append(json.loads(anomaly_json))
        
        if not anomalies:
            return {
                "service": service,
                "recommendations": [],
                "message": "No recent anomalies to base recommendations on"
            }
        
        # Find similar past incidents
        incident_ids = redis_client.lrange(f"incident_history:{service}", 0, 19)
        
        action_scores = {}
        
        for incident_id in incident_ids:
            incident_data = redis_client.get(f"incident_memory:{incident_id.decode('utf-8')}")
            if not incident_data:
                continue
            
            incident = json.loads(incident_data)
            
            if not incident.get('was_successful'):
                continue
            
            for action in incident.get('actions_taken', []):
                action_type = action.get('action_type')
                
                if action_type not in action_scores:
                    action_scores[action_type] = {
                        "count": 0,
                        "avg_resolution_time": 0,
                        "example": action
                    }
                
                action_scores[action_type]["count"] += 1
                action_scores[action_type]["avg_resolution_time"] += incident.get('resolution_time_seconds', 0)
        
        # Calculate recommendations
        recommendations = []
        for action_type, stats in action_scores.items():
            if stats["count"] > 0:
                recommendations.append({
                    "action_type": action_type,
                    "confidence": min(stats["count"] * 10, 100),
                    "success_count": stats["count"],
                    "avg_resolution_time_seconds": stats["avg_resolution_time"] / stats["count"],
                    "example_params": stats["example"].get('params', {})
                })
        
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            "service": service,
            "recommendations": recommendations[:5],
            "based_on_incidents": len(incident_ids)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONFIGURATION
# ============================================================================

@router.get("/config")
async def get_configuration():
    """
    Get current Phase 2 configuration
    """
    return {
        "auto_approve_low_risk": os.getenv("AUTO_APPROVE_LOW_RISK", "false").lower() == "true",
        "dry_run_mode": os.getenv("DRY_RUN_MODE", "true").lower() == "true",
        "learning_enabled": True,
        "action_cooldown_seconds": 300,
        "max_concurrent_actions": 3
    }


@router.post("/config/auto-approve")
@limiter.limit("10/minute")  # Config changes rate limit
async def update_auto_approve(request: Request, enabled: bool):
    """
    Enable/disable auto-approval of low-risk actions
    """
    # In production, this would update environment config
    return {
        "auto_approve_low_risk": enabled,
        "message": f"Auto-approval {'enabled' if enabled else 'disabled'}"
    }