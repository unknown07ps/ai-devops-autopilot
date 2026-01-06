"""
Intelligence Features Integrity Test
=====================================
Tests all 5 new Intelligence features added to AI DevOps Autopilot:
1. Production Knowledge Model
2. Alert Noise Suppression  
3. MTTR Acceleration Engine
4. Incident Timeline Generator
5. Cloud Cost Incident Handler
"""

import asyncio
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List
import traceback

# Add src to path
sys.path.insert(0, '.')

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")
    test_results["tests"].append({"name": name, "passed": passed, "details": details})
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1

def test_header(section: str):
    """Print test section header"""
    print(f"\n{'='*60}")
    print(f"  {section}")
    print(f"{'='*60}\n")


# ============================================================================
# TEST 1: Production Knowledge Model
# ============================================================================

def test_production_knowledge_model():
    """Test ProductionKnowledgeModel class"""
    test_header("1. PRODUCTION KNOWLEDGE MODEL")
    
    try:
        from src.model.production_knowledge import (
            ProductionKnowledgeModel, 
            ServiceNode, 
            DependencyEdge,
            ServiceType,
            HealthStatus
        )
        log_test("Import ProductionKnowledgeModel", True)
    except ImportError as e:
        log_test("Import ProductionKnowledgeModel", False, str(e))
        return
    
    # Test ServiceNode dataclass (correct fields from source)
    try:
        node = ServiceNode(
            service_id="test-service",
            name="Test Service",
            service_type=ServiceType.MICROSERVICE.value,
            team="platform",
            owner="platform-team",
            criticality_tier=1,
            health_status=HealthStatus.HEALTHY.value,
            replica_count=3,
            current_version="v1.0.0",
            avg_latency_ms=25.0,
            avg_error_rate=0.1,
            avg_requests_per_second=100.0,
            avg_cpu_usage=45.0,
            avg_memory_usage=60.0
        )
        log_test("Create ServiceNode", True, f"service_id={node.service_id}")
    except Exception as e:
        log_test("Create ServiceNode", False, str(e))
    
    # Test DependencyEdge dataclass (correct fields from source)
    try:
        edge = DependencyEdge(
            edge_id="svc-a->svc-b",
            source_service="svc-a",
            target_service="svc-b",
            dependency_type="sync_http",
            is_critical=True,
            is_async=False,
            has_fallback=False,
            avg_latency_ms=15.0,
            avg_calls_per_second=50.0,
            error_rate=0.01
        )
        log_test("Create DependencyEdge", True, f"{edge.source_service} -> {edge.target_service}")
    except Exception as e:
        log_test("Create DependencyEdge", False, str(e))
    
    # Test ServiceType enum
    try:
        types = [t.value for t in ServiceType]
        log_test("ServiceType enum", True, f"{len(types)} types: {types[:4]}...")
    except Exception as e:
        log_test("ServiceType enum", False, str(e))
    
    # Test HealthStatus enum
    try:
        statuses = [s.value for s in HealthStatus]
        log_test("HealthStatus enum", True, f"{len(statuses)} statuses: {statuses}")
    except Exception as e:
        log_test("HealthStatus enum", False, str(e))
    
    print("  → Production Knowledge Model: Structure verified")


# ============================================================================
# TEST 2: Alert Noise Suppression
# ============================================================================

def test_alert_noise_suppression():
    """Test AlertNoiseSuppressor class"""
    test_header("2. ALERT NOISE SUPPRESSION")
    
    try:
        from src.alerts.noise_suppressor import (
            AlertNoiseSuppressor,
            AlertContext,
            TriageDecision,
            AlertDisposition,
            SuppressionReason
        )
        log_test("Import AlertNoiseSuppressor", True)
    except ImportError as e:
        log_test("Import AlertNoiseSuppressor", False, str(e))
        return
    
    # Test AlertContext dataclass
    try:
        alert = AlertContext(
            service="api-gateway",
            alert_name="High CPU Usage",
            severity="warning",
            labels={"env": "prod"},
            value=85.0,
            threshold=80.0,
            message="CPU usage is above threshold",
            source="prometheus",
            timestamp="2024-01-01T00:00:00Z"
        )
        log_test("Create AlertContext", True, f"service={alert.service}")
    except Exception as e:
        log_test("Create AlertContext", False, str(e))
    
    # Test AlertDisposition enum
    try:
        dispositions = [d.value for d in AlertDisposition]
        log_test("AlertDisposition enum", True, f"{len(dispositions)} dispositions: {dispositions[:3]}...")
    except Exception as e:
        log_test("AlertDisposition enum", False, str(e))
    
    # Test SuppressionReason enum
    try:
        reasons = [r.value for r in SuppressionReason]
        log_test("SuppressionReason enum", True, f"{len(reasons)} reasons defined")
    except Exception as e:
        log_test("SuppressionReason enum", False, str(e))
    
    print("  → Alert Noise Suppression: Structure verified")


# ============================================================================
# TEST 3: MTTR Acceleration Engine
# ============================================================================

def test_mttr_acceleration():
    """Test MTTRAccelerator class"""
    test_header("3. MTTR ACCELERATION ENGINE")
    
    try:
        from src.acceleration.mttr_engine import (
            MTTRAccelerator,
            AnalysisResult,
            RemediationPlan,
            AnalysisStrategy
        )
        log_test("Import MTTRAccelerator", True)
    except ImportError as e:
        log_test("Import MTTRAccelerator", False, str(e))
        return
    
    # Test AnalysisStrategy enum
    try:
        strategies = [s.value for s in AnalysisStrategy]
        log_test("AnalysisStrategy enum", True, f"{len(strategies)} strategies: {strategies}")
    except Exception as e:
        log_test("AnalysisStrategy enum", False, str(e))
    
    # Test AnalysisResult dataclass (correct fields from source)
    try:
        result = AnalysisResult(
            strategy=AnalysisStrategy.LOG_ANALYSIS.value,  # string, not enum
            success=True,
            confidence=85.0,
            root_cause="Memory leak detected",
            contributing_factors=["High memory usage", "Possible memory leak"],
            evidence=[{"type": "log", "pattern": "OOM"}],
            execution_time_ms=45.0
        )
        log_test("Create AnalysisResult", True, f"strategy={result.strategy}, confidence={result.confidence}")
    except Exception as e:
        log_test("Create AnalysisResult", False, str(e))
    
    # Test RemediationPlan dataclass (correct fields from source)
    try:
        plan = RemediationPlan(
            plan_id="plan-123",
            action_type="rollback",
            priority=1,
            prerequisites=["Previous version available"],
            steps=[{"action": "rollback_deployment"}],
            rollback_steps=[{"action": "redeploy"}],
            estimated_impact="Brief interruption",
            estimated_time_minutes=5.0,
            risk_level="low",
            ready_to_execute=True
        )
        log_test("Create RemediationPlan", True, f"action_type={plan.action_type}")
    except Exception as e:
        log_test("Create RemediationPlan", False, str(e))
    
    print("  → MTTR Acceleration Engine: Structure verified")


# ============================================================================
# TEST 4: Incident Timeline Generator
# ============================================================================

def test_incident_timeline():
    """Test IncidentTimelineGenerator class"""
    test_header("4. INCIDENT TIMELINE GENERATOR")
    
    try:
        from src.timeline.incident_timeline import (
            IncidentTimelineGenerator,
            TimelineEvent,
            IncidentTimeline,
            TimelineEventType,
            EventSource
        )
        log_test("Import IncidentTimelineGenerator", True)
    except ImportError as e:
        log_test("Import IncidentTimelineGenerator", False, str(e))
        return
    
    # Test TimelineEventType enum
    try:
        types = [t.value for t in TimelineEventType]
        log_test("TimelineEventType enum", True, f"{len(types)} types: {types[:5]}...")
    except Exception as e:
        log_test("TimelineEventType enum", False, str(e))
    
    # Test EventSource enum
    try:
        sources = [s.value for s in EventSource]
        log_test("EventSource enum", True, f"{len(sources)} sources: {sources}")
    except Exception as e:
        log_test("EventSource enum", False, str(e))
    
    # Test TimelineEvent dataclass (event_type and source are strings, not enums)
    try:
        event = TimelineEvent(
            event_id="evt-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=TimelineEventType.DEPLOYMENT.value,  # string
            source=EventSource.CI_CD.value,  # string
            title="Deployment Started",
            description="Deploying v2.3.1",
            severity="info",
            service="payment-service"
        )
        log_test("Create TimelineEvent", True, f"type={event.event_type}")
    except Exception as e:
        log_test("Create TimelineEvent", False, str(e))
    
    print("  → Incident Timeline Generator: Structure verified")


# ============================================================================
# TEST 5: Cloud Cost Incident Handler
# ============================================================================

def test_cost_incident_handler():
    """Test CloudCostIncidentHandler class"""
    test_header("5. CLOUD COST INCIDENT HANDLER")
    
    try:
        from src.cost.cost_incident_handler import (
            CloudCostIncidentHandler,
            CostAnomaly,
            CostIncident,
            CostAnomalyType,
            RemediationAction
        )
        log_test("Import CloudCostIncidentHandler", True)
    except ImportError as e:
        log_test("Import CloudCostIncidentHandler", False, str(e))
        return
    
    # Test CostAnomalyType enum
    try:
        types = [t.value for t in CostAnomalyType]
        log_test("CostAnomalyType enum", True, f"{len(types)} types: {types}")
    except Exception as e:
        log_test("CostAnomalyType enum", False, str(e))
    
    # Test RemediationAction enum
    try:
        actions = [a.value for a in RemediationAction]
        log_test("RemediationAction enum", True, f"{len(actions)} actions: {actions[:4]}...")
    except Exception as e:
        log_test("RemediationAction enum", False, str(e))
    
    # Test CostAnomaly dataclass (uses string for anomaly_type, not enum)
    try:
        anomaly = CostAnomaly(
            anomaly_id="cost-123",
            anomaly_type=CostAnomalyType.SPIKE.value,  # Use string value
            severity="high",
            current_spend=340.0,
            baseline_spend=50.0,
            deviation_percent=580.0,
            estimated_daily_impact=6960.0,
            service="data-pipeline",
            region="us-east-1",
            account_id="123456789",
            resource_ids=["i-abc123"],
            detected_at=datetime.now(timezone.utc).isoformat(),
            detection_method="spike_detection",
            confidence=85.0,
            status="detected"
        )
        log_test("Create CostAnomaly", True, f"type={anomaly.anomaly_type}, deviation={anomaly.deviation_percent}%")
    except Exception as e:
        log_test("Create CostAnomaly", False, str(e))
    
    print("  → Cloud Cost Incident Handler: Structure verified")


# ============================================================================
# TEST 6: Module Exports
# ============================================================================

def test_module_exports():
    """Test that all modules export correctly"""
    test_header("6. MODULE EXPORTS")
    
    modules = [
        ("src.model", ["ProductionKnowledgeModel", "ServiceNode", "DependencyEdge"]),
        ("src.alerts", ["AlertNoiseSuppressor", "AlertContext", "TriageDecision"]),
        ("src.acceleration", ["MTTRAccelerator", "AnalysisResult", "RemediationPlan"]),
        ("src.timeline", ["IncidentTimelineGenerator", "TimelineEvent", "IncidentTimeline"]),
        ("src.cost", ["CloudCostIncidentHandler", "CostAnomaly", "CostIncident"])
    ]
    
    for module_name, expected_exports in modules:
        try:
            module = __import__(module_name, fromlist=expected_exports)
            missing = [e for e in expected_exports if not hasattr(module, e)]
            if missing:
                log_test(f"Module {module_name}", False, f"Missing exports: {missing}")
            else:
                log_test(f"Module {module_name}", True, f"All {len(expected_exports)} exports present")
        except Exception as e:
            log_test(f"Module {module_name}", False, str(e))


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all integrity tests"""
    print("\n" + "="*60)
    print("  INTELLIGENCE FEATURES INTEGRITY TEST")
    print("  AI DevOps Autopilot - New Features Validation")
    print("="*60)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_production_knowledge_model()
    test_alert_noise_suppression()
    test_mttr_acceleration()
    test_incident_timeline()
    test_cost_incident_handler()
    test_module_exports()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    total = test_results["passed"] + test_results["failed"]
    print(f"  Total Tests: {total}")
    print(f"  ✅ Passed:   {test_results['passed']}")
    print(f"  ❌ Failed:   {test_results['failed']}")
    print(f"  Success Rate: {test_results['passed']/total*100:.1f}%")
    print("="*60 + "\n")
    
    return test_results["failed"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
