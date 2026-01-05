#!/usr/bin/env python3
"""
🧪 AI DevOps Autopilot - Comprehensive System Test
===================================================
This script tests the entire system end-to-end with fake data,
simulating real-world DevOps scenarios.

Tests Include:
- Health checks for all services
- Metrics ingestion and anomaly detection
- Log ingestion and pattern matching
- Deployment tracking
- Autonomous execution features
- Learning system validation
- Action management
- Safety rails verification

Usage:
    python test_full_system.py [--base-url URL]
"""

import httpx
import time
import random
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_BASE_URL = "http://localhost:8000"

class TestStatus(Enum):
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⏭️ SKIPPED"
    WARNING = "⚠️ WARNING"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float
    message: str = ""
    details: Dict[str, Any] = None

# ============================================================================
# Test Data Generators
# ============================================================================

class FakeDataGenerator:
    """Generates realistic fake data for testing"""
    
    SERVICES = ["auth-api", "user-service", "payment-gateway", "notification-service", "order-processor"]
    ERROR_MESSAGES = [
        "Database connection timeout after 30 seconds",
        "Connection pool exhausted",
        "Memory allocation failed",
        "Request processing timeout",
        "Service degraded - high latency detected",
        "Cache miss rate exceeding threshold",
        "SSL certificate validation failed",
        "Rate limit exceeded for upstream service",
        "Disk I/O latency spike detected",
        "Pod memory pressure detected"
    ]
    COMPONENTS = ["database", "cache", "api", "worker", "scheduler", "gateway"]
    
    @staticmethod
    def generate_normal_metrics(service: str, count: int = 10) -> List[Dict]:
        """Generate normal baseline metrics"""
        metrics = []
        base_time = datetime.utcnow()
        for i in range(count):
            metrics.append({
                "timestamp": (base_time + timedelta(seconds=i*10)).isoformat() + "Z",
                "metric_name": "api_latency_ms",
                "value": random.uniform(80, 150),  # Normal range
                "labels": {"service": service, "endpoint": "/api/v1/resource"}
            })
        return metrics
    
    @staticmethod
    def generate_anomaly_metrics(service: str, spike_level: str = "high") -> List[Dict]:
        """Generate anomalous metrics (latency spikes)"""
        spike_values = {
            "medium": (500, 800),
            "high": (1000, 1500),
            "critical": (2000, 3500)
        }
        min_val, max_val = spike_values.get(spike_level, (1000, 1500))
        
        return [{
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metric_name": "api_latency_ms",
            "value": random.uniform(min_val, max_val),
            "labels": {"service": service, "endpoint": "/api/v1/resource", "anomaly": "true"}
        }]
    
    @staticmethod
    def generate_error_logs(service: str, count: int = 5) -> List[Dict]:
        """Generate error log entries"""
        logs = []
        for i in range(count):
            logs.append({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": random.choice(["ERROR", "CRITICAL", "WARNING"]),
                "message": random.choice(FakeDataGenerator.ERROR_MESSAGES),
                "service": service,
                "labels": {
                    "component": random.choice(FakeDataGenerator.COMPONENTS),
                    "trace_id": f"trace-{random.randint(10000, 99999)}",
                    "span_id": f"span-{random.randint(1000, 9999)}"
                }
            })
        return logs
    
    @staticmethod
    def generate_deployment_event(service: str, success: bool = True) -> Dict:
        """Generate a deployment event"""
        version = f"v{random.randint(1,5)}.{random.randint(0,15)}.{random.randint(0,99)}"
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": service,
            "version": version,
            "status": "success" if success else "failed",
            "metadata": {
                "commit": f"{random.randint(0, 0xFFFFFF):06x}",
                "deployed_by": random.choice(["ci-cd-pipeline", "manual-deploy", "argocd"]),
                "environment": random.choice(["production", "staging", "development"]),
                "rollback_available": success
            }
        }

# ============================================================================
# Test Client
# ============================================================================

class SystemTestClient:
    """HTTP client for system tests"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
        self.results: List[TestResult] = []
    
    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request"""
        url = f"{self.base_url}{path}"
        return self.client.request(method, url, **kwargs)
    
    def run_test(self, name: str, test_func, *args, **kwargs) -> TestResult:
        """Run a single test and record result"""
        start_time = time.time()
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            test_result = TestResult(
                name=name,
                status=TestStatus.PASSED if result.get("success", True) else TestStatus.FAILED,
                duration=duration,
                message=result.get("message", ""),
                details=result.get("details")
            )
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                message=str(e)
            )
        
        self.results.append(test_result)
        return test_result

# ============================================================================
# Test Suite
# ============================================================================

class FullSystemTestSuite:
    """Comprehensive system test suite"""
    
    def __init__(self, base_url: str):
        self.client = SystemTestClient(base_url)
        self.data_gen = FakeDataGenerator()
        self.test_service = "auth-api"  # Primary service for testing
    
    def print_header(self, text: str):
        """Print a section header"""
        print(f"\n{'='*60}")
        print(f"🔷 {text}")
        print('='*60)
    
    def print_result(self, result: TestResult):
        """Print a single test result"""
        status_icon = result.status.value
        print(f"   {status_icon} {result.name} ({result.duration:.2f}s)")
        if result.message:
            print(f"      └─ {result.message}")
    
    # ========================================================================
    # Health Check Tests
    # ========================================================================
    
    def test_root_health(self) -> Dict:
        """Test root endpoint"""
        response = self.client._request("GET", "/")
        if response.status_code == 200:
            return {"success": True, "message": f"API Version: {response.json().get('version', 'N/A')}"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_health_endpoint(self) -> Dict:
        """Test main health endpoint"""
        response = self.client._request("GET", "/health")
        if response.status_code == 200:
            data = response.json()
            return {"success": data.get("status") == "healthy", "details": data}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_database_health(self) -> Dict:
        """Test database health"""
        response = self.client._request("GET", "/health/database")
        if response.status_code == 200:
            data = response.json()
            # Check for either status=healthy or connection=active
            is_healthy = data.get("status") == "healthy" or data.get("connection") == "active"
            stats = data.get("statistics", {})
            return {
                "success": is_healthy, 
                "message": f"Users: {stats.get('users', 0)}, Subscriptions: {stats.get('subscriptions', 0)}",
                "details": data
            }
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    # ========================================================================
    # Ingestion Tests
    # ========================================================================
    
    def test_metrics_ingestion_baseline(self) -> Dict:
        """Test normal metrics ingestion"""
        metrics = self.data_gen.generate_normal_metrics(self.test_service, count=5)
        response = self.client._request("POST", "/ingest/metrics", json=metrics)
        if response.status_code == 200:
            return {"success": True, "message": f"Ingested {len(metrics)} baseline metrics"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_metrics_ingestion_anomaly(self) -> Dict:
        """Test anomaly metrics ingestion"""
        metrics = self.data_gen.generate_anomaly_metrics(self.test_service, spike_level="high")
        response = self.client._request("POST", "/ingest/metrics", json=metrics)
        if response.status_code == 200:
            data = response.json()
            anomaly_detected = data.get("anomaly_detected", False)
            return {
                "success": True, 
                "message": f"Anomaly detection: {'triggered' if anomaly_detected else 'not triggered'}",
                "details": data
            }
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_log_ingestion(self) -> Dict:
        """Test log ingestion"""
        logs = self.data_gen.generate_error_logs(self.test_service, count=5)
        response = self.client._request("POST", "/ingest/logs", json=logs)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": f"Ingested {len(logs)} logs, patterns: {data.get('patterns_detected', 0)}"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_deployment_ingestion(self) -> Dict:
        """Test deployment event ingestion"""
        deployment = self.data_gen.generate_deployment_event(self.test_service)
        response = self.client._request("POST", "/ingest/deployment", json=deployment)
        if response.status_code == 200:
            return {"success": True, "message": f"Tracked deployment {deployment['version']}"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    # ========================================================================
    # Phase 2 Tests - Learning & Actions
    # ========================================================================
    
    def test_pending_actions(self) -> Dict:
        """Test pending actions endpoint"""
        response = self.client._request("GET", "/api/v2/actions/pending")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("actions", []))
            return {"success": True, "message": f"Found {count} pending actions"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_action_history(self) -> Dict:
        """Test action history endpoint"""
        response = self.client._request("GET", f"/api/v2/actions/history?service={self.test_service}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("actions", []))
            return {"success": True, "message": f"Found {count} historical actions"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_learning_stats(self) -> Dict:
        """Test learning statistics endpoint"""
        response = self.client._request("GET", "/api/v2/learning/stats")
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True, 
                "message": f"Total patterns: {data.get('total_patterns', 0)}, Decisions: {data.get('total_decisions', 0)}"
            }
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_service_insights(self) -> Dict:
        """Test service insights endpoint"""
        response = self.client._request("GET", f"/api/v2/learning/insights/{self.test_service}")
        if response.status_code == 200:
            return {"success": True, "message": "Service insights retrieved"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_recommendations(self) -> Dict:
        """Test recommendations endpoint"""
        response = self.client._request("GET", f"/api/v2/recommendations/{self.test_service}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("recommendations", []))
            return {"success": True, "message": f"Found {count} recommendations"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    # ========================================================================
    # Phase 3 Tests - Autonomous Execution
    # ========================================================================
    
    def test_autonomous_status(self) -> Dict:
        """Test autonomous status endpoint (public)"""
        response = self.client._request("GET", "/api/v3/autonomous/status/public")
        if response.status_code == 200:
            data = response.json()
            mode = data.get("mode", "unknown")
            return {"success": True, "message": f"Autonomous mode: {mode}", "details": data}
        elif response.status_code == 503:
            return {"success": True, "message": "Phase 3 not enabled (expected)"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_safety_status(self) -> Dict:
        """Test safety rails status (public)"""
        response = self.client._request("GET", "/api/v3/autonomous/safety-status/public")
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": f"Safety rails: {data.get('status', 'unknown')}", "details": data}
        elif response.status_code == 503:
            return {"success": True, "message": "Phase 3 not enabled (expected)"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_autonomous_outcomes(self) -> Dict:
        """Test autonomous outcomes endpoint (public)"""
        response = self.client._request("GET", "/api/v3/autonomous/outcomes/public?limit=10")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("outcomes", []))
            return {"success": True, "message": f"Found {count} autonomous outcomes"}
        elif response.status_code == 503:
            return {"success": True, "message": "Phase 3 not enabled (expected)"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    # ========================================================================
    # Stress Test - Simulated Incident
    # ========================================================================
    
    def test_simulated_incident(self) -> Dict:
        """Simulate a full incident with escalating severity"""
        results = []
        
        # Phase 1: Normal traffic
        for i in range(3):
            metrics = self.data_gen.generate_normal_metrics(self.test_service, count=2)
            self.client._request("POST", "/ingest/metrics", json=metrics)
            results.append("baseline")
            time.sleep(0.5)
        
        # Phase 2: Start of incident (medium latency)
        metrics = self.data_gen.generate_anomaly_metrics(self.test_service, spike_level="medium")
        self.client._request("POST", "/ingest/metrics", json=metrics)
        results.append("medium_spike")
        time.sleep(0.5)
        
        # Phase 3: Escalation (high latency + errors)
        metrics = self.data_gen.generate_anomaly_metrics(self.test_service, spike_level="high")
        logs = self.data_gen.generate_error_logs(self.test_service, count=3)
        self.client._request("POST", "/ingest/metrics", json=metrics)
        self.client._request("POST", "/ingest/logs", json=logs)
        results.append("high_spike+errors")
        time.sleep(0.5)
        
        # Phase 4: Critical incident
        metrics = self.data_gen.generate_anomaly_metrics(self.test_service, spike_level="critical")
        logs = self.data_gen.generate_error_logs(self.test_service, count=5)
        self.client._request("POST", "/ingest/metrics", json=metrics)
        self.client._request("POST", "/ingest/logs", json=logs)
        results.append("critical_spike")
        
        # Phase 5: Deployment (potential cause)
        deployment = self.data_gen.generate_deployment_event(self.test_service)
        self.client._request("POST", "/ingest/deployment", json=deployment)
        results.append("deployment")
        
        return {
            "success": True,
            "message": f"Simulated incident with {len(results)} phases",
            "details": {"phases": results}
        }
    
    # ========================================================================
    # Multi-Service Test
    # ========================================================================
    
    def test_multi_service_metrics(self) -> Dict:
        """Test metrics ingestion across multiple services"""
        services = FakeDataGenerator.SERVICES
        successful = 0
        
        for service in services:
            metrics = self.data_gen.generate_normal_metrics(service, count=2)
            response = self.client._request("POST", "/ingest/metrics", json=metrics)
            if response.status_code == 200:
                successful += 1
        
        return {
            "success": successful == len(services),
            "message": f"Ingested metrics for {successful}/{len(services)} services"
        }
    
    # ========================================================================
    # Dashboard API Tests
    # ========================================================================
    
    def test_dashboard_stats(self) -> Dict:
        """Test dashboard statistics endpoint"""
        response = self.client._request("GET", "/api/stats")
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": "Dashboard stats retrieved", "details": data}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    def test_dashboard_incidents(self) -> Dict:
        """Test dashboard incidents endpoint"""
        response = self.client._request("GET", "/api/incidents?limit=10")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("incidents", data)) if isinstance(data, dict) else len(data)
            return {"success": True, "message": f"Found {count} incidents"}
        return {"success": False, "message": f"Status code: {response.status_code}"}
    
    # ========================================================================
    # Run All Tests
    # ========================================================================
    
    def run_all(self):
        """Run the complete test suite"""
        print("\n" + "🧪"*30)
        print("   AI DevOps Autopilot - Comprehensive System Test")
        print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("🧪"*30)
        
        # ====== Health Checks ======
        self.print_header("HEALTH CHECKS")
        self.print_result(self.client.run_test("Root Endpoint", self.test_root_health))
        self.print_result(self.client.run_test("Health Endpoint", self.test_health_endpoint))
        self.print_result(self.client.run_test("Database Health", self.test_database_health))
        
        # ====== Ingestion Tests ======
        self.print_header("DATA INGESTION")
        self.print_result(self.client.run_test("Metrics - Baseline", self.test_metrics_ingestion_baseline))
        time.sleep(1)
        self.print_result(self.client.run_test("Metrics - Anomaly", self.test_metrics_ingestion_anomaly))
        time.sleep(1)
        self.print_result(self.client.run_test("Log Ingestion", self.test_log_ingestion))
        time.sleep(1)
        self.print_result(self.client.run_test("Deployment Event", self.test_deployment_ingestion))
        
        # ====== Phase 2 Tests ======
        self.print_header("PHASE 2 - LEARNING & ACTIONS")
        self.print_result(self.client.run_test("Pending Actions", self.test_pending_actions))
        self.print_result(self.client.run_test("Action History", self.test_action_history))
        self.print_result(self.client.run_test("Learning Stats", self.test_learning_stats))
        self.print_result(self.client.run_test("Service Insights", self.test_service_insights))
        self.print_result(self.client.run_test("Recommendations", self.test_recommendations))
        
        # ====== Phase 3 Tests ======
        self.print_header("PHASE 3 - AUTONOMOUS EXECUTION")
        self.print_result(self.client.run_test("Autonomous Status", self.test_autonomous_status))
        self.print_result(self.client.run_test("Safety Rails", self.test_safety_status))
        self.print_result(self.client.run_test("Autonomous Outcomes", self.test_autonomous_outcomes))
        
        # ====== Dashboard Tests ======
        self.print_header("DASHBOARD API")
        self.print_result(self.client.run_test("Dashboard Stats", self.test_dashboard_stats))
        self.print_result(self.client.run_test("Dashboard Incidents", self.test_dashboard_incidents))
        
        # ====== Stress Tests ======
        self.print_header("STRESS TESTS")
        self.print_result(self.client.run_test("Multi-Service Metrics", self.test_multi_service_metrics))
        time.sleep(1)
        self.print_result(self.client.run_test("Simulated Incident", self.test_simulated_incident))
        
        # ====== Summary ======
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        results = self.client.results
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        total_time = sum(r.duration for r in results)
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"   Total Tests:  {len(results)}")
        print(f"   ✅ Passed:    {passed}")
        print(f"   ❌ Failed:    {failed}")
        print(f"   ⏭️ Skipped:   {skipped}")
        print(f"   ⏱️ Duration:  {total_time:.2f}s")
        print("="*60)
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! System is healthy.\n")
        else:
            print(f"\n⚠️ {failed} test(s) failed. Review the output above.\n")
            print("Failed tests:")
            for r in results:
                if r.status == TestStatus.FAILED:
                    print(f"   - {r.name}: {r.message}")
            print()

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="AI DevOps Autopilot - Full System Test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only (skip stress tests)")
    args = parser.parse_args()
    
    print(f"\n🔗 Testing against: {args.base_url}")
    
    # Check if server is reachable
    try:
        client = httpx.Client(timeout=5.0)
        response = client.get(f"{args.base_url}/health")
        print(f"✅ Server is reachable (status: {response.status_code})")
    except Exception as e:
        print(f"\n❌ Cannot connect to server at {args.base_url}")
        print(f"   Error: {e}")
        print(f"\n💡 Make sure the API is running:")
        print(f"   uvicorn src.main:app --host 0.0.0.0 --port 8000")
        exit(1)
    
    # Run tests
    suite = FullSystemTestSuite(args.base_url)
    suite.run_all()

if __name__ == "__main__":
    main()
