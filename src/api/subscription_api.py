"""
Subscription Management API
Handles trial management, payments, and feature access control
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import redis
import json
import os
import stripe
from fastapi import Depends, Header


router = APIRouter(prefix="/api/subscription", tags=["subscription"])

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')

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

class Subscription(BaseModel):
    user_id: str
    email: str
    status: str  # trialing, active, expired, cancelled
    plan: str  # trial, pro, enterprise
    trial_end: Optional[str] = None
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None
    features: Dict[str, bool]
    created_at: str
    updated_at: str

# ============================================================================
# Feature Access Control
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
  

async def verify_subscription(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> Dict:
    """
    Dependency to verify subscription for protected endpoints
    Usage: @app.get("/endpoint", dependencies=[Depends(verify_subscription)])
    """
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID required in X-User-ID header"
        )
    
    from main import redis_client  # Import here to avoid circular dependency
    
    sub_data = redis_client.get(f"subscription:{user_id}")
    if not sub_data:
        raise HTTPException(
            status_code=404,
            detail="No subscription found"
        )
    
    subscription = json.loads(sub_data)
    
    if subscription["status"] not in ["trialing", "active"]:
        raise HTTPException(
            status_code=403,
            detail=f"Subscription {subscription['status']}"
        )
    
    return subscription  
  
async def check_access(user_id: str, db: Session) -> Dict:
    """Check if user has access to a specific feature"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if not subscription:
        return {"allowed": False, "reason": "No subscription found"}
    
    try:
        # Get user subscription
        sub_data = redis_client.get(f"subscription:{user_id}")
        
        if not sub_data:
            return {
                "allowed": False,
                "reason": "No subscription found",
                "upgrade_required": True,
                "plan": None
            }
        
        sub = json.loads(sub_data)
        
        # Check if subscription is active
        if sub["status"] == "expired":
            return {
                "allowed": False,
                "reason": "Subscription expired",
                "upgrade_required": True,
                "plan": sub["plan"]
            }
        
        if sub["status"] == "cancelled":
            return {
                "allowed": False,
                "reason": "Subscription cancelled",
                "upgrade_required": True,
                "plan": sub["plan"]
            }
        
        # Check trial expiration
        if sub["status"] == "trialing":
            trial_end = datetime.fromisoformat(sub["trial_end"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > trial_end:
                # Mark as expired
                sub["status"] = "expired"
                redis_client.setex(f"subscription:{user_id}", 365 * 86400, json.dumps(sub))
                
                return {
                    "allowed": False,
                    "reason": "Trial expired",
                    "upgrade_required": True,
                    "plan": "trial"
                }
        
        # Check feature access
        plan = sub["plan"]
        features = FEATURE_MATRIX.get(plan, {})
        
        feature_allowed = features.get(feature, False)
        
        if not feature_allowed:
            return {
                "allowed": False,
                "reason": f"Feature '{feature}' not available in {plan} plan",
                "upgrade_required": True,
                "plan": plan,
                "available_in": ["pro", "enterprise"] if plan == "trial" else ["enterprise"]
            }
        
        return {
            "allowed": True,
            "reason": "Access granted",
            "upgrade_required": False,
            "plan": plan
        }
    
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] check_access failed: {e}")
        return {
            "allowed": False,
            "reason": "Error checking subscription",
            "upgrade_required": False
        }

# ============================================================================
# Subscription Management Endpoints
# ============================================================================

@router.post("/create")
async def create_subscription(sub_create: SubscriptionCreate):
    """Create a new trial subscription"""
    try:
        # Check if subscription already exists
        existing = redis_client.get(f"subscription:{sub_create.user_id}")
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Subscription already exists for this user"
            )
        
        # Create trial subscription
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=7)  # 7-day trial
        
        subscription = {
            "user_id": sub_create.user_id,
            "email": sub_create.email,
            "status": "trialing",
            "plan": "trial",
            "trial_end": trial_end.isoformat(),
            "subscription_start": None,
            "subscription_end": None,
            "features": FEATURE_MATRIX["trial"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Store in Redis (1 year expiry)
        redis_client.setex(
            f"subscription:{sub_create.user_id}",
            365 * 86400,
            json.dumps(subscription)
        )
        
        print(f"[SUBSCRIPTION] Created trial for {sub_create.user_id}")
        
        return {
            "status": "success",
            "subscription": subscription,
            "message": f"Trial subscription created. Expires: {trial_end.isoformat()}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] create: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_id}")
async def get_subscription_status(user_id: str):
    """Get subscription status for a user"""
    try:
        sub_data = redis_client.get(f"subscription:{user_id}")
        
        if not sub_data:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found"
            )
        
        subscription = json.loads(sub_data)
        
        # Calculate days remaining for trial
        days_remaining = None
        if subscription["status"] == "trialing":
            trial_end = datetime.fromisoformat(
                subscription["trial_end"].replace("Z", "+00:00")
            )
            days_remaining = (trial_end - datetime.now(timezone.utc)).days
        
        return {
            "subscription": subscription,
            "days_remaining": days_remaining,
            "is_active": subscription["status"] in ["trialing", "active"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] get_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upgrade")
async def upgrade_to_paid(payment: PaymentConfirmation):
    """Upgrade from trial to paid subscription"""
    try:
        sub_data = redis_client.get(f"subscription:{payment.user_id}")
        
        if not sub_data:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found"
            )
        
        subscription = json.loads(sub_data)
        
        # Update to pro plan
        now = datetime.now(timezone.utc)
        subscription_end = now + timedelta(days=30)  # Monthly billing
        
        subscription.update({
            "status": "active",
            "plan": "pro",
            "subscription_start": now.isoformat(),
            "subscription_end": subscription_end.isoformat(),
            "features": FEATURE_MATRIX["pro"],
            "updated_at": now.isoformat(),
            "payment_provider_customer_id": payment.payment_provider_customer_id,
            "payment_method_id": payment.payment_method_id
        })
        
        # Update in Redis
        redis_client.setex(
            f"subscription:{payment.user_id}",
            365 * 86400,
            json.dumps(subscription)
        )
        
        print(f"[SUBSCRIPTION] Upgraded {payment.user_id} to pro")
        
        return {
            "status": "success",
            "subscription": subscription,
            "message": "Subscription upgraded to Pro"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] upgrade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-expirations")
async def check_expirations():
    """Check and mark expired trials (called by scheduler)"""
    try:
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        # Scan all subscriptions
        for key in redis_client.scan_iter("subscription:*"):
            sub_data = redis_client.get(key)
            if not sub_data:
                continue
            
            subscription = json.loads(sub_data)
            
            # Check trial expiration
            if subscription["status"] == "trialing":
                trial_end = datetime.fromisoformat(
                    subscription["trial_end"].replace("Z", "+00:00")
                )
                
                if now > trial_end:
                    subscription["status"] = "expired"
                    subscription["updated_at"] = now.isoformat()
                    
                    user_id = subscription["user_id"]
                    redis_client.setex(
                        f"subscription:{user_id}",
                        365 * 86400,
                        json.dumps(subscription)
                    )
                    
                    expired_count += 1
                    print(f"[SUBSCRIPTION] Marked {user_id} as expired")
        
        return {
            "status": "success",
            "expired_count": expired_count,
            "timestamp": now.isoformat()
        }
    
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] check_expirations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-access/{user_id}/{feature}")
async def check_feature_access(user_id: str, feature: str):
    """Check if user has access to a specific feature"""
    try:
        access = await check_access(user_id, feature)
        return access
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] check_feature_access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/list")
async def list_all_subscriptions(limit: int = 50):
    """List all subscriptions (admin only)"""
    try:
        subscriptions = []
        
        for key in redis_client.scan_iter("subscription:*"):
            sub_data = redis_client.get(key)
            if sub_data:
                subscriptions.append(json.loads(sub_data))
            
            if len(subscriptions) >= limit:
                break
        
        # Sort by created date
        subscriptions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            "subscriptions": subscriptions[:limit],
            "total": len(subscriptions)
        }
    
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] list_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/extend-trial/{user_id}")
async def extend_trial(user_id: str, days: int = 7):
    """Extend trial period for a user (admin only)"""
    try:
        sub_data = redis_client.get(f"subscription:{user_id}")
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        subscription = json.loads(sub_data)
        
        if subscription["status"] != "trialing":
            raise HTTPException(
                status_code=400,
                detail="Can only extend trials"
            )
        
        # Extend trial end date
        current_end = datetime.fromisoformat(
            subscription["trial_end"].replace("Z", "+00:00")
        )
        new_end = current_end + timedelta(days=days)
        
        subscription["trial_end"] = new_end.isoformat()
        subscription["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        redis_client.setex(
            f"subscription:{user_id}",
            365 * 86400,
            json.dumps(subscription)
        )
        
        return {
            "status": "success",
            "message": f"Trial extended by {days} days",
            "new_trial_end": new_end.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUBSCRIPTION ERROR] extend_trial: {e}")
        raise HTTPException(status_code=500, detail=str(e))