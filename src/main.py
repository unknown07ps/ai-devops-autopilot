from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import redis
import json
from typing import List, Dict, Any, Optional
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Import database and authentication
from src.database import get_db, init_db, engine, get_db_context
from src.auth import get_current_user, get_current_active_subscription, cleanup_expired_sessions
from src.models import User, Subscription

# Import API routers
from src.api.auth_api import router as auth_router
from src.api.subscription_api import router as subscription_router, check_access
from src.api.razorpay_api import router as razorpay_router
from src.api.dashboard_api import router as dashboard_router

# Import notification and scheduling components
from src.notifications.email import send_expiry_reminder_email
from src.scheduler.trial_jobs import check_trial_expirations, send_trial_reminders
from src.subscription_service import check_all_expirations

# Initialize Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Validate critical environment variables
def validate_environment():
    """Validate that critical environment variables are set"""
    import os
    
    errors = []
    warnings = []
    
    # Database - REQUIRED
    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL is required for database connection")
    
    # JWT Secret - CRITICAL
    if not os.getenv("JWT_SECRET_KEY"):
        errors.append("JWT_SECRET_KEY is required - generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    
    # Redis - REQUIRED
    if not os.getenv("REDIS_URL"):
        errors.append("REDIS_URL is required for application state")
    
    # Razorpay (optional but warn if not set)
    if not os.getenv("RAZORPAY_KEY_ID") or not os.getenv("RAZORPAY_KEY_SECRET"):
        warnings.append("Razorpay credentials not set - payment features will be disabled")
    
    # Slack (optional)
    if not os.getenv("SLACK_WEBHOOK_URL"):
        warnings.append("Slack webhook not configured - notifications disabled")
    
    if errors:
        print("\n[VALIDATION ERRORS - APPLICATION CANNOT START]")
        for error in errors:
            print(f"  ❌ {error}")
        print("\nPlease check your .env file and set required variables.\n")
        raise ValueError("Critical environment variables missing")
    
    if warnings:
        print("\n[VALIDATION WARNINGS]")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
        print()
    
    return len(errors) == 0

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
    # Note: knowledge_base and learning_engine are set to None initially
    # They will be connected after learning components are initialized below
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
# Background Jobs
# ============================================================================

async def check_trial_expirations_job():
    """Check and expire trials (runs daily at midnight)"""
    try:
        with get_db_context() as db:
            result = check_all_expirations(db)
            print(f"[SCHEDULER] Checked expirations: {result.get('expired_count', 0)} expired")
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed to check expirations: {e}")

async def send_trial_reminders_job():
    """Send trial expiry reminders (runs daily at 9 AM)"""
    try:
        await send_trial_reminders()
        print(f"[SCHEDULER] Sent trial reminder emails")
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed to send reminders: {e}")

async def cleanup_expired_sessions_job():
    """Cleanup expired sessions (runs every 6 hours)"""
    try:
        with get_db_context() as db:
            cleanup_expired_sessions(db)
            print(f"[SCHEDULER] Cleaned up expired sessions")
    except Exception as e:
        print(f"[SCHEDULER ERROR] Failed to cleanup sessions: {e}")

# Define lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n" + "="*60)
    print("🚀 AI DevOps Autopilot - Startup Sequence")
    print("="*60)
    
    # Validate environment
    if not validate_environment():
        print("[STARTUP] ⚠️ Environment validation failed - some features may not work")
    
    # Initialize database
    try:
        print("[DATABASE] Testing database connection...")
        # FIX: Use text() wrapper
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[DATABASE] ✓ Connected to PostgreSQL")
        
        # Create tables if they don't exist
        print("[DATABASE] Ensuring tables exist...")
        init_db()
        print("[DATABASE] ✓ Database initialized")
        
    except Exception as e:
        print(f"[DATABASE] ❌ Database initialization failed: {e}")
        print("[DATABASE] ⚠️ API will continue but database features may not work")
    
    # Start background jobs
    print("[SCHEDULER] Starting background jobs...")
    
    # Add scheduled jobs
    scheduler.add_job(
        check_trial_expirations_job,
        CronTrigger(hour=0, minute=0),  # Midnight daily
        id='check_expirations',
        name='Check Trial Expirations'
    )
    
    scheduler.add_job(
        send_trial_reminders_job,
        CronTrigger(hour=9, minute=0),  # 9 AM daily
        id='send_reminders',
        name='Send Trial Reminders'
    )
    
    scheduler.add_job(
        cleanup_expired_sessions_job,
        CronTrigger(hour='*/6', minute=0),  # Every 6 hours
        id='cleanup_sessions',
        name='Cleanup Expired Sessions'
    )
    
    scheduler.start()
    print(f"[SCHEDULER] ✓ Started {len(scheduler.get_jobs())} background jobs")
    
    # Print startup summary
    print("\n" + "="*60)
    print("📊 System Status")
    print("="*60)
    print(f"Database: {'✓ Connected' if engine else '✗ Failed'}")
    print(f"Redis: ✓ Connected")
    print(f"Auth: {'✓ Enabled' if os.getenv('JWT_SECRET_KEY') else '⚠️ Using temporary secret'}")
    print(f"Payments: {'✓ Razorpay' if os.getenv('RAZORPAY_KEY_ID') else '✗ Disabled'}")
    print(f"Autonomous Mode: {'✓ Enabled' if AUTONOMOUS_ENABLED else '✗ Disabled'}")
    print(f"Background Jobs: ✓ {len(scheduler.get_jobs())} scheduled")
    print("="*60)
    print("✅ System Ready - Listening on http://0.0.0.0:8000")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n[SHUTDOWN] Shutting down background jobs...")
    scheduler.shutdown()
    print("[SHUTDOWN] ✓ Graceful shutdown complete")

# Create FastAPI app with lifespan
app = FastAPI(
    title="AI DevOps Autopilot",
    version="0.3.0",
    description="Autonomous incident detection, analysis, and response with subscription management",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    print(f"[GLOBAL ERROR] {request.method} {request.url.path}: {exc}")
    
    # Don't expose internal errors in production
    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )
    else:
        # In development, show detailed error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__
            }
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
app.include_router(auth_router)
app.include_router(subscription_router)
app.include_router(razorpay_router)
app.include_router(dashboard_router)

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
            "User authentication & authorization",
            "Subscription management",
            "Payment processing (Razorpay)",
            "Slack notifications",
            "Web dashboard"
        ]
    }

@app.get("/health")
async def health():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Database - FIX: Use text()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Authentication
    health_status["components"]["authentication"] = "healthy" if os.getenv("JWT_SECRET_KEY") else "warning: using temporary secret"
    
    # Check Payment Gateway
    razorpay_configured = bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))
    health_status["components"]["payment_gateway"] = "healthy" if razorpay_configured else "disabled"
    
    # Check Autonomous Mode
    health_status["components"]["autonomous_mode"] = "healthy" if AUTONOMOUS_ENABLED else "disabled"
    
    return health_status


@app.get("/health/database")
async def health_database(db: Session = Depends(get_db)):
    """Detailed database health check"""
    try:
        # FIX: Use text() wrapper for raw SQL
        db.execute(text("SELECT 1"))
        
        # Count users and subscriptions
        user_count = db.query(User).count()
        subscription_count = db.query(Subscription).count()
        
        return {
            "status": "healthy",
            "connection": "active",
            "statistics": {
                "users": user_count,
                "subscriptions": subscription_count
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/health/auth")
async def health_auth():
    """Authentication system health check"""
    return {
        "status": "healthy",
        "jwt_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "session_cleanup_scheduled": scheduler.get_job('cleanup_sessions') is not None
    }

@app.get("/health/payments")
async def health_payments():
    """Payment gateway health check"""
    razorpay_configured = bool(
        os.getenv("RAZORPAY_KEY_ID") and 
        os.getenv("RAZORPAY_KEY_SECRET")
    )
    
    return {
        "status": "healthy" if razorpay_configured else "disabled",
        "provider": "razorpay",
        "configured": razorpay_configured,
        "webhook_secret_set": bool(os.getenv("RAZORPAY_WEBHOOK_SECRET"))
    }

# ============================================================================
# Protected Endpoints Example
# ============================================================================

@app.get("/api/user/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with subscription"""
    # Get subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    return {
        "user": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "company": current_user.company,
            "email_verified": current_user.email_verified,
            "created_at": current_user.created_at.isoformat()
        },
        "subscription": {
            "plan": subscription.plan.value if subscription else None,
            "status": subscription.status.value if subscription else None,
            "days_remaining": subscription.days_until_expiry() if subscription else 0,
            "features": {
                "autonomous_mode": subscription.plan.value in ["pro", "enterprise"] if subscription else False,
                "max_services": 5 if not subscription else (10 if subscription.plan.value == "pro" else 999),
                "advanced_analytics": subscription.plan.value in ["pro", "enterprise"] if subscription else False
            }
        } if subscription else None
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
# Client API ENDPOINTS
# ============================================================================
    
@app.post("/prometheus/write")
async def prometheus_write_handler(request: Request):
    """
    Receive metrics from Prometheus remote_write
    """
    # Parse Prometheus protobuf format
    import snappy
    from prometheus_client.parser import text_string_to_metric_families
    
    body = await request.body()
    
    # Decompress
    decompressed = snappy.decompress(body)
    
    # Convert to your format and ingest
    metrics = parse_prometheus_metrics(decompressed)
    
    # Send to your ingestion pipeline
    for metric in metrics:
        await ingest_metric(metric)
    
    return {"status": "success"}

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
    # Validate inputs
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
    
    if service:
        # Validate service name format (alphanumeric, dash, underscore only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', service):
            raise HTTPException(status_code=400, detail="Invalid service name format")
        
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
# PHASE 3 API ENDPOINTS - SUBSCRIPTION GATED
# ============================================================================

@app.get("/api/v3/autonomous/status")
async def get_autonomous_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get autonomous execution status (requires authentication)"""
    try:
        # Get user subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.user_id
        ).first()
        
        # Check if autonomous mode is available
        has_access = subscription and subscription.plan.value in ["pro", "enterprise"]
        
        if not AUTONOMOUS_ENABLED:
            return {
                "autonomous_enabled": False,
                "message": "Autonomous mode not available - check that autonomous_executor.py exists",
                "user_has_access": has_access,
                "user_plan": subscription.plan.value if subscription else None
            }
        
        # Get stats from Redis
        outcomes_data = redis_client.lrange('autonomous_outcomes', 0, 99)
        outcomes = [json.loads(o) for o in outcomes_data]
        
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.get('success'))
        success_rate = (successes / total * 100) if total > 0 else 0
        
        return {
            "autonomous_enabled": True,
            "user_has_access": has_access,
            "user_plan": subscription.plan.value if subscription else None,
            "execution_mode": autonomous_executor.execution_mode.value,
            "confidence_threshold": autonomous_executor.confidence_threshold,
            "learning_weights": {
                "rule_based": round(autonomous_executor.rule_weight, 3),
                "ai": round(autonomous_executor.ai_weight, 3),
                "historical": round(autonomous_executor.historical_weight, 3)
            },
            "total_autonomous_actions": total,
            "successful_actions": successes,
            "success_rate": round(success_rate, 1),
            "active_actions": len(autonomous_executor.active_actions)
        }
    except Exception as e:
        print(f"[API ERROR] get_autonomous_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/status/public")
async def get_autonomous_status_public():
    """Get autonomous execution status (public - for dashboard without auth)"""
    try:
        if not AUTONOMOUS_ENABLED:
            return {
                "autonomous_enabled": False,
                "message": "Autonomous mode not available - check that autonomous_executor.py exists",
                "user_has_access": False,
                "user_plan": "unknown"
            }
        
        # Get stats from Redis
        outcomes_data = redis_client.lrange('autonomous_outcomes', 0, 99)
        outcomes = [json.loads(o) for o in outcomes_data]
        
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.get('success'))
        success_rate = (successes / total * 100) if total > 0 else 0
        
        return {
            "autonomous_enabled": True,
            "user_has_access": True,  # Public endpoint assumes access
            "user_plan": "demo",
            "execution_mode": autonomous_executor.execution_mode.value,
            "confidence_threshold": autonomous_executor.confidence_threshold,
            "learning_weights": {
                "rule_based": round(autonomous_executor.rule_weight, 3),
                "ai": round(autonomous_executor.ai_weight, 3),
                "historical": round(autonomous_executor.historical_weight, 3)
            },
            "total_autonomous_actions": total,
            "successful_actions": successes,
            "success_rate": round(success_rate, 1),
            "active_actions": len(autonomous_executor.active_actions)
        }
    except Exception as e:
        print(f"[API ERROR] get_autonomous_status_public: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v3/autonomous/mode")
async def set_autonomous_mode(
    update: AutonomousModeUpdate,
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_current_active_subscription),
    db: Session = Depends(get_db)
):
    """Change autonomous execution mode (subscription-gated)"""
    try:
        # Check subscription access
        access = await check_access(current_user.user_id, "autonomous_mode", db)
        
        if not access["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Autonomous mode requires Pro or Enterprise plan",
                    "reason": access.get("reason"),
                    "current_plan": subscription.plan.value if subscription else "free_trial",
                    "upgrade_url": f"/api/subscription/create-checkout-session?user_id={current_user.user_id}"
                }
            )
        
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            raise HTTPException(
                status_code=503,
                detail="Autonomous mode not available. Check that autonomous_executor.py exists in src/"
            )
        
        # Validate mode
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
            "timestamp": datetime.utcnow().isoformat(),
            "plan": subscription.plan.value
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] set_autonomous_mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v3/autonomous/mode/public")
async def set_autonomous_mode_public(update: AutonomousModeUpdate):
    """Change autonomous execution mode (public - for dashboard without auth)"""
    try:
        if not AUTONOMOUS_ENABLED or not autonomous_executor:
            raise HTTPException(
                status_code=503,
                detail="Autonomous mode not available. Check that autonomous_executor.py exists in src/"
            )
        
        # Validate mode
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
            "timestamp": datetime.utcnow().isoformat(),
            "plan": "demo"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] set_autonomous_mode_public: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/autonomous/outcomes")
async def get_autonomous_outcomes(
    limit: int = 50,
    success_only: bool = False,
    current_user: User = Depends(get_current_user)
):
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

@app.get("/api/v3/autonomous/outcomes/public")
async def get_autonomous_outcomes_public(
    limit: int = 50,
    success_only: bool = False
):
    """Get autonomous action outcomes (public - for dashboard)"""
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
        print(f"[API ERROR] get_autonomous_outcomes_public: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/safety-status")
async def get_safety_status(current_user: User = Depends(get_current_user)):
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

@app.get("/api/v3/autonomous/safety-status/public")
async def get_safety_status_public():
    """Get current safety rail status and limits (public - for dashboard)"""
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
        print(f"[API ERROR] get_safety_status_public: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/confidence-breakdown/{action_id}")
async def get_confidence_breakdown(
    action_id: str,
    current_user: User = Depends(get_current_user)
):
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
async def adjust_learning_weights(
    update: LearningWeightsUpdate,
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_current_active_subscription)
):
    """Manually adjust learning weights (for experimentation) - Enterprise only"""
    try:
        # Check for Enterprise subscription
        if subscription.plan.value != "enterprise":
            raise HTTPException(
                status_code=403,
                detail="Learning weight adjustment is only available on Enterprise plan"
            )
        
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
    success_only: bool = False,
    current_user: User = Depends(get_current_user)
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
        baseline_keys = list(redis_client.scan_iter("baseline:*"))
        
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
        
        anomaly_keys = list(redis_client.scan_iter("recent_anomalies:*"))
        
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
    """Serve main dashboard"""
    try:
        with open('Deployr_dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html><body style="font-family: sans-serif; padding: 40px; text-align: center;">
        <h1>❌ Dashboard Not Found</h1>
        <p>Please ensure <code>Deployr_dashboard.html</code> exists in the project root.</p>
        </body></html>
        """

@app.get("/dashboard/phase2", response_class=HTMLResponse)
async def get_phase2_dashboard(user_id: Optional[str] = None):
    """Serve Phase 2 dashboard with subscription check"""
    try:
        # Optional: Check subscription status
        subscription_status = None
        if user_id:
            sub_data = redis_client.get(f"subscription:{user_id}")
            if sub_data:
                subscription_status = json.loads(sub_data)
        
        with open('dashboard_phase2.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return html_content
    except FileNotFoundError:
        return """<html><body style="font-family: sans-serif; padding: 40px; text-align: center;">
        <h1>❌ Phase 2 Dashboard Not Found</h1>
        <p>Please ensure <code>dashboard_phase2.html</code> exists in the project root.</p>
        <p><a href="/dashboard">← Back to Main Dashboard</a></p></body></html>"""

# ============================================================================
# PHASE 4 API ENDPOINTS - ENTERPRISE FEATURES
# ============================================================================

# Import new modules (with graceful fallback)
try:
    from src.actions import UnifiedActionDispatcher, K8sActionType, CloudActionType, DatabaseActionType, CICDActionType
    from src.runbooks import RunbookEngine, get_high_latency_runbook, get_database_connection_runbook, get_memory_leak_runbook
    from src.analytics import ActionAnalytics
    
    # Initialize enterprise components
    action_dispatcher = UnifiedActionDispatcher(redis_client)
    runbook_engine = RunbookEngine(redis_client, action_dispatcher)
    action_analytics = ActionAnalytics(redis_client)
    
    # Register default runbooks
    runbook_engine.register_runbook(get_high_latency_runbook())
    runbook_engine.register_runbook(get_database_connection_runbook())
    runbook_engine.register_runbook(get_memory_leak_runbook())
    
    ENTERPRISE_ENABLED = True
    print("[INIT] ✅ Enterprise modules initialized (Actions, Runbooks, Analytics)")
except Exception as e:
    ENTERPRISE_ENABLED = False
    action_dispatcher = None
    runbook_engine = None
    action_analytics = None
    print(f"[INIT] ⚠️ Enterprise modules not available: {e}")


# --- Enhanced Actions API ---

class ActionRequest(BaseModel):
    category: str  # k8s, cloud, database, cicd
    action_type: str
    params: Dict[str, Any] = {}


@app.get("/api/v4/actions/available")
async def get_available_actions():
    """Get all available action types by category"""
    if not ENTERPRISE_ENABLED:
        return {"error": "Enterprise features not enabled", "available": False}
    
    return {
        "available": True,
        "actions": action_dispatcher.get_available_actions(),
        "categories": ["k8s", "cloud", "database", "cicd"]
    }


@app.post("/api/v4/actions/execute")
async def execute_action(request: ActionRequest):
    """Execute an action through the unified dispatcher"""
    if not ENTERPRISE_ENABLED:
        raise HTTPException(status_code=503, detail="Enterprise features not enabled")
    
    result = await action_dispatcher.execute(
        request.category,
        request.action_type,
        request.params
    )
    
    return result


@app.get("/api/v4/actions/history")
async def get_enhanced_action_history(
    category: Optional[str] = None,
    limit: int = 50
):
    """Get action history with optional category filter"""
    history_keys = {
        "k8s": "k8s_action_history",
        "cloud": "cloud_action_history",
        "database": "database_action_history",
        "cicd": "cicd_action_history"
    }
    
    actions = []
    
    if category and category in history_keys:
        data = redis_client.lrange(history_keys[category], 0, limit - 1)
        actions = [json.loads(a) for a in data]
    else:
        for key in history_keys.values():
            data = redis_client.lrange(key, 0, 20)
            actions.extend([json.loads(a) for a in data])
        actions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        actions = actions[:limit]
    
    return {
        "actions": actions,
        "total": len(actions),
        "category": category
    }


# --- Runbooks API ---

class RunbookRegistration(BaseModel):
    id: str
    name: str
    description: str = ""
    trigger: Dict[str, Any] = {}
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}


class RunbookExecution(BaseModel):
    runbook_id: str
    context: Dict[str, Any] = {}
    incident_id: Optional[str] = None


@app.get("/api/v4/runbooks")
async def list_runbooks():
    """List all registered runbooks"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        return {"runbooks": [], "enterprise_enabled": False}
    
    return {
        "runbooks": runbook_engine.list_runbooks(),
        "total": len(runbook_engine.runbooks)
    }


@app.get("/api/v4/runbooks/{runbook_id}")
async def get_runbook(runbook_id: str):
    """Get a specific runbook"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not available")
    
    runbook = runbook_engine.get_runbook(runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    
    return {
        "id": runbook.id,
        "name": runbook.name,
        "description": runbook.description,
        "trigger": runbook.trigger,
        "steps": [
            {
                "id": s.id,
                "name": s.name,
                "action_category": s.action_category,
                "action_type": s.action_type,
                "params": s.params,
                "condition": s.condition,
                "require_approval": s.require_approval
            }
            for s in runbook.steps
        ],
        "variables": runbook.variables
    }


@app.post("/api/v4/runbooks")
async def register_runbook(runbook: RunbookRegistration):
    """Register a new runbook"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not available")
    
    try:
        result = runbook_engine.register_runbook(runbook.dict())
        return {
            "success": True,
            "runbook_id": result.id,
            "message": f"Runbook '{result.name}' registered"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v4/runbooks/execute")
async def execute_runbook(request: RunbookExecution, background_tasks: BackgroundTasks):
    """Execute a runbook"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not available")
    
    # Execute in background
    async def run_runbook():
        return await runbook_engine.execute_runbook(
            request.runbook_id,
            request.context,
            request.incident_id
        )
    
    background_tasks.add_task(run_runbook)
    
    return {
        "success": True,
        "message": f"Runbook '{request.runbook_id}' execution started",
        "runbook_id": request.runbook_id
    }


@app.get("/api/v4/runbooks/executions/{execution_id}")
async def get_runbook_execution(execution_id: str):
    """Get status of a runbook execution"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not available")
    
    status = runbook_engine.get_execution_status(execution_id)
    if not status:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return status


@app.post("/api/v4/runbooks/executions/{execution_id}/cancel")
async def cancel_runbook_execution(execution_id: str):
    """Cancel a running runbook execution"""
    if not ENTERPRISE_ENABLED or not runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not available")
    
    return runbook_engine.cancel_execution(execution_id)


# --- Analytics API ---

@app.get("/api/v4/analytics/overview")
async def get_analytics_overview(days: int = 30):
    """Get analytics overview"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available", "enterprise_enabled": False}
    
    return action_analytics.get_overview_stats(days)


@app.get("/api/v4/analytics/trends")
async def get_success_trends(days: int = 30):
    """Get success rate trends"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_action_success_trends(days)


@app.get("/api/v4/analytics/resolution-times")
async def get_resolution_times(days: int = 30):
    """Get resolution time analysis"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_resolution_time_analysis(days)


@app.get("/api/v4/analytics/effectiveness")
async def get_action_effectiveness(action_type: Optional[str] = None):
    """Get action effectiveness analysis"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_action_effectiveness(action_type)


@app.get("/api/v4/analytics/ai-accuracy")
async def get_ai_accuracy():
    """Get AI recommendation accuracy"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_recommendation_accuracy()


@app.get("/api/v4/analytics/service-health")
async def get_service_health():
    """Get service health summary"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_service_health_summary()


@app.get("/api/v4/analytics/cost-impact")
async def get_cost_impact(days: int = 30):
    """Get cost impact analysis"""
    if not ENTERPRISE_ENABLED or not action_analytics:
        return {"error": "Analytics not available"}
    
    return action_analytics.get_cost_impact_analysis(days)


@app.get("/api/v4/status")
async def get_enterprise_status():
    """Get enterprise features status"""
    return {
        "enterprise_enabled": ENTERPRISE_ENABLED,
        "features": {
            "enhanced_actions": action_dispatcher is not None,
            "runbooks": runbook_engine is not None,
            "analytics": action_analytics is not None
        },
        "available_action_categories": ["k8s", "cloud", "database", "cicd"] if ENTERPRISE_ENABLED else [],
        "registered_runbooks": len(runbook_engine.runbooks) if runbook_engine else 0
    }


# ============================================================================
# Learning Stats API - Dashboard Integration
# ============================================================================

# Initialize learning components
LEARNING_ENABLED = False
knowledge_base = None
learning_engine = None
incident_analyzer = None

try:
    from src.training.devops_knowledge_base import DevOpsKnowledgeBase
    from src.learning.learning_engine import LearningEngine
    from src.analysis.incident_analyzer import IncidentAnalyzer
    
    knowledge_base = DevOpsKnowledgeBase(redis_client)
    learning_engine = LearningEngine(redis_client)
    incident_analyzer = IncidentAnalyzer(redis_client, knowledge_base)
    
    LEARNING_ENABLED = True
    print(f"[INIT] ✅ Learning System initialized ({knowledge_base.get_stats()['total_patterns']} patterns)")
    
    # Connect learning components to autonomous executor
    if AUTONOMOUS_ENABLED and autonomous_executor:
        autonomous_executor.knowledge_base = knowledge_base
        autonomous_executor.learning_engine = learning_engine
        print("[INIT] ✅ Learning Engine connected to Autonomous Executor")
        
except ImportError as e:
    print(f"[INIT] ⚠️ Learning components not available: {e}")
except Exception as e:
    print(f"[INIT] ⚠️ Failed to initialize learning system: {e}")


@app.get("/api/v5/learning/stats")
async def get_learning_stats():
    """Get comprehensive learning system statistics"""
    if not LEARNING_ENABLED:
        return {"error": "Learning system not available", "learning_enabled": False}
    
    kb_stats = knowledge_base.get_stats()
    learning_stats = learning_engine.get_learning_stats()
    
    # Get autonomous executor stats if available
    autonomous_stats = {}
    if AUTONOMOUS_ENABLED and autonomous_executor:
        autonomous_stats = autonomous_executor.get_autonomous_stats()
    
    return {
        "learning_enabled": True,
        "knowledge_base": {
            "total_patterns": kb_stats.get("total_patterns", 0),
            "by_category": kb_stats.get("by_category", {}),
            "by_severity": kb_stats.get("by_severity", {}),
            "autonomous_safe_count": kb_stats.get("autonomous_safe_count", 0)
        },
        "learning_engine": {
            "total_outcomes": learning_stats.get("total_outcomes", 0),
            "success_rate": learning_stats.get("success_rate", 0),
            "patterns_promoted": learning_stats.get("patterns_promoted", 0),
            "patterns_demoted": learning_stats.get("patterns_demoted", 0),
            "confidence_adjustments": learning_stats.get("confidence_adjustments", 0)
        },
        "autonomous": autonomous_stats
    }


@app.get("/api/v5/learning/knowledge-base")
async def get_knowledge_base_stats():
    """Get detailed knowledge base statistics"""
    if not LEARNING_ENABLED or not knowledge_base:
        return {"error": "Knowledge base not available"}
    
    stats = knowledge_base.get_stats()
    
    # Get pattern counts per category
    category_details = {}
    for cat_name, count in stats.get("by_category", {}).items():
        patterns = knowledge_base.get_patterns_by_category(cat_name)
        autonomous_safe = sum(1 for p in patterns if p.autonomous_safe)
        high_severity = sum(1 for p in patterns if p.severity.value in ["critical", "high"])
        category_details[cat_name] = {
            "total": count,
            "autonomous_safe": autonomous_safe,
            "high_severity": high_severity
        }
    
    return {
        "total_patterns": stats.get("total_patterns", 0),
        "by_category": category_details,
        "by_severity": stats.get("by_severity", {}),
        "autonomous_safe_total": stats.get("autonomous_safe_count", 0)
    }


@app.get("/api/v5/learning/patterns/{category}")
async def get_patterns_by_category(category: str, limit: int = 20):
    """Get patterns for a specific category"""
    if not LEARNING_ENABLED or not knowledge_base:
        return {"error": "Knowledge base not available"}
    
    try:
        from src.training.devops_knowledge_base import PatternCategory
        cat_enum = PatternCategory(category.lower())
        patterns = knowledge_base.get_patterns_by_category(cat_enum)
        
        # Return simplified pattern info
        return {
            "category": category,
            "count": len(patterns),
            "patterns": [
                {
                    "id": p.pattern_id,
                    "name": p.name,
                    "severity": p.severity.value,
                    "autonomous_safe": p.autonomous_safe,
                    "signals": p.signals[:3],  # First 3 signals
                    "resolution_time": p.resolution_time_avg_seconds
                }
                for p in patterns[:limit]
            ]
        }
    except ValueError:
        return {"error": f"Invalid category: {category}"}


@app.get("/api/v5/learning/pattern/{pattern_id}")
async def get_pattern_details(pattern_id: str):
    """Get detailed information about a specific pattern"""
    if not LEARNING_ENABLED or not knowledge_base:
        return {"error": "Knowledge base not available"}
    
    pattern = knowledge_base.get_pattern(pattern_id)
    if not pattern:
        return {"error": f"Pattern not found: {pattern_id}"}
    
    # Get learning stats for this pattern
    pattern_stats = learning_engine.get_pattern_stats(pattern_id) if learning_engine else {}
    
    return {
        "pattern": {
            "id": pattern.pattern_id,
            "name": pattern.name,
            "description": pattern.description,
            "category": pattern.category.value,
            "subcategory": pattern.subcategory,
            "severity": pattern.severity.value,
            "autonomous_safe": pattern.autonomous_safe,
            "blast_radius": pattern.blast_radius.value,
            "signals": pattern.signals,
            "root_causes": pattern.root_causes,
            "tags": pattern.tags,
            "resolution_time_avg": pattern.resolution_time_avg_seconds,
            "recommended_actions": [
                {
                    "type": a.action_type,
                    "category": a.action_category,
                    "confidence": a.confidence,
                    "requires_approval": a.requires_approval
                }
                for a in pattern.recommended_actions
            ]
        },
        "learning_stats": pattern_stats
    }


@app.post("/api/v5/learning/match")
async def match_patterns(anomalies: List[Dict], logs: List[Dict] = None):
    """Match anomalies against knowledge base patterns"""
    if not LEARNING_ENABLED or not knowledge_base:
        return {"error": "Knowledge base not available"}
    
    matches = knowledge_base.find_matching_patterns(anomalies, logs or [])
    
    return {
        "match_count": len(matches),
        "matches": [
            {
                "pattern_id": pattern.pattern_id,
                "name": pattern.name,
                "category": pattern.category.value,
                "severity": pattern.severity.value,
                "confidence": round(score, 1),
                "autonomous_safe": pattern.autonomous_safe
            }
            for pattern, score in matches[:10]  # Top 10 matches
        ]
    }


@app.get("/api/v5/learning/autonomous-patterns")
async def get_autonomous_safe_patterns():
    """Get all patterns that are safe for autonomous execution"""
    if not LEARNING_ENABLED or not knowledge_base:
        return {"error": "Knowledge base not available"}
    
    patterns = knowledge_base.get_autonomous_safe_patterns()
    
    # Group by category
    by_category = {}
    for p in patterns:
        cat = p.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "id": p.pattern_id,
            "name": p.name,
            "severity": p.severity.value
        })
    
    return {
        "total_autonomous_safe": len(patterns),
        "by_category": by_category
    }


@app.get("/api/v5/learning/engine-stats")
async def get_learning_engine_stats():
    """Get detailed learning engine statistics"""
    if not LEARNING_ENABLED or not learning_engine:
        return {"error": "Learning engine not available"}
    
    return learning_engine.get_learning_stats()


@app.post("/api/v5/learning/record-outcome")
async def record_action_outcome(
    pattern_id: str,
    action_type: str,
    success: bool,
    autonomous: bool = False,
    resolution_time_seconds: int = 0
):
    """Record an action outcome for learning"""
    if not LEARNING_ENABLED or not learning_engine:
        return {"error": "Learning engine not available"}
    
    outcome = {
        "pattern_id": pattern_id,
        "action_type": action_type,
        "success": success,
        "autonomous": autonomous,
        "resolution_time_seconds": resolution_time_seconds
    }
    
    learning_engine.record_outcome(outcome)
    
    return {"success": True, "message": "Outcome recorded for learning"}

# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)