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
            CriticalityTier
        )
        log_test("Import ProductionKnowledgeModel", True)
    except ImportError as e:
        log_test("Import ProductionKnowledgeModel", False, str(e))
        return
    
    # Test ServiceNode dataclass
    try:
        node = ServiceNode(
            service_id="test-service",
            name="Test Service",
            service_type="api",
            criticality_tier=1,
            owner_team="platform"
        )
        log_test("Create ServiceNode", True, f"service_id={node.service_id}")
    except Exception as e:
        log_test("Create ServiceNode", False, str(e))
    
    # Test DependencyEdge dataclass
    try:
        edge = DependencyEdge(
            source_id="svc-a",
            target_id="svc-b",
            dependency_type="http",
            is_critical=True
        )
        log_test("Create DependencyEdge", True, f"{edge.source_id} -> {edge.target_id}")
    except Exception as e:
        log_test("Create DependencyEdge", False, str(e))
    
    # Test CriticalityTier enum
    try:
        tier1 = CriticalityTier.TIER_1
        tier2 = CriticalityTier.TIER_2
        log_test("CriticalityTier enum", True, f"TIER_1={tier1.value}, TIER_2={tier2.value}")
    except Exception as e:
        log_test("CriticalityTier enum", False, str(e))
    
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
            AnalysisStrategy,
            RemediationType
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
    
    # Test RemediationType enum
    try:
        types = [t.value for t in RemediationType]
        log_test("RemediationType enum", True, f"{len(types)} types: {types}")
    except Exception as e:
        log_test("RemediationType enum", False, str(e))
    
    # Test AnalysisResult dataclass
    try:
        result = AnalysisResult(
            strategy=AnalysisStrategy.LOG_ANALYSIS,
            root_cause_hypothesis="Memory leak detected",
            confidence=0.85,
            evidence=["OOM errors in logs"],
            suggested_action="restart",
            execution_time_ms=45
        )
        log_test("Create AnalysisResult", True, f"strategy={result.strategy.value}, confidence={result.confidence}")
    except Exception as e:
        log_test("Create AnalysisResult", False, str(e))
    
    # Test RemediationPlan dataclass
    try:
        plan = RemediationPlan(
            plan_id="plan-123",
            remediation_type=RemediationType.ROLLBACK,
            target_service="payment-service",
            description="Rollback to previous version",
            estimated_time_seconds=60,
            risk_level="low",
            requires_approval=False
        )
        log_test("Create RemediationPlan", True, f"type={plan.remediation_type.value}")
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
            EventType,
            EventSource
        )
        log_test("Import IncidentTimelineGenerator", True)
    except ImportError as e:
        log_test("Import IncidentTimelineGenerator", False, str(e))
        return
    
    # Test EventType enum
    try:
        types = [t.value for t in EventType]
        log_test("EventType enum", True, f"{len(types)} types: {types[:5]}...")
    except Exception as e:
        log_test("EventType enum", False, str(e))
    
    # Test EventSource enum
    try:
        sources = [s.value for s in EventSource]
        log_test("EventSource enum", True, f"{len(sources)} sources: {sources}")
    except Exception as e:
        log_test("EventSource enum", False, str(e))
    
    # Test TimelineEvent dataclass
    try:
        event = TimelineEvent(
            event_id="evt-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.DEPLOYMENT,
            source=EventSource.CICD,
            title="Deployment Started",
            description="Deploying v2.3.1",
            severity="info",
            service="payment-service"
        )
        log_test("Create TimelineEvent", True, f"type={event.event_type.value}")
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
