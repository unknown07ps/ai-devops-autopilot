"""
Deployr Training Script
Generates realistic sample data to train the AI system
Run this to populate your system with historical incidents
"""

import asyncio
import httpx
import random
from datetime import datetime, timedelta, timezone
import json
import sys

BASE_URL = "http://localhost:8000"

async def check_server_running():
    """Check if Deployr server is running"""
    try:
        client = httpx.AsyncClient(timeout=5.0)
        response = await client.get(f"{BASE_URL}/health")
        await client.aclose()
        return response.status_code == 200
    except:
        return False

# Sample services your clients might have
SERVICES = [
    "api-gateway",
    "user-service", 
    "payment-service",
    "notification-service",
    "database-primary",
    "cache-redis"
]

# Sample incident scenarios
INCIDENT_SCENARIOS = [
    {
        "trigger": "high_latency",
        "metrics": ["api_latency_ms", "response_time_p95"],
        "values": [250, 300, 400, 500, 600],
        "solution": "scale_up",
        "deployment_related": False
    },
    {
        "trigger": "deployment_issue",
        "metrics": ["error_rate", "api_latency_ms"],
        "values": [5.0, 8.0, 12.0, 15.0],
        "solution": "rollback",
        "deployment_related": True
    },
    {
        "trigger": "memory_leak",
        "metrics": ["memory_usage_percent", "gc_time_ms"],
        "values": [75, 80, 85, 90, 95],
        "solution": "restart_service",
        "deployment_related": False
    },
    {
        "trigger": "database_overload",
        "metrics": ["db_connection_pool", "query_time_ms"],
        "values": [90, 95, 98, 100],
        "solution": "kill_connections",
        "deployment_related": False
    }
]

async def generate_training_data(num_incidents: int = 50):
    """
    Generate training data for the AI system
    """
    # Check if server is running
    print("🔍 Checking if Deployr server is running...")
    if not await check_server_running():
        print("\n❌ ERROR: Deployr server is not running!")
        print("\n💡 Please start the server first:")
        print("   1. Open a terminal")
        print("   2. Run: python src/main.py")
        print("   3. Wait for 'System Ready' message")
        print("   4. Then run this training script again\n")
        sys.exit(1)
    
    print("✅ Server is running!\n")
    
    client = httpx.AsyncClient(timeout=30.0)
    
    print(f"🎓 Starting Training: Generating {num_incidents} incidents...")
    print("=" * 60)
    
    for i in range(num_incidents):
        # Pick random service and scenario
        service = random.choice(SERVICES)
        scenario = random.choice(INCIDENT_SCENARIOS)
        
        print(f"\n[{i+1}/{num_incidents}] Training incident: {scenario['trigger']} on {service}")
        
        # Step 1: Generate deployment if needed
        if scenario["deployment_related"]:
            await simulate_deployment(client, service)
            await asyncio.sleep(1)
        
        # Step 2: Generate anomalous metrics
        await simulate_anomalous_metrics(client, service, scenario)
        await asyncio.sleep(2)
        
        # Step 3: Generate error logs
        await simulate_error_logs(client, service, scenario)
        await asyncio.sleep(2)
        
        # Step 4: Wait for system to detect and analyze
        print("   ⏳ Waiting for AI analysis...")
        await asyncio.sleep(5)
        
        # Step 5: Approve and execute the recommended action
        await approve_and_execute_action(client, service, scenario["solution"])
        await asyncio.sleep(3)
        
        print(f"   ✅ Incident {i+1} training complete")
    
    await client.aclose()
    
    print("\n" + "=" * 60)
    print("🎉 Training Complete!")
    print(f"Generated {num_incidents} incidents across {len(SERVICES)} services")
    print("\n📊 Your AI should now have:")
    print(f"   • {num_incidents} historical incidents")
    print(f"   • ~{num_incidents * 3} actions recorded")
    print(f"   • Pattern recognition across {len(INCIDENT_SCENARIOS)} scenario types")

async def simulate_deployment(client, service):
    """Simulate a deployment event"""
    version = f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 99)}"
    
    await client.post(f"{BASE_URL}/ingest/deployment", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "version": version,
        "status": "success",
        "metadata": {
            "deployed_by": "training_script",
            "commit": f"abc{random.randint(1000, 9999)}"
        }
    })
    print(f"   📦 Deployed {service} {version}")

async def simulate_anomalous_metrics(client, service, scenario):
    """Generate anomalous metrics"""
    metrics = []
    
    for metric_name in scenario["metrics"]:
        for value in scenario["values"]:
            # Add some noise
            noisy_value = value * random.uniform(0.95, 1.05)
            
            metrics.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metric_name": metric_name,
                "value": noisy_value,
                "labels": {
                    "service": service,
                    "environment": "production",
                    "region": "us-east-1"
                }
            })
    
    await client.post(f"{BASE_URL}/ingest/metrics", json=metrics)
    print(f"   📈 Generated {len(metrics)} anomalous metrics")

async def simulate_error_logs(client, service, scenario):
    """Generate error logs"""
    logs = []
    
    error_messages = [
        "Connection timeout after 30s",
        "Database query exceeded timeout",
        "HTTP 500: Internal Server Error",
        "Memory allocation failed",
        "Circuit breaker OPEN: too many failures"
    ]
    
    for _ in range(random.randint(5, 15)):
        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": random.choice(["ERROR", "CRITICAL", "WARNING"]),
            "message": random.choice(error_messages),
            "service": service,
            "labels": {
                "environment": "production"
            }
        })
    
    await client.post(f"{BASE_URL}/ingest/logs", json=logs)
    print(f"   📝 Generated {len(logs)} error logs")

async def approve_and_execute_action(client, service, action_type):
    """Approve and execute the recommended action"""
    try:
        # Get pending actions
        response = await client.get(f"{BASE_URL}/api/v2/actions/pending")
        if response.status_code != 200:
            print("   ⚠️ No pending actions found")
            return
        
        data = response.json()
        actions = data.get("actions", [])
        
        # Find action for this service
        matching_action = None
        for action in actions:
            if action.get("service") == service and action.get("action_type") == action_type:
                matching_action = action
                break
        
        if not matching_action:
            print(f"   ⚠️ No {action_type} action found for {service}")
            return
        
        # Approve the action
        response = await client.post(f"{BASE_URL}/api/v2/actions/approve", json={
            "action_id": matching_action["id"],
            "approved_by": "training_script",
            "notes": "Auto-approved during training"
        })
        
        if response.status_code == 200:
            print(f"   ✅ Approved and executed: {action_type}")
        else:
            print(f"   ❌ Failed to approve action")
    
    except Exception as e:
        print(f"   ⚠️ Action approval error: {e}")

async def verify_training():
    """Check training results"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("\n🔍 Verifying Training Results...")
    print("=" * 60)
    
    # Check learning stats
    response = await client.get(f"{BASE_URL}/api/v2/learning/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"\n📚 Learning Statistics:")
        print(f"   • Total incidents learned: {stats['total_incidents_learned']}")
        print(f"   • Total actions recorded: {stats['total_actions_recorded']}")
        print(f"   • Services monitored: {stats['services_monitored']}")
    
    # Check incidents
    response = await client.get(f"{BASE_URL}/api/incidents?limit=100")
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Incident Statistics:")
        print(f"   • Total incidents: {data['total']}")
        
        by_severity = {}
        for incident in data['incidents']:
            severity = incident.get('severity', 'unknown')
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        for severity, count in by_severity.items():
            print(f"   • {severity.capitalize()}: {count}")
    
    await client.aclose()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    print("\n" + "=" * 60)
    print("🚀 DEPLOYR AI TRAINING SCRIPT")
    print("=" * 60)
    
    # Step 1: Generate training data
    await generate_training_data(num_incidents=50)
    
    # Step 2: Verify results
    await asyncio.sleep(5)
    await verify_training()
    
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE!")
    print("=" * 60)
    print("\n💡 Next Steps:")
    print("   1. Check the dashboard at http://localhost:8000/dashboard")
    print("   2. Review incidents and learning stats")
    print("   3. Test with real client metrics")
    print("   4. Enable autonomous mode when confident")

if __name__ == "__main__":
    asyncio.run(main())