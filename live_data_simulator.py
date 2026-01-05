#!/usr/bin/env python3
"""
🔴 LIVE Synthetic Data Generator for Dashboard Testing
======================================================
Generates continuous synthetic data to test dashboard real-time updates.
"""

import httpx
import time
import random
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"
client = httpx.Client(timeout=10.0)

# Services to simulate - All 35 services the AI model is trained on
SERVICES = [
    # Core Infrastructure
    "api-gateway", "nginx-ingress", "istio-mesh",
    # Authentication & User
    "auth-api", "user-service", "user-auth",
    # Payment & Commerce
    "payment-gateway", "payment-service", "order-processor", "order-service", "inventory-db",
    # Messaging & Notifications
    "notification-service", "notification-worker", "kafka-brokers", "rabbitmq-cluster",
    # Kubernetes
    "kubernetes-cluster", "k8s-cluster",
    # AWS Services
    "aws-ec2-fleet", "aws-rds-primary", "aws-lambda-functions", "web-frontend-asg",
    # GCP & Azure
    "gcp-gke-cluster", "azure-aks-cluster",
    # Databases
    "database-primary", "mongodb-replica", "redis-cluster", "postgresql-primary", "mysql-replica", "cache-redis",
    # Search & Analytics
    "elasticsearch-cluster", "analytics-pipeline",
    # Monitoring & Observability
    "logging-stack", "prometheus-server", "grafana-dashboards", "datadog-agent",
    # Security
    "vault-secrets", "waf-security", "security-waf", "cert-manager",
    # CI/CD & DevOps
    "jenkins-ci", "argocd-controller", "docker-registry", "harbor-registry", "sonarqube",
    # CDN
    "cdn-cloudfront"
]

def send_metrics(service: str, value: float, is_anomaly: bool = False):
    """Send a metric to the API"""
    metric = [{
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metric_name": "api_latency_ms",
        "value": value,
        "labels": {"service": service, "anomaly": str(is_anomaly).lower()}
    }]
    try:
        client.post(f"{BASE_URL}/ingest/metrics", json=metric)
        return True
    except:
        return False

def send_logs(service: str, level: str, message: str):
    """Send a log entry"""
    log = [{
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "service": service,
        "labels": {"component": random.choice(["database", "cache", "api", "worker"])}
    }]
    try:
        client.post(f"{BASE_URL}/ingest/logs", json=log)
        return True
    except:
        return False

def send_deployment(service: str, version: str):
    """Send a deployment event"""
    deployment = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": service,
        "version": version,
        "status": "success",
        "metadata": {"deployed_by": "live-test", "environment": "production"}
    }
    try:
        client.post(f"{BASE_URL}/ingest/deployment", json=deployment)
        return True
    except:
        return False

def print_status(message: str, icon: str = "📊"):
    """Print status with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {message}")

def run_live_simulation():
    """Run continuous live data simulation"""
    print("\n" + "="*60)
    print("🔴 LIVE DASHBOARD TEST - Synthetic Data Generator")
    print("="*60)
    print("📡 Sending data to:", BASE_URL)
    print("🖥️  Open dashboard at: file:///c:/Users/Daddy%20Sagar/ai-devops-autopilot/Deployr_dashboard.html")
    print("⏹️  Press Ctrl+C to stop\n")
    
    cycle = 0
    incident_mode = False
    incident_service = None
    
    try:
        while True:
            cycle += 1
            
            # Normal metrics for all services
            for service in SERVICES:
                if incident_mode and service == incident_service:
                    # Send anomaly metrics during incident
                    latency = random.uniform(800, 2500)
                    send_metrics(service, latency, is_anomaly=True)
                    print_status(f"🚨 {service}: {latency:.0f}ms (ANOMALY)", "⚠️")
                else:
                    # Normal metrics
                    latency = random.uniform(50, 150)
                    send_metrics(service, latency)
                    if cycle % 5 == 0:  # Print every 5th cycle
                        print_status(f"✅ {service}: {latency:.0f}ms", "📈")
            
            # Randomly trigger incidents
            if not incident_mode and random.random() < 0.1:  # 10% chance
                incident_mode = True
                incident_service = random.choice(SERVICES)
                print_status(f"🔥 INCIDENT STARTED on {incident_service}!", "🚨")
                
                # Send error logs
                error_messages = [
                    "Database connection timeout",
                    "Memory pressure detected",
                    "Request queue overflow",
                    "Connection pool exhausted"
                ]
                for msg in random.sample(error_messages, 2):
                    send_logs(incident_service, "ERROR", msg)
                    print_status(f"📝 ERROR: {msg}", "❌")
            
            # Randomly resolve incidents
            elif incident_mode and random.random() < 0.2:  # 20% chance to resolve
                print_status(f"✅ INCIDENT RESOLVED on {incident_service}", "🎉")
                send_logs(incident_service, "INFO", "Service recovered - metrics normalized")
                incident_mode = False
                incident_service = None
            
            # Occasional deployments
            if random.random() < 0.05:  # 5% chance
                service = random.choice(SERVICES)
                version = f"v{random.randint(1,5)}.{random.randint(0,20)}.{random.randint(0,100)}"
                send_deployment(service, version)
                print_status(f"🚀 Deployed {service} {version}", "🚀")
            
            # Status update every 10 cycles
            if cycle % 10 == 0:
                mode = "🔥 INCIDENT" if incident_mode else "✅ NORMAL"
                print_status(f"Cycle {cycle} - Mode: {mode}", "🔄")
            
            time.sleep(2)  # 2 second intervals
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 SIMULATION STOPPED")
        print(f"   Total cycles: {cycle}")
        print("="*60 + "\n")

if __name__ == "__main__":
    # Check server connectivity
    try:
        r = client.get(f"{BASE_URL}/health")
        if r.status_code != 200:
            print("❌ Server not healthy")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure the API is running on port 8000")
        sys.exit(1)
    
    run_live_simulation()
