"""
Subscription Management API - FIXED
Handles trial management, payments, and feature access control
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import os

# Import from correct modules
from database import get_db
from models import Subscription as DBSubscription, SubscriptionStatus, SubscriptionPlan, User
from subscription_service import check_feature_access as service_check_feature_access

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

# ============================================================================
# Pydantic Models
# ============================================================================

class SubscriptionCreate(BaseModel):
    user_id: str
    email: EmailStr
    plan: str = "trial"

class PaymentConfirmation(BaseModel):
    user_id: str
    payment_provider_customer_id: str
    payment_method_id: str

class SubscriptionResponse(BaseModel):
    user_id: str
    email: str
    status: str
    plan: str
    trial_end: Optional[str] = None
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None
    features: Dict[str, bool]
    created_at: str
    updated_at: str

# ============================================================================
# Feature Access Control - FIXED
# ============================================================================

FEATURE_MATRIX = {
    "trial": {
        "basic_monitoring": True,
        "ai_analysis": True,
        "action_proposals": True,
        "autonomous_mode": False,  # Locked in trial
        "max_services": 3,
        "data_retention_days": 7
    },
    "pro": {
        "basic_monitoring": True,
        "ai_analysis": True,
        "action_proposals": True,
        "autonomous_mode": True,  # Unlocked in pro
        "max_services": 10,
        "data_retention_days": 30
    },
    "enterprise": {
        "basic_monitoring": True,
        "ai_analysis": True,
        "action_proposals": True,
        "autonomous_mode": True,
        "max_services": -1,  # Unlimited
        "data_retention_days": 90
    }
}

async def check_access(user_id: str, feature: str, db: Session = None) -> Dict:
    """
    Check if user has access to a specific feature
    FIXED: Now properly uses database subscription
    """
    if not db:
        # If no db session provided, return error
        return {
            "allowed": False,
            "reason": "Database session required",
            "upgrade_required": False
        }
    
    try:
        # Get user subscription from database
        subscription = db.query(DBSubscription).filter(
            DBSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            return {
                "allowed": False,
                "reason": "No subscription found",
                "upgrade_required": True,
                "plan": None
            }
        
        # Use the service layer function for proper access check
        return service_check_feature_access(subscription, feature)
    
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] check_access failed: {e}")
        return {
            "allowed": False,
            "reason": f"Error checking subscription: {str(e)}",
            "upgrade_required": False
        }

# ============================================================================
# Subscription Management Endpoints - FIXED
# ============================================================================

@router.get("/status/{user_id}")
async def get_subscription_status(user_id: str, db: Session = Depends(get_db)):
    """Get subscription status for a user - FIXED"""
    try:
        subscription = db.query(DBSubscription).filter(
            DBSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found"
            )
        
        # Get user for email
        user = db.query(User).filter(User.user_id == user_id).first()
        
        return {
            "subscription": {
                "user_id": subscription.user_id,
                "email": user.email if user else "unknown",
                "status": subscription.status.value,
                "plan": subscription.plan.value,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "subscription_start": subscription.subscription_start.isoformat() if subscription.subscription_start else None,
                "subscription_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "features": subscription.feature_limits,
                "created_at": subscription.created_at.isoformat(),
                "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None
            },
            "days_remaining": subscription.days_until_expiry(),
            "is_active": subscription.is_active_subscription()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] get_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-access/{user_id}/{feature}")
async def check_feature_access_endpoint(
    user_id: str, 
    feature: str,
    db: Session = Depends(get_db)
):
    """Check if user has access to a specific feature - FIXED"""
    try:
        access = await check_access(user_id, feature, db)
        return access
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] check_feature_access: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Admin Endpoints - FIXED
# ============================================================================

@router.get("/admin/list")
async def list_all_subscriptions(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all subscriptions (admin only) - FIXED"""
    try:
        subscriptions = db.query(DBSubscription).limit(limit).all()
        
        result = []
        for sub in subscriptions:
            user = db.query(User).filter(User.user_id == sub.user_id).first()
            result.append({
                "user_id": sub.user_id,
                "email": user.email if user else "unknown",
                "status": sub.status.value,
                "plan": sub.plan.value,
                "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                "created_at": sub.created_at.isoformat()
            })
        
        return {
            "subscriptions": result,
            "total": len(result)
        }
    
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] list_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))