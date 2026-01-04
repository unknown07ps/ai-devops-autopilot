"""
Deployr Demo Data Simulator
Simulates realistic DevOps incidents, actions, and metrics for dashboard demonstration
"""
import asyncio
import random
import datetime
import json
from typing import Dict, List, Any

# Simulated incident types with realistic scenarios
INCIDENT_SCENARIOS = [
    {
        "type": "kubernetes",
        "title": "Pod CrashLoopBackOff in payment-service",
        "description": "Payment service pod is repeatedly crashing due to OOM",
        "severity": "critical",
        "service": "payment-service",
        "suggested_action": "Increase memory limits from 512Mi to 1Gi"
    },
    {
        "type": "database",
        "title": "High connection pool exhaustion on PostgreSQL",
        "description": "Connection pool at 95% capacity, causing slow queries",
        "severity": "warning",
        "service": "postgres-primary",
        "suggested_action": "Scale read replicas and increase pool size"
    },
    {
        "type": "cloud",
        "title": "AWS EC2 instance unhealthy in ASG",
        "description": "Instance i-0abc123 failed health checks 3 times",
        "severity": "critical",
        "service": "web-frontend-asg",
        "suggested_action": "Terminate unhealthy instance and let ASG replace"
    },
    {
        "type": "application",
        "title": "Memory leak detected in user-auth microservice",
        "description": "Memory usage growing 5% per hour without release",
        "severity": "warning",
        "service": "user-auth",
        "suggested_action": "Rolling restart of service pods"
    },
    {
        "type": "network",
        "title": "Elevated latency on API Gateway",
        "description": "P99 latency increased from 50ms to 500ms",
        "severity": "critical",
        "service": "api-gateway",
        "suggested_action": "Check upstream service health and scale if needed"
    },
    {
        "type": "cicd",
        "title": "Deployment pipeline stuck in prod-release",
        "description": "Canary deployment at 10% showing elevated error rates",
        "severity": "warning",
        "service": "ci-pipeline",
        "suggested_action": "Rollback canary and investigate error logs"
    },
    {
        "type": "security",
        "title": "Unusual API access pattern detected",
        "description": "10x normal request rate from IP 192.168.1.100",
        "severity": "critical",
        "service": "security-waf",
        "suggested_action": "Enable rate limiting and investigate source"
    },
    {
        "type": "kubernetes",
        "title": "Node NotReady in cluster-prod-03",
        "description": "Worker node kubelet stopped reporting status",
        "severity": "critical",
        "service": "k8s-cluster",
        "suggested_action": "Drain node and restart kubelet service"
    },
]

SERVICES = [
    {"name": "api-gateway", "status": "healthy", "cpu": 45, "memory": 62, "requests_per_sec": 1250},
    {"name": "user-auth", "status": "degraded", "cpu": 78, "memory": 85, "requests_per_sec": 450},
    {"name": "payment-service", "status": "critical", "cpu": 92, "memory": 95, "requests_per_sec": 320},
    {"name": "order-service", "status": "healthy", "cpu": 35, "memory": 48, "requests_per_sec": 890},
    {"name": "inventory-db", "status": "healthy", "cpu": 55, "memory": 72, "requests_per_sec": 2100},
    {"name": "notification-worker", "status": "healthy", "cpu": 22, "memory": 38, "requests_per_sec": 150},
    {"name": "analytics-pipeline", "status": "warning", "cpu": 68, "memory": 75, "requests_per_sec": 5500},
    {"name": "logging-stack", "status": "healthy", "cpu": 42, "memory": 65, "requests_per_sec": 8900},
]

class DemoDataSimulator:
    def __init__(self):
        self.incidents: List[Dict] = []
        self.actions: List[Dict] = []
        self.outcomes: List[Dict] = []
        self.anomalies: List[Dict] = []
        self.services = SERVICES.copy()
        self.stats = {
            "healthy_services": 5,
            "degraded_services": 2,
            "critical_services": 1,
            "total_incidents_today": 0,
            "auto_remediated": 0,
            "pending_approval": 0
        }
        self.learning_stats = {
            "total_patterns": 580,
            "autonomous_safe": 45,
            "success_rate": 94,
            "patterns_promoted": 12
        }
        
    def generate_incident(self) -> Dict:
        """Generate a random realistic incident"""
        scenario = random.choice(INCIDENT_SCENARIOS)
        incident = {
            "id": f"INC-{random.randint(10000, 99999)}",
            "timestamp": datetime.datetime.now().isoformat(),
            "type": scenario["type"],
            "title": scenario["title"],
            "description": scenario["description"],
            "severity": scenario["severity"],
            "service": scenario["service"],
            "status": random.choice(["new", "analyzing", "action_proposed"]),
            "suggested_action": scenario["suggested_action"],
            "confidence": random.randint(85, 99),
            "affected_pods": random.randint(1, 5),
            "metrics": {
                "error_rate": round(random.uniform(0.5, 15.0), 2),
                "latency_p99": random.randint(100, 2000),
                "cpu_usage": random.randint(60, 98)
            }
        }
        return incident
    
    def generate_action(self, incident: Dict) -> Dict:
        """Generate a remediation action for an incident"""
        action = {
            "id": f"ACT-{random.randint(10000, 99999)}",
            "incident_id": incident["id"],
            "timestamp": datetime.datetime.now().isoformat(),
            "action_type": random.choice(["scale", "restart", "rollback", "config_change", "drain"]),
            "description": incident["suggested_action"],
            "status": "pending_approval",
            "confidence": incident["confidence"],
            "estimated_impact": random.choice(["low", "medium", "high"]),
            "rollback_available": True,
            "requires_approval": True
        }
        return action

    def simulate_events(self, num_incidents: int = 5) -> Dict:
        """Simulate a batch of events"""
        print(f"\n🚀 Deployr Demo Simulator Starting...")
        print(f"📊 Generating {num_incidents} realistic DevOps incidents...\n")
        
        for i in range(num_incidents):
            incident = self.generate_incident()
            self.incidents.append(incident)
            self.stats["total_incidents_today"] += 1
            
            # Generate action for some incidents
            if random.random() > 0.3:
                action = self.generate_action(incident)
                self.actions.append(action)
                self.stats["pending_approval"] += 1
            
            print(f"  [{incident['severity'].upper()}] {incident['title']}")
            print(f"      Service: {incident['service']} | Confidence: {incident['confidence']}%")
            
        # Generate some anomalies
        for _ in range(random.randint(5, 20)):
            self.anomalies.append({
                "id": f"ANOM-{random.randint(1000, 9999)}",
                "timestamp": datetime.datetime.now().isoformat(),
                "type": random.choice(["cpu_spike", "memory_leak", "traffic_surge", "error_burst"]),
                "severity": random.choice(["low", "medium", "high"]),
                "service": random.choice([s["name"] for s in self.services])
            })
        
        # Simulate some auto-remediated outcomes
        for _ in range(random.randint(3, 8)):
            self.outcomes.append({
                "id": f"OUT-{random.randint(1000, 9999)}",
                "timestamp": datetime.datetime.now().isoformat(),
                "action_type": random.choice(["scale", "restart", "config_change"]),
                "success": random.random() > 0.1,  # 90% success rate
                "confidence": random.randint(85, 99),
                "duration_seconds": random.randint(5, 120)
            })
            self.stats["auto_remediated"] += 1
        
        return self.get_dashboard_data()
    
    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard state"""
        return {
            "incidents": self.incidents,
            "pendingActions": self.actions,
            "outcomes": self.outcomes,
            "anomalies": self.anomalies,
            "services": self.services,
            "stats": self.stats,
            "learningStats": self.learning_stats,
            "autonomousStatus": {
                "execution_mode": "supervised",
                "autonomous_enabled": True,
                "user_plan": "trialing"
            }
        }


def main():
    print("=" * 60)
    print("  🤖 DEPLOYR - AI DevOps Autopilot Demo")
    print("  'Fix the oops. Without Ops.'")
    print("=" * 60)
    
    simulator = DemoDataSimulator()
    data = simulator.simulate_events(num_incidents=8)
    
    print(f"\n📈 Demo Summary:")
    print(f"   • Total Incidents: {len(data['incidents'])}")
    print(f"   • Pending Actions: {len(data['pendingActions'])}")
    print(f"   • Anomalies Detected: {len(data['anomalies'])}")
    print(f"   • Auto-Remediated: {data['stats']['auto_remediated']}")
    print(f"\n✅ Demo data generated! Refresh dashboard to see updates.")
    
    # Save to JSON for dashboard consumption
    with open("demo_data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"📁 Data saved to demo_data.json")
    
    return data


if __name__ == "__main__":
    main()
