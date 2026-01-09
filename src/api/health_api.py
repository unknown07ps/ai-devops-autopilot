"""
Health API Router - Health check endpoints for monitoring service status
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os

from src.database import get_db, engine
from src.models import User, Subscription

router = APIRouter(tags=["Health"])


# These will be injected from main.py during router registration
_redis_client = None
_scheduler = None
_autonomous_enabled = False


def configure(redis_client, scheduler, autonomous_enabled: bool):
    """Configure router with shared dependencies from main.py"""
    global _redis_client, _scheduler, _autonomous_enabled
    _redis_client = redis_client
    _scheduler = scheduler
    _autonomous_enabled = autonomous_enabled


@router.get("/")
async def root():
    """Root endpoint - service info"""
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


@router.get("/health")
async def health():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # Check Redis
    try:
        if _redis_client:
            _redis_client.ping()
            health_status["components"]["redis"] = "healthy"
        else:
            health_status["components"]["redis"] = "not configured"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Database
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
    health_status["components"]["autonomous_mode"] = "healthy" if _autonomous_enabled else "disabled"
    
    return health_status


@router.get("/health/database")
async def health_database(db: Session = Depends(get_db)):
    """Detailed database health check"""
    try:
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


@router.get("/health/auth")
async def health_auth():
    """Authentication system health check"""
    job_scheduled = False
    if _scheduler:
        job_scheduled = _scheduler.get_job('cleanup_sessions') is not None
    
    return {
        "status": "healthy",
        "jwt_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "session_cleanup_scheduled": job_scheduled
    }


@router.get("/health/payments")
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
