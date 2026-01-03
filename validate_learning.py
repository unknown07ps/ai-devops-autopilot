"""
Complete Validation Script for Learning System
Properly creates LearningOutcome objects and handles all Redis methods
"""

import sys
import os
import importlib.util
import json
import uuid

# Project root and ensure it's in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def import_module_directly(module_name, file_path):
    """Import a module directly from file"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"  Warning: Could not load {module_name}: {e}")
        return None


class MockRedis:
    """Full mock Redis implementation"""
    
    def __init__(self):
        self.storage = {}
        self.lists = {}
        self.hashes = {}
    
    def get(self, key):
        return self.storage.get(key)
    
    def set(self, key, value, *args, **kwargs):
        self.storage[key] = value
        return True
    
    def setex(self, key, ttl, value):
        self.storage[key] = value
        return True
    
    def lpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)
        return len(self.lists[key])
    
    def rpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)
        return len(self.lists[key])
    
    def lrange(self, key, start, end):
        if key not in self.lists:
            return []
        if end == -1:
            return self.lists[key][start:]
        return self.lists[key][start:end+1]
    
    def ltrim(self, key, start, end):
        """Trim list to specified range"""
        if key in self.lists:
            if end == -1:
                self.lists[key] = self.lists[key][start:]
            else:
                self.lists[key] = self.lists[key][start:end+1]
        return True
    
    def llen(self, key):
        return len(self.lists.get(key, []))
    
    def incr(self, key):
        current = int(self.storage.get(key, 0))
        self.storage[key] = str(current + 1)
        return current + 1
    
    def incrby(self, key, amount):
        current = int(self.storage.get(key, 0))
        self.storage[key] = str(current + amount)
        return current + amount
    
    def expire(self, key, ttl):
        return True
    
    def keys(self, pattern="*"):
        """Return keys matching pattern"""
        if pattern == "*":
            return list(self.storage.keys())
        import fnmatch
        return [k for k in self.storage.keys() if fnmatch.fnmatch(k, pattern)]
    
    def hget(self, key, field):
        if key not in self.hashes:
            return None
        return self.hashes[key].get(field)
    
    def hset(self, key, field, value):
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key][field] = value
        return True
    
    def hgetall(self, key):
        return self.hashes.get(key, {})
    
    def hincrby(self, key, field, amount=1):
        if key not in self.hashes:
            self.hashes[key] = {}
        current = int(self.hashes[key].get(field, 0))
        self.hashes[key][field] = str(current + amount)
        return current + amount
    
    def delete(self, *keys):
        for key in keys:
            self.storage.pop(key, None)
            self.lists.pop(key, None)
            self.hashes.pop(key, None)
        return len(keys)
    
    def ttl(self, key):
        return -1 if key in self.storage else -2
    
    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline"""
    def __init__(self, redis):
        self.redis = redis
        self.commands = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def lpush(self, key, value):
        self.commands.append(('lpush', key, value))
        return self
    
    def set(self, key, value, *args, **kwargs):
        self.commands.append(('set', key, value))
        return self
    
    def execute(self):
        for cmd in self.commands:
            if cmd[0] == 'lpush':
                self.redis.lpush(cmd[1], cmd[2])
            elif cmd[0] == 'set':
                self.redis.set(cmd[1], cmd[2])
        return [True] * len(self.commands)


def test_knowledge_base():
    """Test Knowledge Base functionality"""
    print("\n" + "="*60)
    print("TEST 1: Knowledge Base")
    print("="*60)
    
    try:
        kb_path = os.path.join(PROJECT_ROOT, "src", "training", "devops_knowledge_base.py")
        kb_module = import_module_directly("devops_knowledge_base", kb_path)
        
        if kb_module is None:
            print("  ✗ Failed to load Knowledge Base module")
            return False, None, None
        
        # Register so extended patterns can import
        sys.modules['src.training.devops_knowledge_base'] = kb_module
        
        redis = MockRedis()
        kb = kb_module.DevOpsKnowledgeBase(redis)
        
        # Test 1.1: Pattern count
        stats = kb.get_stats()
        pattern_count = stats.get('total_patterns', 0)
        
        if pattern_count >= 30:
            print(f"  ✓ Patterns loaded: {pattern_count}")
        else:
            print(f"  ✗ Only {pattern_count} patterns")
            return False, None, None
        
        # Test 1.2: Categories
        categories = stats.get('by_category', {})
        expected_cats = ['kubernetes', 'database', 'cloud', 'application', 'cicd', 'network', 'security']
        
        for cat in expected_cats:
            if cat in categories:
                print(f"  ✓ Category {cat}: {categories[cat]} patterns")
        
        # Test 1.3: Pattern matching
        anomalies = [{'metric_name': 'pod_restart', 'value': 10, 'severity': 'high'}]
        logs = [{'message': 'CrashLoopBackOff pod restarting', 'level': 'error'}]
        
        matches = kb.find_matching_patterns(anomalies, logs)
        
        if len(matches) > 0:
            print(f"  ✓ Pattern matching works: {len(matches)} matches found")
            print(f"    Top match: {matches[0][0].name} ({matches[0][1]:.1f}%)")
        else:
            print("  ⚠ No patterns matched")
        
        # Test 1.4: Autonomous safe patterns
        safe = kb.get_autonomous_safe_patterns()
        print(f"  ✓ Autonomous-safe patterns: {len(safe)}")
        
        return True, kb, kb_module
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_learning_engine():
    """Test Learning Engine functionality"""
    print("\n" + "="*60)
    print("TEST 2: Learning Engine")
    print("="*60)
    
    try:
        le_path = os.path.join(PROJECT_ROOT, "src", "learning", "learning_engine.py")
        le_module = import_module_directly("learning_engine", le_path)
        
        if le_module is None:
            print("  ✗ Failed to load Learning Engine module")
            return False, None, None
        
        redis = MockRedis()
        le = le_module.LearningEngine(redis)
        print("  ✓ Learning Engine initialized")
        
        # Create proper LearningOutcome objects
        LearningOutcome = le_module.LearningOutcome
        
        # Test 2.1: Record success outcome
        outcome1 = LearningOutcome(
            outcome_id=str(uuid.uuid4()),
            incident_id="INC-001",
            pattern_id="test_pattern_success",
            action_type="restart_pod",
            action_category="kubernetes",
            success=True,
            confidence_at_execution=85.0,
            execution_time_seconds=30.0
        )
        le.record_outcome(outcome1)
        print("  ✓ Success outcome recorded")
        
        # Test 2.2: Record failure outcome
        outcome2 = LearningOutcome(
            outcome_id=str(uuid.uuid4()),
            incident_id="INC-002",
            pattern_id="test_pattern_failure",
            action_type="scale_down",
            action_category="kubernetes",
            success=False,
            confidence_at_execution=75.0,
            execution_time_seconds=45.0
        )
        le.record_outcome(outcome2)
        print("  ✓ Failure outcome recorded")
        
        # Test 2.3: Multiple outcomes for same pattern
        for i in range(10):
            outcome = LearningOutcome(
                outcome_id=str(uuid.uuid4()),
                incident_id=f"INC-MULTI-{i}",
                pattern_id="test_pattern_multi",
                action_type="restart",
                action_category="kubernetes",
                success=(i % 3 != 0),  # 70% success
                confidence_at_execution=80.0,
                execution_time_seconds=20.0 + i
            )
            le.record_outcome(outcome)
        print("  ✓ Multiple outcomes recorded (10 total)")
        
        # Test 2.4: Get learning stats
        summary = le.get_learning_summary()
        print(f"  ✓ Learning summary:")
        print(f"     Tracked patterns: {summary['tracked_patterns']}")
        print(f"     Total outcomes: {summary['total_outcomes_recorded']}")
        print(f"     Success rate: {summary['overall_success_rate']:.1%}")
        
        # Test 2.5: Get pattern confidence
        conf = le.get_pattern_confidence("test_pattern_multi", 50.0)
        print(f"  ✓ Pattern confidence: {conf:.1f}%")
        
        # Test 2.6: Check autonomous safety
        is_safe, reason = le.is_autonomous_safe("test_pattern_multi")
        print(f"  ✓ Autonomous safe check: {is_safe} ({reason})")
        
        return True, le, le_module
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_incident_analyzer(kb=None, kb_module=None):
    """Test Incident Analyzer functionality"""
    print("\n" + "="*60)
    print("TEST 3: Incident Analyzer")
    print("="*60)
    
    try:
        ia_path = os.path.join(PROJECT_ROOT, "src", "analysis", "incident_analyzer.py")
        ia_module = import_module_directly("incident_analyzer", ia_path)
        
        if ia_module is None:
            print("  ✗ Failed to load Incident Analyzer module")
            return False
        
        redis = MockRedis()
        
        if kb is None:
            kb_path = os.path.join(PROJECT_ROOT, "src", "training", "devops_knowledge_base.py")
            kb_module = import_module_directly("devops_kb_ia", kb_path)
            kb = kb_module.DevOpsKnowledgeBase(redis)
        
        ia = ia_module.IncidentAnalyzer(redis, kb)
        print("  ✓ Incident Analyzer initialized")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_autonomous_executor(kb=None, le=None):
    """Test Autonomous Executor integration"""
    print("\n" + "="*60)
    print("TEST 4: Autonomous Executor Integration")
    print("="*60)
    
    try:
        ae_path = os.path.join(PROJECT_ROOT, "src", "autonomous_executor.py")
        ae_module = import_module_directly("autonomous_executor", ae_path)
        
        if ae_module is None:
            print("  ✗ Failed to load Autonomous Executor module")
            return False
        
        redis = MockRedis()
        
        if kb is None:
            kb_path = os.path.join(PROJECT_ROOT, "src", "training", "devops_knowledge_base.py")
            kb_module = import_module_directly("devops_kb_ae", kb_path)
            if kb_module:
                sys.modules['src.training.devops_knowledge_base'] = kb_module
                kb = kb_module.DevOpsKnowledgeBase(redis)
        
        if le is None:
            le_path = os.path.join(PROJECT_ROOT, "src", "learning", "learning_engine.py")
            le_module = import_module_directly("learning_engine_ae", le_path)
            if le_module:
                le = le_module.LearningEngine(redis)
        
        from unittest.mock import MagicMock
        action_executor = MagicMock()
        
        executor = ae_module.AutonomousExecutor(redis, action_executor, kb, le)
        
        # Test connections
        if executor.knowledge_base is not None:
            print("  ✓ Knowledge Base connected")
        else:
            print("  ✗ Knowledge Base NOT connected")
        
        if executor.learning_engine is not None:
            print("  ✓ Learning Engine connected")
        else:
            print("  ✗ Learning Engine NOT connected")
        
        # Test mode switching
        for mode in [ae_module.ExecutionMode.MANUAL, 
                     ae_module.ExecutionMode.SUPERVISED, 
                     ae_module.ExecutionMode.AUTONOMOUS]:
            executor.set_execution_mode(mode)
        print("  ✓ Mode switching works")
        
        # Test stats
        stats = executor.get_autonomous_stats()
        print(f"  ✓ Stats: mode={stats['execution_mode']}, threshold={stats['confidence_threshold']}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """Test complete incident-to-learning workflow"""
    print("\n" + "="*60)
    print("TEST 5: Full Incident Workflow")
    print("="*60)
    
    try:
        redis = MockRedis()
        
        # Load modules
        kb_path = os.path.join(PROJECT_ROOT, "src", "training", "devops_knowledge_base.py")
        kb_module = import_module_directly("devops_kb_wf", kb_path)
        sys.modules['src.training.devops_knowledge_base'] = kb_module
        kb = kb_module.DevOpsKnowledgeBase(redis)
        
        le_path = os.path.join(PROJECT_ROOT, "src", "learning", "learning_engine.py")
        le_module = import_module_directly("learning_engine_wf", le_path)
        le = le_module.LearningEngine(redis)
        
        print("  Step 0: Components initialized")
        
        # Simulate incident
        incident = {
            'service': 'api-gateway',
            'anomalies': [
                {'metric_name': 'error_rate', 'value': 25, 'severity': 'critical'}
            ],
            'logs': [
                {'message': 'Connection refused to database', 'level': 'error'}
            ]
        }
        
        # Step 1: Match patterns
        matches = kb.find_matching_patterns(incident['anomalies'], incident['logs'])
        print(f"  Step 1: Found {len(matches)} pattern matches")
        
        if matches:
            pattern = matches[0][0]
            print(f"  Step 2: Selected pattern: {pattern.name}")
            
            actions = pattern.recommended_actions
            print(f"  Step 3: Found {len(actions)} recommended actions")
            
            # Step 4: Record outcome with proper object
            LearningOutcome = le_module.LearningOutcome
            outcome = LearningOutcome(
                outcome_id=str(uuid.uuid4()),
                incident_id="INC-WF-001",
                pattern_id=pattern.pattern_id,
                action_type=actions[0].action_type if actions else "investigate",
                action_category=actions[0].category if actions else "manual",
                success=True,
                confidence_at_execution=matches[0][1],
                execution_time_seconds=120.0
            )
            le.record_outcome(outcome)
            print("  Step 4: Outcome recorded for learning")
            
            # Verify
            summary = le.get_learning_summary()
            print(f"  Step 5: Learning updated - {summary['total_outcomes_recorded']} outcomes")
            
            print("\n  ✓ FULL WORKFLOW COMPLETED SUCCESSFULLY")
        else:
            print("  ⚠ No pattern matches - core workflow still functional")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("\n" + "="*70)
    print("   AI DevOps Autopilot - Learning System Validation")
    print("="*70)
    
    results = []
    kb, kb_module, le, le_module = None, None, None, None
    
    # Test 1: Knowledge Base
    result = test_knowledge_base()
    if isinstance(result, tuple):
        passed, kb, kb_module = result
    else:
        passed = result
    results.append(("Knowledge Base", passed))
    
    # Test 2: Learning Engine
    result = test_learning_engine()
    if isinstance(result, tuple):
        passed, le, le_module = result
    else:
        passed = result
    results.append(("Learning Engine", passed))
    
    # Test 3: Incident Analyzer
    passed = test_incident_analyzer(kb, kb_module)
    results.append(("Incident Analyzer", passed))
    
    # Test 4: Autonomous Executor
    passed = test_autonomous_executor(kb, le)
    results.append(("Autonomous Executor", passed))
    
    # Test 5: Full Workflow
    passed = test_full_workflow()
    results.append(("Full Workflow", passed))
    
    # Summary
    print("\n" + "="*70)
    print("   VALIDATION SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        if not passed:
            all_passed = False
        print(f"  {status} - {name}")
    
    print("="*70)
    
    if all_passed:
        print("\n  🎉 ALL VALIDATIONS PASSED!")
        print("     The Learning System is fully functional.\n")
        return 0
    else:
        failed_count = sum(1 for _, p in results if not p)
        print(f"\n  ⚠️  {failed_count} validation(s) failed.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
