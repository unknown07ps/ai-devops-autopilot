import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_subscription_flow():
    client = httpx.AsyncClient(timeout=30.0)
    
    print("🧪 Testing Subscription System\n")
    
    # Test 1: Create trial subscription
    print("1️⃣ Creating trial subscription...")
    response = await client.post(
        f"{BASE_URL}/api/subscription/create",
        json={
            "user_id": "user_123",
            "email": "test@example.com",
            "plan": "trial"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Trial created, expires: {data['subscription']['trial_end']}")
    else:
        print(f"   ✗ Failed: {response.status_code}")
    
    # Test 2: Check subscription status
    print("\n2️⃣ Checking subscription status...")
    response = await client.get(f"{BASE_URL}/api/subscription/status/user_123")
    if response.status_code == 200:
        data = response.json()
        print(f"   Plan: {data['subscription']['plan']}")
        print(f"   Status: {data['subscription']['status']}")
        print(f"   Days remaining: {data['days_remaining']}")
    
    # Test 3: Check autonomous mode access (should be blocked)
    print("\n3️⃣ Testing autonomous mode access (trial)...")
    response = await client.get(
        f"{BASE_URL}/api/v3/autonomous/status?user_id=user_123"
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Autonomous enabled: {data['autonomous_enabled']}")
        print(f"   Status: {data['status']}")
        print(f"   Message: {data.get('message')}")
    
    # Test 4: Check feature access
    print("\n4️⃣ Checking feature access...")
    response = await client.get(
        f"{BASE_URL}/api/subscription/check-access/user_123/autonomous_mode"
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Allowed: {data['allowed']}")
        print(f"   Reason: {data['reason']}")
        if not data['allowed']:
            print(f"   Available in: {data.get('available_in')}")
    
    # Test 5: Create checkout session
    print("\n5️⃣ Creating Stripe checkout session...")
    response = await client.post(
        f"{BASE_URL}/api/subscription/create-checkout-session",
        params={"user_id": "user_123"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Checkout URL: {data['checkout_url'][:60]}...")
    elif response.status_code == 503:
        print("   ⚠ Stripe not configured (expected in dev)")
    
    # Test 6: Simulate upgrade
    print("\n6️⃣ Simulating upgrade to Pro...")
    response = await client.post(
        f"{BASE_URL}/api/subscription/upgrade",
        json={
            "user_id": "user_123",
            "payment_provider_customer_id": "cus_test123",
            "payment_method_id": "pm_test123"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Upgraded to: {data['subscription']['plan']}")
        print(f"   Status: {data['subscription']['status']}")
    
    # Test 7: Check autonomous mode access again (should work now)
    print("\n7️⃣ Testing autonomous mode access (pro)...")
    response = await client.get(
        f"{BASE_URL}/api/v3/autonomous/status?user_id=user_123"
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Autonomous enabled: {data.get('autonomous_enabled')}")
        print(f"   Status: {data['status']}")
    
    await client.aclose()
    print("\n✅ Subscription tests complete!")

if __name__ == "__main__":
    asyncio.run(test_subscription_flow())
