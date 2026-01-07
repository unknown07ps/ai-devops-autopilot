"""
Setup Enterprise Subscription for User
Run this script to create/upgrade a user to Enterprise plan

Usage:
    python setup_enterprise_user.py <email>
    
Example:
    python setup_enterprise_user.py user@example.com
"""

import sys
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, '.')

from src.database import get_db_context
from src.models import User, Subscription, SubscriptionStatus, SubscriptionPlan
from src.auth import hash_password
import secrets


def setup_enterprise_user(email: str, password: str = None):
    """Create or upgrade a user to Enterprise subscription"""
    
    with get_db_context() as db:
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user_id = f"usr_{secrets.token_urlsafe(16)}"
            default_password = password or "Deployr2026!"
            
            user = User(
                user_id=user_id,
                email=email,
                hashed_password=hash_password(default_password),
                full_name="Enterprise User",
                is_active=True,
                email_verified=True,
                is_superuser=True,  # Grant full admin access
                created_at=datetime.now(timezone.utc)
            )
            db.add(user)
            db.flush()  # Get user_id
            
            print(f"✅ Created user: {email}")
            print(f"   Password: {default_password}")
        else:
            print(f"✅ Found existing user: {email}")
            user.email_verified = True
            user.is_active = True
            user.is_superuser = True
        
        # Check for existing subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.user_id
        ).first()
        
        now = datetime.now(timezone.utc)
        # Set expiry to 10 years from now (effectively permanent)
        expiry = now + timedelta(days=3650)
        
        if subscription:
            # Upgrade existing subscription
            subscription.plan = SubscriptionPlan.ENTERPRISE
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.subscription_start = now
            subscription.current_period_start = now
            subscription.current_period_end = expiry
            subscription.cancel_at_period_end = False
            subscription.feature_limits = {
                "max_services": -1,  # Unlimited
                "data_retention_days": 365,
                "max_actions_per_day": -1,  # Unlimited
                "ai_analysis": True,
                "auto_remediation": True,
                "autonomous_mode": True,
                "slack_alerts": True,
                "priority_support": True,
                "custom_integrations": True,
                "advanced_analytics": True
            }
            print(f"✅ Upgraded subscription to ENTERPRISE")
        else:
            # Create new Enterprise subscription
            subscription = Subscription(
                subscription_id=f"sub_{secrets.token_urlsafe(16)}",
                user_id=user.user_id,
                plan=SubscriptionPlan.ENTERPRISE,
                status=SubscriptionStatus.ACTIVE,
                subscription_start=now,
                current_period_start=now,
                current_period_end=expiry,
                feature_limits={
                    "max_services": -1,
                    "data_retention_days": 365,
                    "max_actions_per_day": -1,
                    "ai_analysis": True,
                    "auto_remediation": True,
                    "autonomous_mode": True,
                    "slack_alerts": True,
                    "priority_support": True,
                    "custom_integrations": True,
                    "advanced_analytics": True
                }
            )
            db.add(subscription)
            print(f"✅ Created ENTERPRISE subscription")
        
        db.commit()
        
        print(f"\n🎉 SUCCESS!")
        print(f"   Email: {email}")
        print(f"   Plan: ENTERPRISE (Ultimate)")
        print(f"   Status: ACTIVE")
        print(f"   Expires: {expiry.strftime('%Y-%m-%d')}")
        print(f"   Features: ALL UNLIMITED")
        
        return user


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_enterprise_user.py <email> [password]")
        print("Example: python setup_enterprise_user.py admin@deployr.com MySecurePass123!")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None
    
    setup_enterprise_user(email, password)
