"""
Test Runner for AI DevOps Learning System
Runs all tests: Pattern Matching, Learning Loop, Integration
"""

import subprocess
import sys
import os

def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print("   AI DevOps Autopilot - Complete Test Suite")
    print("="*70 + "\n")
    
    test_files = [
        ("Pattern Matching Tests", "tests/test_pattern_matching.py"),
        ("Learning Loop Tests", "tests/test_learning_loop.py"),
        ("Integration Tests", "tests/test_integration.py")
    ]
    
    results = []
    
    for name, path in test_files:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print("="*60)
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", path, "-v", "--tb=short"],
            capture_output=False,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        results.append((name, result.returncode))
    
    # Summary
    print("\n" + "="*70)
    print("   TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, code in results:
        status = "✓ PASSED" if code == 0 else "✗ FAILED"
        if code != 0:
            all_passed = False
        print(f"  {status} - {name}")
    
    print("="*70)
    
    if all_passed:
        print("\n  🎉 ALL TESTS PASSED!\n")
    else:
        print("\n  ⚠️  Some tests failed. Please review above.\n")
    
    return 0 if all_passed else 1


def run_quick_validation():
    """Quick validation without pytest - just imports and basics"""
    print("\n" + "="*70)
    print("   Quick Validation (Import Checks)")
    print("="*70 + "\n")
    
    checks = []
    
    # Check 1: DevOps Knowledge Base
    try:
        from src.training.devops_knowledge_base import DevOpsKnowledgeBase
        from unittest.mock import MagicMock
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.lrange.return_value = []
        
        kb = DevOpsKnowledgeBase(redis_mock)
        stats = kb.get_stats()
        pattern_count = stats.get('total_patterns', 0)
        
        if pattern_count >= 500:
            checks.append(("Knowledge Base", True, f"{pattern_count} patterns loaded"))
        else:
            checks.append(("Knowledge Base", False, f"Only {pattern_count} patterns"))
    except Exception as e:
        checks.append(("Knowledge Base", False, str(e)))
    
    # Check 2: Learning Engine
    try:
        from src.learning.learning_engine import LearningEngine
        le = LearningEngine(redis_mock)
        checks.append(("Learning Engine", True, "Initialized"))
    except Exception as e:
        checks.append(("Learning Engine", False, str(e)))
    
    # Check 3: Incident Analyzer
    try:
        from src.analysis.incident_analyzer import IncidentAnalyzer
        ia = IncidentAnalyzer(redis_mock, kb)
        checks.append(("Incident Analyzer", True, "Initialized"))
    except Exception as e:
        checks.append(("Incident Analyzer", False, str(e)))
    
    # Check 4: Autonomous Executor
    try:
        from src.autonomous_executor import AutonomousExecutor, ExecutionMode
        action_executor = MagicMock()
        ae = AutonomousExecutor(redis_mock, action_executor, kb, le)
        checks.append(("Autonomous Executor", True, "Initialized with learning"))
    except Exception as e:
        checks.append(("Autonomous Executor", False, str(e)))
    
    # Check 5: Pattern categories
    try:
        categories = stats.get('by_category', {})
        expected = ['kubernetes', 'database', 'cloud', 'application', 'cicd', 'network', 'security']
        missing = [c for c in expected if c not in categories]
        if not missing:
            checks.append(("Pattern Categories", True, f"All {len(expected)} categories present"))
        else:
            checks.append(("Pattern Categories", False, f"Missing: {missing}"))
    except Exception as e:
        checks.append(("Pattern Categories", False, str(e)))
    
    # Print results
    all_passed = True
    for name, passed, message in checks:
        status = "✓" if passed else "✗"
        if not passed:
            all_passed = False
        print(f"  {status} {name}: {message}")
    
    print("\n" + "="*70)
    
    if all_passed:
        print("\n  🎉 All validations passed! System ready.\n")
    else:
        print("\n  ⚠️  Some checks failed. Review the issues above.\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        sys.exit(run_quick_validation())
    else:
        sys.exit(run_all_tests())
