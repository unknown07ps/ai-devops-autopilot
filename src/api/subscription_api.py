# Add to your subscription_api.py
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@router.post("/create-checkout-session")
async def create_checkout_session(user_id: str):
    """Create Stripe checkout session"""
    
    sub_data = redis_client.get(f"subscription:{user_id}")
    if not sub_data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub = Subscription.model_validate_json(sub_data)
    
    session = stripe.checkout.Session.create(
        customer_email=sub.email,
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_XXXXX',  # Your Stripe price ID
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://yourdomain.com/subscription/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://yourdomain.com/subscription/cancel',
        metadata={'user_id': user_id}
    )
    
    return {"checkout_url": session.url}

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            
            # Upgrade subscription
            await upgrade_to_paid(PaymentConfirmation(
                user_id=user_id,
                payment_provider_customer_id=session['customer'],
                payment_method_id=session['payment_method']
            ))
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))