import os
import asyncio
import redis
from dotenv import load_dotenv
from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ai_analyzer import AIIncidentAnalyzer
from src.api.slack_notifier import SlackNotifier

load_dotenv()

async def test_clean():
    print("🧪 Clean Anomaly Detection Test\n")
    
    # Clear Redis completely first
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    print("🗑️  Clearing all Redis data...")
    redis_client.flushall()
    print("   ✅ Redis cleared\n")
    
    # Initialize fresh detector
    detector = AnomalyDetector(os.getenv("REDIS_URL", "redis://localhost:6379"))
    analyzer = AIIncidentAnalyzer(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "llama3:latest")
    )
    slack = SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
    
    service = "payment-api"  # Different service to avoid any caching
    metric_name = "request_latency_ms"
    
    print("1️⃣ Building baseline (20 samples)...")
    baseline_values = [100, 105, 110, 115, 120, 108, 112, 98, 105, 110,
                       102, 108, 115, 110, 105, 112, 100, 108, 115, 110]
    
    for i, value in enumerate(baseline_values, 1):
        result = detector.detect_anomaly(metric_name, service, value)
        if result:
            print(f"   [{i}/20] ⚠️ Unexpected anomaly at {value}ms")
        else:
            print(f"   [{i}/20] ✅ {value}ms")
    
    # Check baseline
    baseline = detector.get_baseline(metric_name, service)
    print(f"\n📊 Baseline established:")
    print(f"   Mean: {baseline['mean']:.2f}ms")
    print(f"   Std Dev: {baseline['std_dev']:.2f}ms")
    print(f"   Count: {baseline['count']} samples")
    print(f"   Anomaly threshold: {baseline['mean'] + (2.5 * baseline['std_dev']):.2f}ms")
    
    print("\n2️⃣ Sending MASSIVE SPIKES...")
    anomalies = []
    
    for value in [1500, 2000, 1800]:
        print(f"\n   Testing {value}ms...")
        result = detector.detect_anomaly(metric_name, service, value)
        
        if result:
            print(f"   🚨 ANOMALY DETECTED!")
            print(f"      Current: {result['current_value']:.0f}ms vs Baseline: {result['baseline_mean']:.0f}ms")
            print(f"      Z-score: {result['z_score']:.2f}")
            print(f"      Deviation: {result['deviation_percent']:+.0f}%")
            print(f"      Severity: {result['severity'].upper()}")
            anomalies.append(result)
            detector.store_anomaly(service, result)
        else:
            print(f"   ❌ NOT detected as anomaly (this is a bug)")
            # Manual calculation for debugging
            z = (value - baseline['mean']) / baseline['std_dev']
            print(f"      Z-score should be: {z:.2f}")
    
    if not anomalies:
        print("\n❌ ANOMALY DETECTION FAILED!")
        print("   The detector has a bug - 1500ms should definitely be anomalous vs 108ms baseline")
        return
    
    print(f"\n✅ Detected {len(anomalies)} anomalies!")
    
    print(f"\n3️⃣ AI Analysis...")
    
    fake_logs = [
        {"timestamp": "2025-12-28T10:00:00Z", "level": "ERROR", 
         "message": "Payment processing timeout", "service": service},
        {"timestamp": "2025-12-28T10:00:05Z", "level": "CRITICAL",
         "message": "Multiple transaction failures", "service": service},
        {"timestamp": "2025-12-28T10:00:10Z", "level": "ERROR",
         "message": "Database pool exhausted", "service": service}
    ]
    
    fake_deployment = [
        {"version": "v3.2.1", "timestamp": "2025-12-28T09:50:00Z", "service": service}
    ]
    
    print("   🤖 Analyzing with Ollama...")
    analysis = analyzer.analyze_incident(
        anomalies=anomalies,
        recent_logs=fake_logs,
        recent_deployments=fake_deployment,
        service_name=service
    )
    
    print(f"\n4️⃣ Results:")
    print(f"   Root Cause: {analysis['root_cause']['description']}")
    print(f"   Confidence: {analysis['root_cause']['confidence']}%")
    print(f"   Severity: {analysis['severity']}")
    
    print(f"\n5️⃣ Sending to Slack...")
    success = await slack.send_incident_alert(analysis=analysis, anomalies=anomalies)
    
    if success:
        print("   ✅ Alert sent!")
        print("\n" + "="*60)
        print("🎉 SUCCESS! Check your Slack channel!")
        print("="*60)
    else:
        print("   ❌ Slack failed")

if __name__ == "__main__":
    asyncio.run(test_clean())