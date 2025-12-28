import os
import asyncio
from dotenv import load_dotenv
from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ai_analyzer import AIIncidentAnalyzer
from src.api.slack_notifier import SlackNotifier

load_dotenv()

async def test_direct():
    print("🧪 Direct Anomaly Detection Test\n")
    
    # Initialize components
    detector = AnomalyDetector(os.getenv("REDIS_URL", "redis://localhost:6379"))
    analyzer = AIIncidentAnalyzer(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "llama3:latest")
    )
    slack = SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
    
    service = "auth-api"
    
    print("1️⃣ Sending baseline metrics...")
    # Send MORE baseline metrics to establish pattern
    baseline_values = [100, 105, 110, 115, 120, 108, 112, 98, 105, 110,
                       102, 108, 115, 110, 105, 112, 100, 108, 115, 110]
    
    for value in baseline_values:
        result = detector.detect_anomaly("api_latency_ms", service, value)
        if result:
            print(f"   ⚠️ Anomaly at {value}: {result}")
        else:
            print(f"   ✅ Normal: {value}ms")
    
    print("\n2️⃣ Sending ANOMALIES...")
    # Send anomalous metrics
    anomalies = []
    
    # First check what the baseline looks like
    baseline = detector.get_baseline("api_latency_ms", service)
    if baseline:
        print(f"   📊 Current baseline: mean={baseline['mean']:.2f}ms, std_dev={baseline['std_dev']:.2f}, count={baseline['count']}")
        print(f"   📊 Threshold for anomaly: {baseline['mean'] + (detector.std_dev_threshold * baseline['std_dev']):.2f}ms")
    
    for value in [1500, 1800]:
        result = detector.detect_anomaly("api_latency_ms", service, value)
        if result:
            print(f"   🚨 ANOMALY DETECTED: {value}ms")
            print(f"      Severity: {result['severity']}")
            print(f"      Z-score: {result['z_score']:.2f}")
            print(f"      Deviation: {result['deviation_percent']:.1f}%")
            anomalies.append(result)
            detector.store_anomaly(service, result)
        else:
            print(f"   ❓ No anomaly detected at {value}ms")
            if baseline:
                z_score = (value - baseline['mean']) / baseline['std_dev'] if baseline['std_dev'] > 0 else 0
                print(f"      Calculated z-score: {z_score:.2f} (threshold: {detector.std_dev_threshold})")
    
    print(f"\n3️⃣ Triggering AI Analysis...")
    print(f"   Anomalies to analyze: {len(anomalies)}")
    
    # Create some fake logs for context
    fake_logs = [
        {
            "timestamp": "2025-12-28T10:00:00Z",
            "level": "ERROR",
            "message": "Database connection timeout",
            "service": service
        },
        {
            "timestamp": "2025-12-28T10:00:05Z",
            "level": "CRITICAL",
            "message": "Service degraded - high latency",
            "service": service
        }
    ]
    
    # Create fake deployment
    fake_deployment = [
        {
            "version": "v2.1.0",
            "timestamp": "2025-12-28T09:55:00Z",
            "service": service
        }
    ]
    
    print("   🤖 Running AI analysis with Ollama...")
    analysis = analyzer.analyze_incident(
        anomalies=anomalies,
        recent_logs=fake_logs,
        recent_deployments=fake_deployment,
        service_name=service
    )
    
    print(f"\n4️⃣ Analysis Results:")
    print(f"   Root Cause: {analysis['root_cause']['description']}")
    print(f"   Confidence: {analysis['root_cause']['confidence']}%")
    print(f"   Severity: {analysis['severity']}")
    print(f"   Reasoning: {analysis['root_cause']['reasoning'][:100]}...")
    
    if analysis.get('recommended_actions'):
        print(f"\n   Recommended Actions:")
        for i, action in enumerate(analysis['recommended_actions'][:3], 1):
            print(f"   {i}. {action['action']} (Risk: {action['risk']})")
    
    print(f"\n5️⃣ Sending Slack Alert...")
    success = await slack.send_incident_alert(
        analysis=analysis,
        anomalies=anomalies,
        include_actions=True
    )
    
    if success:
        print("   ✅ Slack alert sent successfully!")
        print("   🎉 Check your Slack channel!")
    else:
        print("   ❌ Failed to send Slack alert")
        print("   Check your SLACK_WEBHOOK_URL in .env")
    
    print("\n" + "="*60)
    print("✅ Direct test complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_direct())