"""
Subscription Service
Manages subscription lifecycle, trial management, and feature access
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import secrets

from models import (
    User, Subscription, SubscriptionStatus, 
    SubscriptionPlan, AuditLog
)

# ============================================================================
# Feature Access Matrix
# ============================================================================

FEATURE_MATRIX = {
    SubscriptionPlan.FREE: {
        "max_services": 1,
        "data_retention_days": 7,
        "max_actions_per_day": 10,
        "ai_analysis": False,
        "auto_remediation": False,
        "autonomous_mode": False,
        "slack_alerts": False,
    },
    SubscriptionPlan.TRIAL: {
        "max_services": 3,
        "data_retention_days": 7,
        "max_actions_per_day": 50,
        "ai_analysis": True,
        "auto_remediation": True,
        "autonomous_mode": False,  # Locked during trial
        "slack_alerts": True,
    },
    SubscriptionPlan.PRO: {
        "max_services": 10,
        "data_retention_days": 30,
        "max_actions_per_day": 500,
        "ai_analysis": True,
        "auto_remediation": True,
        "autonomous_mode": True,  # Unlocked in Pro
        "slack_alerts": True,
    },
    SubscriptionPlan.ENTERPRISE: {
        "max_services": -1,  # Unlimited
        "data_retention_days": 90,
        "max_actions_per_day": -1,  # Unlimited
        "ai_analysis": True,
        "auto_remediation": True,
        "autonomous_mode": True,
        "slack_alerts": True,
    }
}

# ============================================================================
# Subscription Creation
# ============================================================================

def create_trial_subscription(db: Session, user: User) -> Subscription:
    """Create a 7-day trial subscription for new user"""
    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=7)
    
    subscription_id = f"sub_{secrets.token_urlsafe(16)}"
    
    subscription = Subscription(
        subscription_id=subscription_id,
        user_id=user.user_id,
        plan=SubscriptionPlan.TRIAL,
        status=SubscriptionStatus.TRIALING,
        trial_start=now,
        trial_end=trial_end,
        current_period_end=trial_end,
        feature_limits=FEATURE_MATRIX[SubscriptionPlan.TRIAL]
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Log creation
    log_audit_event(
        db, user.user_id, "subscription.created",
        resource_type="subscription",
        resource_id=subscription_id,
        new_value={"plan": "trial", "trial_days": 7}
    )
    
    print(f"[SUBSCRIPTION] Created trial for {user.email} (expires: {trial_end})")
    
    return subscription

def upgrade_to_paid(db, user_id: str, plan, payment_provider: str, 
                   payment_provider_customer_id: str, 
                   payment_provider_subscription_id: str):
    """Upgrade user to paid subscription"""
    from models import Subscription
    from datetime import datetime, timedelta, timezone
    
    try:
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("No subscription found for user")
        
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        
        # Update subscription
        old_status = subscription.status
        subscription.plan = plan
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.subscription_start = now
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.payment_provider = payment_provider
        subscription.payment_provider_customer_id = payment_provider_customer_id
        subscription.payment_provider_subscription_id = payment_provider_subscription_id
        subscription.feature_limits = FEATURE_MATRIX[plan]
        
        db.commit()
        db.refresh(subscription)
        
        # Log upgrade
        log_audit_event(
            db, user_id, "subscription.upgraded",
            resource_type="subscription",
            resource_id=subscription.subscription_id,
            old_value={"status": old_status.value},
            new_value={"status": "active", "plan": plan.value}
        )
        
        print(f"[SUBSCRIPTION] Upgraded {user_id} to {plan.value}")
        return subscription
        
    except Exception as e:
        db.rollback()
        print(f"[SUBSCRIPTION ERROR] Failed to upgrade: {e}")
        raise

# ============================================================================
# Subscription Management
# ============================================================================

def check_subscription_expiry(db: Session, subscription: Subscription) -> bool:
    """
    Check if subscription has expired and update status
    Returns True if status changed
    """
    now = datetime.now(timezone.utc)
    changed = False
    
    # Check trial expiration
    if subscription.status == SubscriptionStatus.TRIALING:
        if subscription.trial_end and now > subscription.trial_end:
            subscription.status = SubscriptionStatus.EXPIRED
            changed = True
            print(f"[SUBSCRIPTION] Trial expired: {subscription.subscription_id}")
    
    # Check active subscription expiration
    elif subscription.status == SubscriptionStatus.ACTIVE:
        if subscription.current_period_end and now > subscription.current_period_end:
            # Check if should cancel or mark as past due
            if subscription.cancel_at_period_end:
                subscription.status = SubscriptionStatus.CANCELED
            else:
                subscription.status = SubscriptionStatus.PAST_DUE
            changed = True
            print(f"[SUBSCRIPTION] Subscription expired: {subscription.subscription_id}")
    
    if changed:
        db.commit()
        db.refresh(subscription)
    
    return changed

def renew_subscription(
    db: Session,
    subscription_id: str,
    new_period_end: datetime
) -> Subscription:
    """Renew subscription (called by payment webhook)"""
    subscription = db.query(Subscription).filter(
        Subscription.subscription_id == subscription_id
    ).first()
    
    if not subscription:
        raise ValueError("Subscription not found")
    
    now = datetime.now(timezone.utc)
    
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_start = now
    subscription.current_period_end = new_period_end
    
    db.commit()
    db.refresh(subscription)
    
    print(f"[SUBSCRIPTION] Renewed {subscription_id} until {new_period_end}")
    
    return subscription

def cancel_subscription(
    db: Session,
    user_id: str,
    immediately: bool = False
) -> Subscription:
    """Cancel subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if not subscription:
        raise ValueError("No subscription found")
    
    now = datetime.now(timezone.utc)
    
    if immediately:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = now
        subscription.current_period_end = now
    else:
        # Cancel at end of current period
        subscription.cancel_at_period_end = True
        subscription.canceled_at = now
    
    db.commit()
    db.refresh(subscription)
    
    # Log cancellation
    log_audit_event(
        db, user_id, "subscription.canceled",
        resource_type="subscription",
        resource_id=subscription.subscription_id,
        new_value={"immediately": immediately}
    )
    
    print(f"[SUBSCRIPTION] Canceled {subscription.subscription_id}")
    
    return subscription

# ============================================================================
# Feature Access Control
# ============================================================================

def check_feature_access(subscription: Subscription, feature: str) -> Dict:
    """
    Check if subscription allows access to a feature
    Returns: {allowed: bool, reason: str, upgrade_required: bool}
    """
    # Check if subscription is active
    if not subscription.is_active_subscription():
        return {
            "allowed": False,
            "reason": f"Subscription {subscription.status.value}",
            "upgrade_required": True,
            "current_plan": subscription.plan.value
        }
    
    # Get feature limits
    limits = subscription.feature_limits or {}
    
    # Check specific feature
    feature_allowed = limits.get(feature, False)
    
    if not feature_allowed:
        # Find which plan has this feature
        available_in = []
        for plan, features in FEATURE_MATRIX.items():
            if features.get(feature):
                available_in.append(plan.value)
        
        return {
            "allowed": False,
            "reason": f"Feature '{feature}' not available in {subscription.plan.value} plan",
            "upgrade_required": True,
            "current_plan": subscription.plan.value,
            "available_in": available_in
        }
    
    return {
        "allowed": True,
        "reason": "Access granted",
        "upgrade_required": False,
        "current_plan": subscription.plan.value
    }

def get_usage_limits(subscription: Subscription) -> Dict:
    """Get current usage limits for subscription"""
    limits = subscription.feature_limits or {}
    
    return {
        "max_services": limits.get("max_services", 0),
        "data_retention_days": limits.get("data_retention_days", 0),
        "max_actions_per_day": limits.get("max_actions_per_day", 0),
        "features": {
            "ai_analysis": limits.get("ai_analysis", False),
            "auto_remediation": limits.get("auto_remediation", False),
            "autonomous_mode": limits.get("autonomous_mode", False),
            "slack_alerts": limits.get("slack_alerts", False),
        }
    }

# ============================================================================
# Bulk Operations (for admin/cron jobs)
# ============================================================================

def check_all_expirations(db: Session) -> Dict:
    """
    Check all subscriptions for expiration (run daily via cron)
    Returns: {expired_count, notified_count}
    """
    now = datetime.now(timezone.utc)
    expired_count = 0
    notified_count = 0
    
    # Check trialing subscriptions
    trialing = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.TRIALING,
        Subscription.trial_end < now
    ).all()
    
    for subscription in trialing:
        subscription.status = SubscriptionStatus.EXPIRED
        expired_count += 1
    
    # Check active subscriptions
    active = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.ACTIVE,
        Subscription.current_period_end < now
    ).all()
    
    for subscription in active:
        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
        else:
            subscription.status = SubscriptionStatus.PAST_DUE
        expired_count += 1
    
    db.commit()
    
    print(f"[SUBSCRIPTION] Checked expirations: {expired_count} expired")
    
    return {
        "expired_count": expired_count,
        "notified_count": notified_count,
        "timestamp": now.isoformat()
    }

def get_expiring_trials(db: Session, days: int = 3) -> list:
    """Get trials expiring in N days (for reminder emails)"""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)
    
    expiring = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.TRIALING,
        Subscription.trial_end > now,
        Subscription.trial_end <= cutoff
    ).all()
    
    return expiring

# ============================================================================
# Audit Logging
# ============================================================================

def log_audit_event(
    db: Session,
    user_id: str,
    event_type: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log an audit event"""
    log = AuditLog(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(log)
    db.commit()

# ============================================================================
# Subscription Analytics
# ============================================================================

def get_subscription_stats(db: Session) -> Dict:
    """Get overall subscription statistics"""
    total = db.query(Subscription).count()
    
    stats = {
        "total": total,
        "by_status": {},
        "by_plan": {},
        "active_trials": 0,
        "active_paid": 0
    }
    
    # Count by status
    for status in SubscriptionStatus:
        count = db.query(Subscription).filter(
            Subscription.status == status
        ).count()
        stats["by_status"][status.value] = count
    
    # Count by plan
    for plan in SubscriptionPlan:
        count = db.query(Subscription).filter(
            Subscription.plan == plan
        ).count()
        stats["by_plan"][plan.value] = count
    
    # Active counts
    stats["active_trials"] = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.TRIALING
    ).count()
    
    stats["active_paid"] = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    ).count()
    
    return stats