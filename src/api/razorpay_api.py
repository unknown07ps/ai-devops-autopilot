"""
Razorpay Subscription API Endpoints
Checkout, webhooks, subscription management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import json

from src.database import get_db
from src.auth import get_current_user
from src.models import User, Subscription
from src.razorpay_service import (
    create_razorpay_subscription,
    create_payment_link,
    verify_razorpay_signature,
    verify_payment_signature,
    handle_subscription_authenticated,
    handle_subscription_activated,
    handle_subscription_charged,
    handle_payment_captured,
    handle_subscription_cancelled,
    handle_subscription_paused,
    cancel_razorpay_subscription,
    get_razorpay_subscription_details,
    pause_razorpay_subscription,
    resume_razorpay_subscription,
    get_invoices,
    RAZORPAY_PLANS,
    RAZORPAY_KEY_ID,
    RAZORPAY_WEBHOOK_SECRET
)
from src.subscription_service import cancel_subscription

router = APIRouter(prefix="/api/razorpay", tags=["razorpay"])

# ============================================================================
# Request/Response Models
# ============================================================================

class CheckoutRequest(BaseModel):
    plan: str  # pro_monthly, pro_yearly, enterprise_monthly
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

# ============================================================================
# Checkout & Payment
# ============================================================================

@router.get("/plans")
async def get_available_plans():
    """
    Get all available subscription plans
    """
    plans = []
    for plan_key, config in RAZORPAY_PLANS.items():
        plans.append({
            "key": plan_key,
            "name": plan_key.replace("_", " ").title(),
            "amount": config["amount"],
            "amount_inr": config["amount"] / 100,  # Convert paise to rupees
            "currency": config["currency"],
            "interval": config["interval"],
            "plan": config["deployr_plan"].value
        })
    
    return {
        "plans": plans,
        "currency": "INR"
    }

@router.post("/create-checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay checkout session
    Returns payment link for user to complete payment
    """
    # Check if plan is valid
    if request.plan not in RAZORPAY_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}"
        )
    
    # Check if user already has active subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if subscription and subscription.is_active_subscription():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active subscription"
        )
    
    try:
        # Create payment link (simpler than subscription for now)
        payment_link = create_payment_link(
            db=db,
            user=current_user,
            plan_key=request.plan
        )
        
        return {
            "status": "success",
            "payment_link_id": payment_link["payment_link_id"],
            "payment_url": payment_link["short_url"],
            "amount": payment_link["amount"],
            "currency": payment_link["currency"]
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/verify-payment")
async def verify_payment(
    verification: PaymentVerification,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify payment signature from frontend after payment completion
    """
    # Verify signature
    is_valid = verify_payment_signature(
        order_id=verification.razorpay_order_id,
        payment_id=verification.razorpay_payment_id,
        signature=verification.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature"
        )
    
    return {
        "status": "success",
        "message": "Payment verified successfully",
        "payment_id": verification.razorpay_payment_id
    }

@router.get("/callback")
async def payment_callback(
    razorpay_payment_id: str,
    razorpay_payment_link_id: str,
    razorpay_payment_link_reference_id: str,
    razorpay_payment_link_status: str,
    razorpay_signature: str
):
    """
    Handle payment callback from Razorpay
    Redirects user to success/failure page
    """
    if razorpay_payment_link_status == "paid":
        # Redirect to success page
        return RedirectResponse(
            url=f"/subscription/success?payment_id={razorpay_payment_id}"
        )
    else:
        # Redirect to failure page
        return RedirectResponse(
            url="/subscription/failed"
        )

# ============================================================================
# Webhooks
# ============================================================================

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Razorpay webhooks
    Events: subscription.activated, subscription.charged, payment.captured, etc.
    """
    # Get raw body and signature
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature"
        )
    
    # Verify signature
    if not verify_razorpay_signature(payload, signature, RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Parse event
    try:
        event_data = json.loads(payload)
        event_type = event_data.get("event")
        
        print(f"[RAZORPAY WEBHOOK] Received event: {event_type}")
        
        # Route to appropriate handler
        handlers = {
            "subscription.authenticated": handle_subscription_authenticated,
            "subscription.activated": handle_subscription_activated,
            "subscription.charged": handle_subscription_charged,
            "payment.captured": handle_payment_captured,
            "subscription.cancelled": handle_subscription_cancelled,
            "subscription.paused": handle_subscription_paused,
        }
        
        handler = handlers.get(event_type)
        if handler:
            success = handler(db, event_data)
            if success:
                return {"status": "success", "event": event_type}
            else:
                return {"status": "failed", "event": event_type}
        else:
            print(f"[RAZORPAY WEBHOOK] Unhandled event: {event_type}")
            return {"status": "ignored", "event": event_type}
    
    except Exception as e:
        print(f"[RAZORPAY WEBHOOK ERROR] {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# Subscription Management
# ============================================================================

@router.get("/subscription/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription status with Razorpay details
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    response = {
        "subscription_id": subscription.subscription_id,
        "plan": subscription.plan.value,
        "status": subscription.status.value,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "days_remaining": subscription.days_until_expiry()
    }
    
    # Get Razorpay subscription details if available
    if subscription.payment_provider_subscription_id:
        razorpay_details = get_razorpay_subscription_details(
            subscription.payment_provider_subscription_id
        )
        if razorpay_details:
            response["razorpay_status"] = razorpay_details.get("status")
            response["razorpay_subscription_id"] = razorpay_details.get("id")
    
    return response

@router.post("/subscription/cancel")
async def cancel_user_subscription(
    cancel_immediately: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel subscription
    By default, cancels at end of billing period
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if not subscription.is_active_subscription():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not active"
        )
    
    # Cancel on Razorpay
    if subscription.payment_provider == "razorpay":
        cancel_razorpay_subscription(
            db=db,
            subscription=subscription,
            cancel_at_cycle_end=not cancel_immediately
        )
    
    # Update local subscription
    cancel_subscription(
        db=db,
        user_id=current_user.user_id,
        immediately=cancel_immediately
    )
    
    return {
        "status": "success",
        "message": "Subscription cancelled" if cancel_immediately else "Subscription will cancel at end of period",
        "cancel_at_period_end": not cancel_immediately
    }

@router.post("/subscription/pause")
async def pause_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pause subscription (Razorpay feature)
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription or not subscription.payment_provider_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    success = pause_razorpay_subscription(subscription.payment_provider_subscription_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to pause subscription"
        )
    
    return {"status": "success", "message": "Subscription paused"}

@router.post("/subscription/resume")
async def resume_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resume paused subscription
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription or not subscription.payment_provider_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    success = resume_razorpay_subscription(subscription.payment_provider_subscription_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resume subscription"
        )
    
    return {"status": "success", "message": "Subscription resumed"}

# ============================================================================
# Billing & Invoices
# ============================================================================

@router.get("/invoices")
async def get_user_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all invoices for user's subscription
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription or not subscription.payment_provider_subscription_id:
        return {"invoices": []}
    
    invoices = get_invoices(subscription.payment_provider_subscription_id)
    
    return {
        "invoices": invoices,
        "total": len(invoices)
    }

# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/subscriptions")
async def list_all_subscriptions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all subscriptions (admin only)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    
    subscriptions = db.query(Subscription).limit(limit).all()
    
    return {
        "subscriptions": [
            {
                "subscription_id": sub.subscription_id,
                "user_email": sub.user.email,
                "plan": sub.plan.value,
                "status": sub.status.value,
                "razorpay_subscription_id": sub.payment_provider_subscription_id
            }
            for sub in subscriptions
        ],
        "total": len(subscriptions)
    }