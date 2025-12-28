import httpx
import time
import random
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def generate_baseline_metrics(service, metric_name, base_value, count=20):
    """Generate normal baseline metrics"""
    print(f"📊 Generating {count} baseline metrics for {service}...")
    
    for i in range(count):
        # Add small random variance
        value = base_value + random.uniform(-10, 10)
        
        metric = [{
            "timestamp": (datetime.utcnow() - timedelta(minutes=count-i)).isoformat() + "Z",
            "metric_name": metric_name,
            "value": value,
            "labels": {
                "service": service,
                "environment": "production"
            }
        }]
        
        try:
            response = httpx.post(f"{BASE_URL}/ingest/metrics", json=metric, timeout=5.0)
            if response.status_code == 200:
                print(f"   ✓ Sent {metric_name}: {value:.1f}")
            else:
                print(f"   ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        time.sleep(0.2)  # Small delay

def generate_anomaly(service, metric_name, anomaly_value):
    """Generate a single anomalous metric"""
    print(f"\n🚨 Generating ANOMALY for {service}...")
    
    metric = [{
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metric_name": metric_name,
        "value": anomaly_value,
        "labels": {
            "service": service,
            "environment": "production"
        }
    }]
    
    try:
        response = httpx.post(f"{BASE_URL}/ingest/metrics", json=metric, timeout=5.0)
        if response.status_code == 200:
            print(f"   ✓ Sent anomaly: {anomaly_value}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

def generate_error_logs(service, count=10):
    """Generate error logs"""
    print(f"\n📝 Generating {count} error logs for {service}...")
    
    error_messages = [
        "Database connection timeout after 30 seconds",
        "Request processing exceeded timeout limit",
        "Memory allocation failed - heap exhausted",
        "Connection pool exhausted - max connections reached",
        "Service degraded - high latency detected",
        "Failed to authenticate user token",
        "Rate limit exceeded for API endpoint",
        "External service timeout - no response",
        "Invalid request payload - schema validation failed",
        "Circuit breaker OPEN - service unavailable"
    ]
    
    logs = []
    for i in range(count):
        log = {
            "timestamp": (datetime.utcnow() - timedelta(seconds=count-i)).isoformat() + "Z",
            "level": random.choice(["ERROR", "ERROR", "ERROR", "CRITICAL"]),
            "message": random.choice(error_messages),
            "service": service,
            "labels": {
                "component": random.choice(["api", "database", "cache", "queue"]),
                "severity": "high"
            }
        }
        logs.append(log)
    
    try:
        response = httpx.post(f"{BASE_URL}/ingest/logs", json=logs, timeout=5.0)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Sent {len(logs)} logs ({result.get('errors_detected', 0)} errors)")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

def generate_deployment(service, version, status="success"):
    """Generate a deployment event"""
    print(f"\n🚀 Generating deployment for {service}...")
    
    deployment = {
        "timestamp": (datetime.utcnow() - timedelta(minutes=8)).isoformat() + "Z",
        "service": service,
        "version": version,
        "status": status,
        "metadata": {
            "commit": f"abc{random.randint(1000, 9999)}",
            "deployed_by": random.choice(["ci-cd-pipeline", "jenkins", "github-actions"]),
            "duration_seconds": random.randint(60, 300)
        }
    }
    
    try:
        response = httpx.post(f"{BASE_URL}/ingest/deployment", json=deployment, timeout=5.0)
        if response.status_code == 200:
            print(f"   ✓ Tracked deployment {version}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

def check_api_health():
    """Check if API is running"""
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def main():
    print_header("🧪 AI DevOps Autopilot - Dashboard Test Data Generator")
    
    # Check API health
    print("1️⃣ Checking API health...")
    if not check_api_health():
        print("   ❌ API is not running!")
        print("   Start it with: uvicorn src.main:app --reload")
        return
    print("   ✅ API is healthy")
    
    time.sleep(1)
    
    # Scenario 1: Auth API with latency spike
    print_header("Scenario 1: Auth API - Latency Spike")
    generate_baseline_metrics("auth-api", "api_latency_ms", 100, count=15)
    time.sleep(2)
    generate_deployment("auth-api", "v2.1.0")
    time.sleep(2)
    generate_anomaly("auth-api", "api_latency_ms", 1500)
    generate_anomaly("auth-api", "api_latency_ms", 1800)
    time.sleep(1)
    generate_error_logs("auth-api", count=8)
    
    time.sleep(3)
    
    # Scenario 2: Payment API with error rate spike
    print_header("Scenario 2: Payment API - Error Rate Spike")
    generate_baseline_metrics("payment-api", "api_latency_ms", 85, count=15)
    generate_baseline_metrics("payment-api", "error_rate", 0.2, count=15)
    time.sleep(2)
    generate_deployment("payment-api", "v1.8.3")
    time.sleep(1)
    generate_anomaly("payment-api", "error_rate", 12.5)
    generate_error_logs("payment-api", count=15)
    
    time.sleep(3)
    
    # Scenario 3: User API (healthy)
    print_header("Scenario 3: User API - Healthy Service")
    generate_baseline_metrics("user-api", "api_latency_ms", 75, count=20)
    generate_baseline_metrics("user-api", "error_rate", 0.1, count=20)
    
    time.sleep(2)
    
    # Scenario 4: Notification service with database issues
    print_header("Scenario 4: Notification Service - Database Issues")
    generate_baseline_metrics("notification-service", "db_connections", 45, count=15)
    time.sleep(2)
    generate_anomaly("notification-service", "db_connections", 98)
    generate_error_logs("notification-service", count=5)
    
    time.sleep(3)
    
    # Wait for worker to process
    print_header("⏳ Waiting for worker to process incidents...")
    print("   This may take 10-30 seconds for AI analysis...")
    print("   Watch the worker terminal for progress")
    time.sleep(5)
    
    # Test API endpoints
    print_header("🧪 Testing Dashboard API Endpoints")
    
    try:
        print("📊 Getting statistics...")
        response = httpx.get(f"{BASE_URL}/api/stats", timeout=5.0)
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✓ Active Incidents: {stats.get('active_incidents', 0)}")
            print(f"   ✓ Critical Anomalies: {stats.get('critical_anomalies', 0)}")
            print(f"   ✓ Healthy Services: {stats.get('healthy_services', 0)}/{stats.get('total_services', 0)}")
        
        print("\n🚨 Getting incidents...")
        response = httpx.get(f"{BASE_URL}/api/incidents?limit=10", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found {data.get('total', 0)} incidents")
            for incident in data.get('incidents', [])[:3]:
                print(f"   - {incident['service']}: {incident['severity']} ({incident['status']})")
        
        print("\n📈 Getting anomalies...")
        response = httpx.get(f"{BASE_URL}/api/anomalies?limit=10", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found {data.get('total', 0)} anomalies")
            for anomaly in data.get('anomalies', [])[:3]:
                print(f"   - {anomaly['service']}.{anomaly['metric_name']}: {anomaly['severity']}")
        
        print("\n🖥️  Getting services...")
        response = httpx.get(f"{BASE_URL}/api/services", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found {data.get('total', 0)} services")
            for service in data.get('services', []):
                print(f"   - {service['name']}: {service['status']} ({service['incident_count']} incidents)")
        
    except Exception as e:
        print(f"   ✗ API test failed: {e}")
    
    # Final instructions
    print_header("✅ Test Data Generation Complete!")
    print("📊 Dashboard should now show:")
    print("   - 2-3 active incidents")
    print("   - Multiple anomalies detected")
    print("   - 4 services with various health states")
    print("   - Recent deployments and error logs")
    print()
    print("🎯 Next Steps:")
    print("   1. Open the React dashboard artifact above")
    print("   2. Click 'Overview' to see all incidents")
    print("   3. Click 'Incidents' for detailed view")
    print("   4. Click 'Services' to check health status")
    print()
    print("💡 Tips:")
    print("   - Enable auto-refresh in the dashboard")
    print("   - Click on incidents for detailed analysis")
    print("   - Check Slack for incident alerts")
    print()
    print("🔄 To regenerate data:")
    print("   python test_dashboard.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()