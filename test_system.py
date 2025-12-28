import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

print("🧪 Testing AI DevOps Autopilot System\n")

# Test 1: Health check
print("1️⃣ Testing health endpoint...")
try:
    response = httpx.get(f"{BASE_URL}/health")
    print(f"   ✅ Status: {response.json()}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    print("   Make sure the API is running: uvicorn src.main:app --reload")
    exit(1)

time.sleep(1)

# Test 2: Send normal baseline metrics
print("\n2️⃣ Sending baseline metrics (normal latency)...")
for i in range(5):
    metric = [{
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metric_name": "api_latency_ms",
        "value": 100 + (i * 5),  # 100, 105, 110, 115, 120
        "labels": {"service": "auth-api"}
    }]
    
    response = httpx.post(f"{BASE_URL}/ingest/metrics", json=metric)
    print(f"   📊 Sent: {metric[0]['value']}ms - Response: {response.status_code}")
    time.sleep(2)

# Test 3: Send anomalous metric (huge spike!)
print("\n3️⃣ Sending ANOMALY (latency spike!)...")
anomaly_metric = [{
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "metric_name": "api_latency_ms",
    "value": 1500,  # 🚨 HUGE SPIKE!
    "labels": {"service": "auth-api"}
}]

response = httpx.post(f"{BASE_URL}/ingest/metrics", json=anomaly_metric)
print(f"   🚨 Sent: 1500ms spike - Response: {response.status_code}")

time.sleep(2)

# Test 4: Send another anomaly
print("\n4️⃣ Sending second anomaly...")
anomaly_metric2 = [{
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "metric_name": "api_latency_ms",
    "value": 1800,
    "labels": {"service": "auth-api"}
}]

response = httpx.post(f"{BASE_URL}/ingest/metrics", json=anomaly_metric2)
print(f"   🚨 Sent: 1800ms spike - Response: {response.status_code}")

time.sleep(2)

# Test 5: Send error logs
print("\n5️⃣ Sending error logs...")
logs = [
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": "Database connection timeout after 30 seconds",
        "service": "auth-api",
        "labels": {"component": "database"}
    },
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": "Request processing timeout",
        "service": "auth-api",
        "labels": {"component": "api"}
    },
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "CRITICAL",
        "message": "Service degraded - high latency detected",
        "service": "auth-api",
        "labels": {"severity": "high"}
    },
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": "Connection pool exhausted",
        "service": "auth-api",
        "labels": {"component": "database"}
    },
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": "Memory allocation failed",
        "service": "auth-api",
        "labels": {"component": "system"}
    }
]

response = httpx.post(f"{BASE_URL}/ingest/logs", json=logs)
print(f"   📝 Sent: {len(logs)} error logs - Response: {response.status_code}")

time.sleep(2)

# Test 6: Send deployment event (to correlate with incident)
print("\n6️⃣ Sending deployment event...")
deployment = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "service": "auth-api",
    "version": "v2.1.0",
    "status": "success",
    "metadata": {
        "commit": "abc123",
        "deployed_by": "ci-cd-pipeline"
    }
}

response = httpx.post(f"{BASE_URL}/ingest/deployment", json=deployment)
print(f"   🚀 Sent: deployment v2.1.0 - Response: {response.status_code}")

print("\n" + "="*60)
print("✅ Test data sent successfully!")
print("="*60)
print("\n👀 Now check:")
print("   1. Worker terminal - should show anomaly detection")
print("   2. Slack channel - should receive incident alert")
print("   3. Wait 10-15 seconds for AI analysis to complete")
print("\n💡 The worker might take a moment to correlate the data")
print("   and trigger the AI analysis. Be patient!")