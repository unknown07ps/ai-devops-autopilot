"""
Razorpay Payment Integration
Handles subscription payments, webhooks, and plan management
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
# Razorpay Configuration
# ============================================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ============================================================================
# Plan Configuration
# ============================================================================

# Razorpay Plan IDs (create these in Razorpay Dashboard)
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
        "amount": 99000,  # ₹990.00 in paise (save ₹198)
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
    """
    Create a Razorpay subscription
    Returns: {subscription_id, short_url, status}
    """
    if plan_key not in RAZORPAY_PLANS:
        raise ValueError(f"Invalid plan: {plan_key}")
    
    plan_config = RAZORPAY_PLANS[plan_key]
    
    try:
        # Create subscription on Razorpay
        subscription = razorpay_client.subscription.create({
            "plan_id": plan_config["plan_id"],
            "customer_notify": 1,  # Send email/SMS to customer
            "quantity": 1,
            "total_count": 12 if plan_config["interval"] == "monthly" else 1,  # 12 months or 1 year
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

def create_payment_link(
    db: Session,
    user: User,
    plan_key: str
) -> Dict:
    """
    Create a Razorpay payment link for subscription
    More flexible than subscription - allows one-time and recurring
    """
    if plan_key not in RAZORPAY_PLANS:
        raise ValueError(f"Invalid plan: {plan_key}")
    
    plan_config = RAZORPAY_PLANS[plan_key]
    
    try:
        # Create payment link
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
            "callback_url": f"{os.getenv('APP_URL', 'http://localhost:8000')}/subscription/callback",
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

# ============================================================================
# Webhook Verification
# ============================================================================

def verify_razorpay_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Razorpay webhook signature
    """
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str
) -> bool:
    """
    Verify payment signature from frontend
    """
    message = f"{order_id}|{payment_id}"
    
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

# ============================================================================
# Webhook Event Handlers
# ============================================================================

def handle_subscription_authenticated(db: Session, event_data: Dict) -> bool:
    """
    Handle subscription.authenticated webhook
    Subscription created and payment method added
    """
    subscription_data = event_data["payload"]["subscription"]["entity"]
    subscription_id = subscription_data["id"]
    
    user_id = subscription_data["notes"].get("user_id")
    plan_key = subscription_data["notes"].get("plan")
    
    if not user_id or not plan_key:
        print(f"[RAZORPAY] Missing user_id or plan in subscription notes")
        return False
    
    print(f"[RAZORPAY] Subscription authenticated: {subscription_id} for user {user_id}")
    
    # Subscription will be activated after first payment
    return True

def handle_subscription_activated(db: Session, event_data: Dict) -> bool:
    """
    Handle subscription.activated webhook
    First payment successful - activate pro subscription
    """
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
    
    # Upgrade user to paid subscription
    try:
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
        print(f"[RAZORPAY ERROR] Failed to activate subscription: {e}")
        return False

def handle_subscription_charged(db: Session, event_data: Dict) -> bool:
    """
    Handle subscription.charged webhook
    Recurring payment successful - renew subscription
    """
    subscription_data = event_data["payload"]["subscription"]["entity"]
    payment_data = event_data["payload"]["payment"]["entity"]
    
    subscription_id = subscription_data["id"]
    
    # Find subscription in database
    subscription = db.query(Subscription).filter(
        Subscription.payment_provider_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        print(f"[RAZORPAY] Subscription not found: {subscription_id}")
        return False
    
    # Calculate next period end
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
    
    # Renew subscription
    try:
        renew_subscription(db, subscription.subscription_id, new_period_end)
        print(f"[RAZORPAY] Renewed subscription {subscription_id}")
        return True
    
    except Exception as e:
        print(f"[RAZORPAY ERROR] Failed to renew subscription: {e}")
        return False

def handle_payment_captured(db: Session, event_data: Dict) -> bool:
    """
    Handle payment.captured webhook
    One-time payment successful (for payment links)
    """
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
    
    # Upgrade user to paid subscription
    try:
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
        print(f"[RAZORPAY ERROR] Failed to process payment: {e}")
        return False

def handle_subscription_cancelled(db: Session, event_data: Dict) -> bool:
    """
    Handle subscription.cancelled webhook
    """
    subscription_data = event_data["payload"]["subscription"]["entity"]
    subscription_id = subscription_data["id"]
    
    # Find subscription in database
    subscription = db.query(Subscription).filter(
        Subscription.payment_provider_subscription_id == subscription_id
    ).first()
    
    if not subscription:
        print(f"[RAZORPAY] Subscription not found: {subscription_id}")
        return False
    
    # Update subscription status
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.now(timezone.utc)
    db.commit()
    
    print(f"[RAZORPAY] Cancelled subscription {subscription_id}")
    return True

def handle_subscription_paused(db: Session, event_data: Dict) -> bool:
    """
    Handle subscription.paused webhook
    """
    subscription_data = event_data["payload"]["subscription"]["entity"]
    subscription_id = subscription_data["id"]
    
    # Find subscription
    subscription = db.query(Subscription).filter(
        Subscription.payment_provider_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        db.commit()
        print(f"[RAZORPAY] Paused subscription {subscription_id}")
    
    return True

# ============================================================================
# Subscription Management
# ============================================================================

def cancel_razorpay_subscription(
    db: Session,
    subscription: Subscription,
    cancel_at_cycle_end: bool = True
) -> bool:
    """
    Cancel subscription on Razorpay
    """
    if not subscription.payment_provider_subscription_id:
        return False
    
    try:
        if cancel_at_cycle_end:
            # Cancel at end of billing cycle
            razorpay_client.subscription.cancel(
                subscription.payment_provider_subscription_id,
                {"cancel_at_cycle_end": 1}
            )
        else:
            # Cancel immediately
            razorpay_client.subscription.cancel(
                subscription.payment_provider_subscription_id
            )
        
        print(f"[RAZORPAY] Cancelled subscription {subscription.payment_provider_subscription_id}")
        return True
    
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to cancel: {e}")
        return False

def get_razorpay_subscription_details(subscription_id: str) -> Optional[Dict]:
    """
    Get subscription details from Razorpay
    """
    try:
        subscription = razorpay_client.subscription.fetch(subscription_id)
        return subscription
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to fetch subscription: {e}")
        return None

def pause_razorpay_subscription(subscription_id: str) -> bool:
    """
    Pause a subscription
    """
    try:
        razorpay_client.subscription.pause(subscription_id)
        print(f"[RAZORPAY] Paused subscription {subscription_id}")
        return True
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to pause: {e}")
        return False

def resume_razorpay_subscription(subscription_id: str) -> bool:
    """
    Resume a paused subscription
    """
    try:
        razorpay_client.subscription.resume(subscription_id)
        print(f"[RAZORPAY] Resumed subscription {subscription_id}")
        return True
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to resume: {e}")
        return False

# ============================================================================
# Invoice Management
# ============================================================================

def get_invoices(subscription_id: str) -> list:
    """
    Get all invoices for a subscription
    """
    try:
        invoices = razorpay_client.invoice.all({
            "subscription_id": subscription_id
        })
        return invoices.get("items", [])
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to fetch invoices: {e}")
        return []

# ============================================================================
# Refunds
# ============================================================================

def create_refund(payment_id: str, amount: Optional[int] = None) -> Optional[Dict]:
    """
    Create a refund for a payment
    amount: in paise (optional - full refund if not specified)
    """
    try:
        refund_data = {"payment_id": payment_id}
        if amount:
            refund_data["amount"] = amount
        
        refund = razorpay_client.payment.refund(payment_id, refund_data)
        print(f"[RAZORPAY] Created refund for payment {payment_id}")
        return refund
    except razorpay.errors.BadRequestError as e:
        print(f"[RAZORPAY ERROR] Failed to create refund: {e}")
        return None