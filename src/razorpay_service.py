"""
Razorpay Payment Integration - Fixed Version
Handles subscription payments, webhooks, and plan management with proper error handling
"""

import razorpay
import hmac
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session

from models import Subscription, SubscriptionStatus, SubscriptionPlan, User
from subscription_service import upgrade_to_paid, renew_subscription

# ============================================================================
# Razorpay Configuration with Safety Checks
# ============================================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# Check if Razorpay is configured
RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

# Initialize Razorpay client only if credentials are available
if RAZORPAY_ENABLED:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        print("[RAZORPAY] ✓ Client initialized successfully")
    except Exception as e:
        print(f"[RAZORPAY] ❌ Failed to initialize client: {e}")
        RAZORPAY_ENABLED = False
        razorpay_client = None
else:
    razorpay_client = None
    print("[RAZORPAY] ⚠️  Not configured - payment features disabled")

# ============================================================================
# Plan Configuration
# ============================================================================

RAZORPAY_PLANS = {
    "pro_monthly": {
        "plan_id": os.getenv("RAZORPAY_PRO_MONTHLY_PLAN_ID", "plan_PRO_MONTHLY"),
        "amount": 9900,  # ₹99.00 in paise
        "currency": "INR",
        "interval": "monthly",
        "deployr_plan": SubscriptionPlan.PRO
    },
    "pro_yearly": {
        "plan_id": os.getenv("RAZORPAY_PRO_YEARLY_PLAN_ID", "plan_PRO_YEARLY"),
        "amount": 99000,  # ₹990.00 in paise
        "currency": "INR",
        "interval": "yearly",
        "deployr_plan": SubscriptionPlan.PRO
    },
    "enterprise_monthly": {
        "plan_id": os.getenv("RAZORPAY_ENTERPRISE_MONTHLY_PLAN_ID", "plan_ENT_MONTHLY"),
        "amount": 49900,  # ₹499.00 in paise
        "currency": "INR",
        "interval": "monthly",
        "deployr_plan": SubscriptionPlan.ENTERPRISE
    }
}

# ============================================================================
# Helper Functions
# ============================================================================

def check_razorpay_enabled():
    """Check if Razorpay is properly configured"""
    if not RAZORPAY_ENABLED:
        raise ValueError(
            "Razorpay not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
            "environment variables."
        )

# ============================================================================
# Subscription Creation
# ============================================================================

def create_razorpay_subscription(
    db: Session,
    user: User,
    plan_key: str,
    customer_email: str,
    customer_name: str,
    customer_contact: str
) -> Dict:
    """Create a Razorpay subscription"""
    check_razorpay_enabled()
    
    if plan_key not in RAZORPAY_PLANS:
        raise ValueError(f"Invalid plan: {plan_key}")
    
    plan_config = RAZORPAY_PLANS[plan_key]
    
    try:
        subscription = razorpay_client.subscription.create({
            "plan_id": plan_config["plan_id"],
            "customer_notify": 1,
            "quantity": 1,
            "total_count": 12 if plan_config["interval"] == "monthly" else 1,
            "start_at": int((datetime.now(timezone.utc) + timedelta(seconds=60)).timestamp()),
            "notes": {
                "user_id": user.user_id,
                "email": customer_email,
                "plan": plan_key
            },
            "addons": []
        })
        
        print(f"[RAZORPAY] Created subscription: {subscription['id']}")
        
        return {
            "subscription_id": subscription["id"],
            "status": subscription["status"],
            "short_url": subscription.get("short_url"),
            "plan": plan_key,
            "amount": plan_config["amount"],
            "currency": plan_config["currency"]
        }
    
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] {e}")
        raise ValueError(f"Failed to create subscription: {str(e)}")
    except Exception as e:
        print(f"[RAZORPAY ERROR] Unexpected error: {e}")
        raise ValueError(f"Failed to create subscription: {str(e)}")

def create_payment_link(
    db: Session,
    user: User,
    plan_key: str
) -> Dict:
    """Create a Razorpay payment link for subscription"""
    check_razorpay_enabled()
    
    if plan_key not in RAZORPAY_PLANS:
        raise ValueError(f"Invalid plan: {plan_key}")
    
    plan_config = RAZORPAY_PLANS[plan_key]
    
    try:
        payment_link = razorpay_client.payment_link.create({
            "amount": plan_config["amount"],
            "currency": plan_config["currency"],
            "description": f"Deployr {plan_key.replace('_', ' ').title()} Subscription",
            "customer": {
                "name": user.full_name or user.email,
                "email": user.email,
            },
            "notify": {
                "sms": False,
                "email": True
            },
            "reminder_enable": True,
            "notes": {
                "user_id": user.user_id,
                "plan": plan_key,
                "deployr_plan": plan_config["deployr_plan"].value
            },
            "callback_url": f"{os.getenv('APP_URL', 'http://localhost:8000')}/api/razorpay/callback",
            "callback_method": "get"
        })
        
        print(f"[RAZORPAY] Created payment link: {payment_link['id']}")
        
        return {
            "payment_link_id": payment_link["id"],
            "short_url": payment_link["short_url"],
            "status": payment_link["status"],
            "amount": plan_config["amount"],
            "currency": plan_config["currency"]
        }
    
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] {e}")
        raise ValueError(f"Failed to create payment link: {str(e)}")
    except Exception as e:
        print(f"[RAZORPAY ERROR] Unexpected error: {e}")
        raise ValueError(f"Failed to create payment link: {str(e)}")

# ============================================================================
# Webhook Verification
# ============================================================================

def verify_razorpay_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook signature"""
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        print(f"[RAZORPAY] Signature verification failed: {e}")
        return False

def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str
) -> bool:
    """Verify payment signature from frontend"""
    if not RAZORPAY_KEY_SECRET:
        print("[RAZORPAY] Cannot verify signature - secret not configured")
        return False
    
    try:
        message = f"{order_id}|{payment_id}"
        
        expected_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        print(f"[RAZORPAY] Payment signature verification failed: {e}")
        return False

# ============================================================================
# Webhook Event Handlers
# ============================================================================

def handle_subscription_authenticated(db: Session, event_data: Dict) -> bool:
    """Handle subscription.authenticated webhook"""
    try:
        subscription_data = event_data["payload"]["subscription"]["entity"]
        subscription_id = subscription_data["id"]
        
        user_id = subscription_data["notes"].get("user_id")
        plan_key = subscription_data["notes"].get("plan")
        
        if not user_id or not plan_key:
            print(f"[RAZORPAY] Missing user_id or plan in subscription notes")
            return False
        
        print(f"[RAZORPAY] Subscription authenticated: {subscription_id} for user {user_id}")
        return True
    except Exception as e:
        print(f"[RAZORPAY] Error handling subscription.authenticated: {e}")
        return False

def handle_subscription_activated(db: Session, event_data: Dict) -> bool:
    """Handle subscription.activated webhook"""
    try:
        subscription_data = event_data["payload"]["subscription"]["entity"]
        subscription_id = subscription_data["id"]
        
        user_id = subscription_data["notes"].get("user_id")
        plan_key = subscription_data["notes"].get("plan")
        
        if not user_id or not plan_key:
            print(f"[RAZORPAY] Missing user_id or plan in subscription")
            return False
        
        plan_config = RAZORPAY_PLANS.get(plan_key)
        if not plan_config:
            print(f"[RAZORPAY] Invalid plan: {plan_key}")
            return False
        
        upgrade_to_paid(
            db=db,
            user_id=user_id,
            plan=plan_config["deployr_plan"],
            payment_provider="razorpay",
            payment_provider_customer_id=subscription_data.get("customer_id", ""),
            payment_provider_subscription_id=subscription_id
        )
        
        print(f"[RAZORPAY] Activated subscription for user {user_id}")
        return True
    
    except Exception as e:
        print(f"[RAZORPAY] Error handling subscription.activated: {e}")
        return False

def handle_subscription_charged(db: Session, event_data: Dict) -> bool:
    """Handle subscription.charged webhook"""
    try:
        subscription_data = event_data["payload"]["subscription"]["entity"]
        subscription_id = subscription_data["id"]
        
        subscription = db.query(Subscription).filter(
            Subscription.payment_provider_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            print(f"[RAZORPAY] Subscription not found: {subscription_id}")
            return False
        
        interval = None
        for plan_key, config in RAZORPAY_PLANS.items():
            if config["plan_id"] == subscription_data["plan_id"]:
                interval = config["interval"]
                break
        
        if interval == "monthly":
            new_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        elif interval == "yearly":
            new_period_end = datetime.now(timezone.utc) + timedelta(days=365)
        else:
            new_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        
        renew_subscription(db, subscription.subscription_id, new_period_end)
        print(f"[RAZORPAY] Renewed subscription {subscription_id}")
        return True
    
    except Exception as e:
        print(f"[RAZORPAY] Error handling subscription.charged: {e}")
        return False

def handle_payment_captured(db: Session, event_data: Dict) -> bool:
    """Handle payment.captured webhook"""
    try:
        payment_data = event_data["payload"]["payment"]["entity"]
        
        user_id = payment_data["notes"].get("user_id")
        plan_key = payment_data["notes"].get("plan")
        
        if not user_id or not plan_key:
            print(f"[RAZORPAY] Missing user_id or plan in payment")
            return False
        
        plan_config = RAZORPAY_PLANS.get(plan_key)
        if not plan_config:
            print(f"[RAZORPAY] Invalid plan: {plan_key}")
            return False
        
        upgrade_to_paid(
            db=db,
            user_id=user_id,
            plan=plan_config["deployr_plan"],
            payment_provider="razorpay",
            payment_provider_customer_id=payment_data.get("customer_id", ""),
            payment_provider_subscription_id=payment_data["id"]
        )
        
        print(f"[RAZORPAY] Payment captured for user {user_id}")
        return True
    
    except Exception as e:
        print(f"[RAZORPAY] Error handling payment.captured: {e}")
        return False

def handle_subscription_cancelled(db: Session, event_data: Dict) -> bool:
    """Handle subscription.cancelled webhook"""
    try:
        subscription_data = event_data["payload"]["subscription"]["entity"]
        subscription_id = subscription_data["id"]
        
        subscription = db.query(Subscription).filter(
            Subscription.payment_provider_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            print(f"[RAZORPAY] Subscription not found: {subscription_id}")
            return False
        
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.now(timezone.utc)
        db.commit()
        
        print(f"[RAZORPAY] Cancelled subscription {subscription_id}")
        return True
    except Exception as e:
        print(f"[RAZORPAY] Error handling subscription.cancelled: {e}")
        return False

def handle_subscription_paused(db: Session, event_data: Dict) -> bool:
    """Handle subscription.paused webhook"""
    try:
        subscription_data = event_data["payload"]["subscription"]["entity"]
        subscription_id = subscription_data["id"]
        
        subscription = db.query(Subscription).filter(
            Subscription.payment_provider_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            db.commit()
            print(f"[RAZORPAY] Paused subscription {subscription_id}")
        
        return True
    except Exception as e:
        print(f"[RAZORPAY] Error handling subscription.paused: {e}")
        return False

# ============================================================================
# Subscription Management
# ============================================================================

def cancel_razorpay_subscription(
    db: Session,
    subscription: Subscription,
    cancel_at_cycle_end: bool = True
) -> bool:
    """Cancel subscription on Razorpay"""
    check_razorpay_enabled()
    
    if not subscription.payment_provider_subscription_id:
        return False
    
    try:
        if cancel_at_cycle_end:
            razorpay_client.subscription.cancel(
                subscription.payment_provider_subscription_id,
                {"cancel_at_cycle_end": 1}
            )
        else:
            razorpay_client.subscription.cancel(
                subscription.payment_provider_subscription_id
            )
        
        print(f"[RAZORPAY] Cancelled subscription {subscription.payment_provider_subscription_id}")
        return True
    
    except Exception as e:
        print(f"[RAZORPAY] Failed to cancel: {e}")
        return False

def get_razorpay_subscription_details(subscription_id: str) -> Optional[Dict]:
    """Get subscription details from Razorpay"""
    check_razorpay_enabled()
    
    try:
        subscription = razorpay_client.subscription.fetch(subscription_id)
        return subscription
    except Exception as e:
        print(f"[RAZORPAY] Failed to fetch subscription: {e}")
        return None

def pause_razorpay_subscription(subscription_id: str) -> bool:
    """Pause a subscription"""
    check_razorpay_enabled()
    
    try:
        razorpay_client.subscription.pause(subscription_id)
        print(f"[RAZORPAY] Paused subscription {subscription_id}")
        return True
    except Exception as e:
        print(f"[RAZORPAY] Failed to pause: {e}")
        return False

def resume_razorpay_subscription(subscription_id: str) -> bool:
    """Resume a paused subscription"""
    check_razorpay_enabled()
    
    try:
        razorpay_client.subscription.resume(subscription_id)
        print(f"[RAZORPAY] Resumed subscription {subscription_id}")
        return True
    except Exception as e:
        print(f"[RAZORPAY] Failed to resume: {e}")
        return False

def get_invoices(subscription_id: str) -> list:
    """Get all invoices for a subscription"""
    check_razorpay_enabled()
    
    try:
        invoices = razorpay_client.invoice.all({
            "subscription_id": subscription_id
        })
        return invoices.get("items", [])
    except Exception as e:
        print(f"[RAZORPAY] Failed to fetch invoices: {e}")
        return []

def create_refund(payment_id: str, amount: Optional[int] = None) -> Optional[Dict]:
    """Create a refund for a payment"""
    check_razorpay_enabled()
    
    try:
        refund_data = {"payment_id": payment_id}
        if amount:
            refund_data["amount"] = amount
        
        refund = razorpay_client.payment.refund(payment_id, refund_data)
        print(f"[RAZORPAY] Created refund for payment {payment_id}")
        return refund
    except Exception as e:
        print(f"[RAZORPAY] Failed to create refund: {e}")
        return None