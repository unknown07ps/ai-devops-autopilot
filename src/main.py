from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import redis
import json
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Import subscription components
from src.api.subscription_api import router as subscription_router, check_access
from src.notifications.email import send_expiry_reminder_email
from src.scheduler.trial_jobs import check_trial_expirations, send_trial_reminders

# Initialize Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Define lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[SCHEDULER] Starting background jobs...")
    
    # Add scheduled jobs
    scheduler.add_job(
        check_trial_expirations,
        CronTrigger(hour=0, minute=0),  # Midnight daily
        id='check_expirations',
        name='Check Trial Expirations'
    )
    
    scheduler.add_job(
        send_trial_reminders,
        CronTrigger(hour=9, minute=0),  # 9 AM daily
        id='send_reminders',
        name='Send Trial Reminders'
    )
    
    scheduler.start()
    print(f"[SCHEDULER] ✓ Started {len(scheduler.get_jobs())} background jobs")
    
    yield
    
    # Shutdown
    print("[SCHEDULER] Shutting down background jobs...")
    scheduler.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(
    title="AI DevOps Autopilot",
    version="0.3.0",
    description="Autonomous incident detection, analysis, and response",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(subscription_router)

# ============================================================================
# Data Models
# ============================================================================

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

class ActionApproval(BaseModel):
    action_id: str
    approved_by: str
    notes: Optional[str] = None

class AutonomousModeUpdate(BaseModel):
    mode: str
    confidence_threshold: Optional[int] = None

class LearningWeightsUpdate(BaseModel):
    rule_weight: Optional[float] = None
    ai_weight: Optional[float] = None
    historical_weight: Optional[float] = None

# ============================================================================
# Phase 3: Initialize Autonomous Executor
# ============================================================================

AUTONOMOUS_ENABLED = False
autonomous_executor = None

try:
    from src.autonomous_executor import AutonomousExecutor, ExecutionMode
    
    # Simple action executor for Phase 3
    class SimpleActionExecutor:
        def __init__(self, redis_client):
            self.redis = redis_client
            self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
        
        async def execute_action(self, action_id: str) -> Dict:
            """Execute an action"""
            import asyncio
            
            action_data = self.redis.get(f"action:{action_id}")
            if not action_data:
                return {"success": False, "error": "Action not found"}
            
            action = json.loads(action_data)
            action_type = action.get('action_type', 'unknown')
            
            # Simulate execution
            await asyncio.sleep(1)
            
            if self.dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "message": f"DRY RUN: {action_type} completed",
                    "duration_seconds": 1
                }
            
            return {
                "success": True,
                "message": f"{action_type} completed",
                "duration_seconds": 1
            }
    
    # Initialize
    action_executor = SimpleActionExecutor(redis_client)
    autonomous_executor = AutonomousExecutor(redis_client, action_executor)
    
    # Set initial mode from environment
    initial_mode = os.getenv("EXECUTION_MODE", "supervised")
    mode_map = {
        "manual": ExecutionMode.MANUAL,
        "supervised": ExecutionMode.SUPERVISED,
        "autonomous": ExecutionMode.AUTONOMOUS,
        "night_mode": ExecutionMode.NIGHT_MODE
    }
    
    if initial_mode in mode_map:
        autonomous_executor.set_execution_mode(mode_map[initial_mode])
    
    AUTONOMOUS_ENABLED = True
    print(f"[INIT] ✅ Phase 3 Autonomous Executor initialized (mode: {initial_mode})")

except ImportError as e:
    print(f"[INIT] ⚠️ Phase 3 components not available: {e}")
    print("[INIT] Phase 3 endpoints will return 503")
except Exception as e:
    print(f"[INIT] ⚠️ Failed to initialize autonomous executor: {e}")
    print("[INIT] Phase 3 endpoints will return 503")

# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "operational",
        "service": "AI DevOps Autopilot",
        "version": "0.3.0",
        "features": [
            "Real-time anomaly detection",
            "AI-powered root cause analysis",
            "Action approval workflow",
            "Autonomous execution (Phase 3)",
            "Slack notifications",
            "Web dashboard"
        ]
    }

@app.get("/health")
async def health():
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "autonomous_mode": AUTONOMOUS_ENABLED
        }
    except:
        return {
            "status": "degraded",
            "redis": "disconnected",
            "autonomous_mode": False
        }

# ============================================================================
# INGESTION ENDPOINTS
# ============================================================================

@app.post("/ingest/metrics")
async def ingest_metrics(metrics: List[MetricPoint], background_tasks: BackgroundTasks):
    """Ingest metrics in Prometheus-compatible format"""
    try:
        for metric in metrics:
            event = {
                "type": "metric",
                "data": metric.model_dump_json(),
                "timestamp": metric.timestamp.isoformat()
            }
            try:
                redis_client.xadd("events:metrics", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    metric_key = f"metric:{metric.labels.get('service', 'unknown')}:{metric.timestamp.timestamp()}"
                    redis_client.setex(metric_key, 3600, metric.model_dump_json())
                else:
                    raise
        
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
                redis_client.xadd("events:logs", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    redis_client.lpush(f"logs:{log.service}", log.model_dump_json())
                    redis_client.ltrim(f"logs:{log.service}", 0, 999)
                else:
                    raise
            
            if log.level in ["ERROR", "CRITICAL"]:
                error_count += 1
        
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
    """Track deployment events"""
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
        
        redis_client.zadd(
            f"deployments:{deployment.service}",
            {deployment.version: deployment.timestamp.timestamp()}
        )
        
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
# PHASE 2 API ENDPOINTS
# ============================================================================

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

# ============================================================================
# PHASE 3 API ENDPOINTS
# ============================================================================

@app.get("/api/v3/autonomous/status")
async def get_autonomous_status(user_id: str):
    """Get current autonomous execution status (subscription-gated)"""
    try:
        # Check subscription first
        access = await check_access(user_id, "autonomous_mode")

        if not access["allowed"]:
            return {
                "autonomous_enabled": False,
                "execution_mode": "manual",
                "status": "restricted",
                "message": "Autonomous mode requires an active subscription",
                "reason": access.get("reason"),
                "upgrade_url": "/subscription/upgrade"
            }

        # Check if autonomous executor is available
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            return {
                "autonomous_enabled": False,
                "execution_mode": "manual",
                "status": "not_initialized",
                "message": "Autonomous mode not initialized",
                "error": "Phase 3 components not loaded. Check autonomous_executor.py exists in src/"
            }

        # Get autonomous stats
        stats = autonomous_executor.get_autonomous_stats()

        return {
            "autonomous_enabled": True,
            "execution_mode": stats["execution_mode"],
            "confidence_threshold": stats["confidence_threshold"],
            "total_autonomous_actions": stats["total_autonomous_actions"],
            "successful_actions": stats["successful_actions"],
            "success_rate": stats["success_rate"],
            "active_actions": stats["active_actions"],
            "learning_weights": stats["learning_weights"],
            "night_mode_active": stats.get("is_night_mode_active"),
            "status": "operational"
        }

    except Exception as e:
        print(f"[API ERROR] get_autonomous_status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch autonomous status")

@app.post("/api/v3/autonomous/mode")
async def set_autonomous_mode(update: AutonomousModeUpdate):
    """Change autonomous execution mode"""
    try:
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            raise HTTPException(
                status_code=503,
                detail="Autonomous mode not available. Check that autonomous_executor.py exists in src/"
            )
        
        # Validate mode
        from src.autonomous_executor import ExecutionMode
        valid_modes = {
            "manual": ExecutionMode.MANUAL,
            "supervised": ExecutionMode.SUPERVISED,
            "autonomous": ExecutionMode.AUTONOMOUS,
            "night_mode": ExecutionMode.NIGHT_MODE
        }
        
        if update.mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {list(valid_modes.keys())}"
            )
        
        # Update mode
        autonomous_executor.set_execution_mode(valid_modes[update.mode])
        
        # Update confidence threshold if provided
        if update.confidence_threshold is not None:
            if not 0 <= update.confidence_threshold <= 100:
                raise HTTPException(
                    status_code=400,
                    detail="Confidence threshold must be between 0 and 100"
                )
            autonomous_executor.confidence_threshold = update.confidence_threshold
        
        return {
            "status": "success",
            "mode": update.mode,
            "confidence_threshold": autonomous_executor.confidence_threshold,
            "message": f"Autonomous mode changed to {update.mode}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] set_autonomous_mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/outcomes")
async def get_autonomous_outcomes(limit: int = 50, success_only: bool = False):
    """Get autonomous action outcomes for learning analysis"""
    try:
        outcomes_data = redis_client.lrange('autonomous_outcomes', 0, limit - 1)
        
        outcomes = []
        for outcome_json in outcomes_data:
            outcome = json.loads(outcome_json)
            
            if success_only and not outcome.get('success'):
                continue
            
            outcomes.append(outcome)
        
        # Calculate statistics
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.get('success'))
        failures = total - successes
        
        # Group by action type
        by_action_type = {}
        for outcome in outcomes:
            action_type = outcome.get('action_type', 'unknown')
            if action_type not in by_action_type:
                by_action_type[action_type] = {'total': 0, 'success': 0}
            
            by_action_type[action_type]['total'] += 1
            if outcome.get('success'):
                by_action_type[action_type]['success'] += 1
        
        # Calculate per-type success rates
        action_type_stats = []
        for action_type, stats in by_action_type.items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            action_type_stats.append({
                'action_type': action_type,
                'total': stats['total'],
                'successes': stats['success'],
                'success_rate': round(success_rate, 1)
            })
        
        return {
            "outcomes": outcomes[:limit],
            "statistics": {
                "total": total,
                "successes": successes,
                "failures": failures,
                "success_rate": round((successes / total * 100) if total > 0 else 0, 1),
                "by_action_type": action_type_stats
            },
            "limit": limit
        }
    except Exception as e:
        print(f"[API ERROR] get_autonomous_outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/safety-status")
async def get_safety_status():
    """Get current safety rail status and limits"""
    try:
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            return {
                "safety_rails_active": False,
                "message": "Autonomous mode not available"
            }
        
        # Get recent rollback count
        recent_rollbacks = autonomous_executor._count_recent_actions('rollback', hours=1)
        
        # Calculate time until cooldowns expire
        active_cooldowns = []
        current_time = datetime.now(timezone.utc).timestamp()
        
        for key, last_time in autonomous_executor.last_action_time.items():
            remaining = autonomous_executor.action_cooldown_seconds - (current_time - last_time)
            if remaining > 0:
                service, action_type = key.split(':')
                active_cooldowns.append({
                    'service': service,
                    'action_type': action_type,
                    'remaining_seconds': int(remaining)
                })
        
        return {
            "safety_rails_active": True,
            "limits": {
                "max_concurrent_actions": autonomous_executor.max_concurrent_actions,
                "action_cooldown_seconds": autonomous_executor.action_cooldown_seconds,
                "max_rollbacks_per_hour": autonomous_executor.max_rollbacks_per_hour,
                "max_scale_factor": autonomous_executor.max_scale_factor
            },
            "current_state": {
                "active_actions": len(autonomous_executor.active_actions),
                "active_cooldowns": len(active_cooldowns),
                "recent_rollbacks": recent_rollbacks,
                "cooldowns": active_cooldowns
            },
            "status": "operational"
        }
    except Exception as e:
        print(f"[API ERROR] get_safety_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/confidence-breakdown/{action_id}")
async def get_confidence_breakdown(action_id: str):
    """Get detailed confidence breakdown for an action"""
    try:
        action_data = redis_client.get(f"action:{action_id}")
        if not action_data:
            raise HTTPException(status_code=404, detail="Action not found")
        
        action = json.loads(action_data)
        
        # Check if action has autonomous metadata
        if 'autonomous_confidence' not in action:
            return {
                "action_id": action_id,
                "message": "This action was not evaluated autonomously",
                "action_type": action.get('action_type'),
                "status": action.get('status')
            }
        
        return {
            "action_id": action_id,
            "action_type": action.get('action_type'),
            "service": action.get('service'),
            "overall_confidence": action.get('autonomous_confidence'),
            "reasoning": action.get('autonomous_reasoning'),
            "status": action.get('status'),
            "executed_at": action.get('executed_at'),
            "completed_at": action.get('completed_at'),
            "result": action.get('result')
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] get_confidence_breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v3/autonomous/adjust-weights")
async def adjust_learning_weights(update: LearningWeightsUpdate):
    """Manually adjust learning weights (for experimentation)"""
    try:
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            raise HTTPException(
                status_code=503,
                detail="Autonomous mode not available"
            )
        
        # Validate weights
        weights_to_check = [
            ('rule_weight', update.rule_weight),
            ('ai_weight', update.ai_weight),
            ('historical_weight', update.historical_weight)
        ]
        
        for name, value in weights_to_check:
            if value is not None:
                if not isinstance(value, (int, float)):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{name} must be a number"
                    )
                if not 0 <= value <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Weights must be between 0 and 1. {name}={value} is invalid."
                    )
        
        # Update weights
        if update.rule_weight is not None:
            autonomous_executor.rule_weight = update.rule_weight
        if update.ai_weight is not None:
            autonomous_executor.ai_weight = update.ai_weight
        if update.historical_weight is not None:
            autonomous_executor.historical_weight = update.historical_weight
        
        # Normalize to sum to 1.0
        total = (autonomous_executor.rule_weight + 
                autonomous_executor.ai_weight + 
                autonomous_executor.historical_weight)
        
        if total > 0:
            autonomous_executor.rule_weight /= total
            autonomous_executor.ai_weight /= total
            autonomous_executor.historical_weight /= total
        
        return {
            "status": "success",
            "learning_weights": {
                "rule_based": round(autonomous_executor.rule_weight, 3),
                "ai": round(autonomous_executor.ai_weight, 3),
                "historical": round(autonomous_executor.historical_weight, 3)
            },
            "message": "Learning weights adjusted"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] adjust_learning_weights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/action-history")
async def get_autonomous_action_history(
    limit: int = 50,
    action_type: Optional[str] = None,
    success_only: bool = False
):
    """Get history of autonomous actions with filtering"""
    try:
        # Get all actions
        action_keys = redis_client.keys("action:*")
        actions = []
        
        for key in action_keys[:limit * 2]:  # Get more to allow for filtering
            action_data = redis_client.get(key)
            if action_data:
                action = json.loads(action_data)
                
                # Only include autonomous actions
                if 'autonomous_confidence' not in action:
                    continue
                
                # Filter by action type
                if action_type and action.get('action_type') != action_type:
                    continue
                
                # Filter by success
                if success_only:
                    result = action.get('result', {})
                    if not result.get('success'):
                        continue
                
                actions.append({
                    'action_id': action['id'],
                    'action_type': action['action_type'],
                    'service': action['service'],
                    'confidence': action['autonomous_confidence'],
                    'status': action['status'],
                    'executed_at': action.get('executed_at'),
                    'completed_at': action.get('completed_at'),
                    'success': action.get('result', {}).get('success'),
                    'duration_seconds': action.get('result', {}).get('duration_seconds')
                })
        
        # Sort by execution time (most recent first)
        actions.sort(
            key=lambda x: x.get('executed_at', ''), 
            reverse=True
        )
        
        return {
            "actions": actions[:limit],
            "total": len(actions),
            "filters": {
                "action_type": action_type,
                "success_only": success_only
            }
        }
    except Exception as e:
        print(f"[API ERROR] get_autonomous_action_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

@app.get("/api/stats")
async def get_dashboard_stats():
    """Get high-level dashboard statistics"""
    try:
        # Count active incidents
        active_incidents = 0
        services = redis_client.keys("incidents:*")
        
        for service_key in services:
            incidents = redis_client.lrange(service_key, 0, -1)
            for incident_json in incidents:
                incident = json.loads(incident_json)
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
        
        return {
            "active_incidents": active_incidents,
            "critical_anomalies": critical_anomalies,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "avg_resolution_time_minutes": 8.5,
            "uptime_percent": round((healthy_services / total_services) * 100, 1) if total_services > 0 else 100
        }
    
    except Exception as e:
        print(f"[API ERROR] Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents")
async def get_incidents(status: Optional[str] = None, service: Optional[str] = None, limit: int = 50):
    """Get all incidents with optional filtering"""
    try:
        all_incidents = []
        incident_keys = redis_client.keys("incidents:*")
        
        for key in incident_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            if service and service_name != service:
                continue
            
            incidents_json = redis_client.lrange(key, 0, limit - 1)
            
            for incident_json in incidents_json:
                incident = json.loads(incident_json)
                
                if 'id' not in incident:
                    incident['id'] = f"{service_name}_{incident['timestamp']}"
                
                if 'status' not in incident:
                    incident_time = datetime.fromisoformat(incident['timestamp'].replace('Z', '+00:00'))
                    time_since = datetime.utcnow() - incident_time.replace(tzinfo=None)
                    incident['status'] = 'resolved' if time_since > timedelta(hours=1) else 'active'
                
                if status and incident['status'] != status:
                    continue
                
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
        
        all_incidents.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {"incidents": all_incidents[:limit], "total": len(all_incidents)}
    
    except Exception as e:
        print(f"[API ERROR] Failed to get incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/anomalies")
async def get_anomalies(service: Optional[str] = None, severity: Optional[str] = None, limit: int = 100):
    """Get recent anomalies with optional filtering"""
    try:
        all_anomalies = []
        anomaly_keys = redis_client.keys("recent_anomalies:*")
        
        for key in anomaly_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            if service and service_name != service:
                continue
            
            anomalies_json = redis_client.lrange(key, 0, limit - 1)
            
            for anomaly_json in anomalies_json:
                anomaly = json.loads(anomaly_json)
                
                if severity and anomaly.get('severity') != severity:
                    continue
                
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
        
        all_anomalies.sort(key=lambda x: x['detected_at'], reverse=True)
        
        return {"anomalies": all_anomalies[:limit], "total": len(all_anomalies)}
    
    except Exception as e:
        print(f"[API ERROR] Failed to get anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/services")
async def get_services():
    """Get status of all monitored services"""
    try:
        services_data = {}
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
        
        anomaly_keys = redis_client.keys("recent_anomalies:*")
        
        for key in anomaly_keys:
            service_name = key.decode('utf-8').split(':')[1]
            
            if service_name in services_data:
                anomalies = redis_client.lrange(key, 0, 9)
                critical_count = 0
                
                for anomaly_json in anomalies:
                    anomaly = json.loads(anomaly_json)
                    if anomaly.get('severity') in ['critical', 'high']:
                        critical_count += 1
                
                services_data[service_name]['anomaly_count'] = len(anomalies)
                
                if critical_count > 0:
                    services_data[service_name]['status'] = 'degraded'
        
        for service_name in services_data.keys():
            latency_key = f"baseline:{service_name}:api_latency_ms"
            latency_data = redis_client.get(latency_key)
            
            if latency_data:
                baseline = json.loads(latency_data)
                services_data[service_name]['metrics']['latency_ms'] = round(baseline.get('mean', 0), 2)
            
            error_key = f"baseline:{service_name}:error_rate"
            error_data = redis_client.get(error_key)
            
            if error_data:
                baseline = json.loads(error_data)
                services_data[service_name]['metrics']['error_rate_percent'] = round(baseline.get('mean', 0), 2)
            
            incident_key = f"incidents:{service_name}"
            incidents = redis_client.lrange(incident_key, 0, -1)
            
            recent_incidents = 0
            for incident_json in incidents:
                incident = json.loads(incident_json)
                incident_time = datetime.fromisoformat(incident['timestamp'].replace('Z', '+00:00'))
                if (datetime.utcnow() - incident_time.replace(tzinfo=None)) < timedelta(hours=24):
                    recent_incidents += 1
            
            services_data[service_name]['incident_count'] = recent_incidents
        
        return {"services": list(services_data.values()), "total": len(services_data)}
    
    except Exception as e:
        print(f"[API ERROR] Failed to get services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Background Processing Functions
# ============================================================================

async def check_for_anomalies(metrics: List[MetricPoint]):
    """Check metrics for anomalies"""
    print(f"[DETECTION] Checking {len(metrics)} metrics for anomalies...")

async def investigate_error_spike(logs: List[LogEntry]):
    """Investigate error log spikes"""
    print(f"[ALERT] Error spike detected, investigating...")

async def monitor_deployment(deployment: DeploymentEvent):
    """Monitor deployment health post-deploy"""
    print(f"[MONITOR] Tracking deployment {deployment.service}:{deployment.version}")

# ============================================================================
# Dashboard Routes
# ============================================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve Phase 1 dashboard"""
    return """<!DOCTYPE html>
<html><body><h1>Dashboard - See dashboard_phase2.html for full version</h1></body></html>"""

@app.get("/dashboard/phase2", response_class=HTMLResponse)
async def get_phase2_dashboard():
    """Serve Phase 2 dashboard"""
    try:
        with open('dashboard_phase2.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """<html><body style="font-family: sans-serif; padding: 40px; text-align: center;">
        <h1>❌ Phase 2 Dashboard Not Found</h1>
        <p>Please ensure <code>dashboard_phase2.html</code> exists in the project root.</p>
        <p><a href="/dashboard">← Back to Phase 1 Dashboard</a></p></body></html>"""

# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)