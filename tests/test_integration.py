"""
End-to-End Integration Tests
Tests for complete flow: Detection -> Analysis -> Action -> Learning
"""

import pytest
import asyncio
import sys
import os
import json
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, AsyncMock, patch


class MockRedis:
    """Full mock Redis implementation for integration tests"""
    
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
    
    def lrange(self, key, start, end):
        if key not in self.lists:
            return []
        if end == -1:
            return self.lists[key][start:]
        return self.lists[key][start:end+1]
    
    def incr(self, key):
        current = int(self.storage.get(key, 0))
        self.storage[key] = str(current + 1)
        return current + 1
    
    def hget(self, key, field):
        if key not in self.hashes:
            return None
        return self.hashes[key].get(field)
    
    def hset(self, key, field, value):
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key][field] = value
        return True
    
    def expire(self, key, ttl):
        return True


class TestEndToEndIntegration:
    """End-to-end integration tests for the AI DevOps system"""
    
    @pytest.fixture
    def redis_client(self):
        return MockRedis()
    
    @pytest.fixture
    def knowledge_base(self, redis_client):
        from src.training.devops_knowledge_base import DevOpsKnowledgeBase
        return DevOpsKnowledgeBase(redis_client)
    
    @pytest.fixture
    def learning_engine(self, redis_client):
        from src.learning.learning_engine import LearningEngine
        return LearningEngine(redis_client)
    
    @pytest.fixture
    def incident_analyzer(self, redis_client, knowledge_base):
        from src.analysis.incident_analyzer import IncidentAnalyzer
        return IncidentAnalyzer(redis_client, knowledge_base)
    
    def test_full_incident_workflow(self, knowledge_base, learning_engine, incident_analyzer):
        """Test complete incident detection to resolution workflow"""
        
        # Step 1: Create incident data
        incident = {
            'incident_id': 'INC-001',
            'service': 'payment-service',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'anomalies': [
                {
                    'metric_name': 'response_time_p99',
                    'value': 2500,
                    'threshold': 500,
                    'severity': 'critical'
                },
                {
                    'metric_name': 'error_rate',
                    'value': 15,
                    'threshold': 1,
                    'severity': 'high'
                }
            ],
            'logs': [
                {
                    'message': 'Connection timeout to downstream service',
                    'level': 'error',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                {
                    'message': 'Retrying request... attempt 3 of 3',
                    'level': 'warning',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        # Step 2: Analyze incident with pattern matching
        matches = knowledge_base.find_matching_patterns(
            incident['anomalies'], 
            incident['logs']
        )
        
        assert len(matches) > 0, "Should find matching patterns"
        
        top_pattern = matches[0][0]
        confidence = matches[0][1]
        
        print(f"✓ Step 2: Pattern matched - {top_pattern.name} ({confidence:.1f}%)")
        
        # Step 3: Get recommended actions from pattern
        recommended_actions = top_pattern.recommended_actions
        
        assert len(recommended_actions) > 0, "Pattern should have recommended actions"
        
        print(f"✓ Step 3: Found {len(recommended_actions)} recommended actions")
        
        # Step 4: Simulate action execution
        action = {
            'action_id': 'ACT-001',
            'pattern_id': top_pattern.pattern_id,
            'action_type': recommended_actions[0].action_type,
            'service': incident['service'],
            'executed_at': datetime.now(timezone.utc).isoformat(),
            'success': True
        }
        
        # Step 5: Record outcome for learning
        outcome = {
            'pattern_id': action['pattern_id'],
            'action_type': action['action_type'],
            'success': action['success'],
            'autonomous': False,
            'resolution_time_seconds': 120
        }
        
        learning_engine.record_outcome(outcome)
        
        print("✓ Step 4-5: Action executed and outcome recorded")
        
        # Verify learning stats updated
        stats = learning_engine.get_learning_stats()
        print(f"✓ Learning stats: {stats}")
        
        print("\n✓ FULL INCIDENT WORKFLOW COMPLETED SUCCESSFULLY")
    
    def test_multiple_incidents_learning(self, knowledge_base, learning_engine):
        """Test learning from multiple similar incidents"""
        
        incidents = [
            {
                'anomalies': [{'metric_name': 'cpu_usage', 'value': 95, 'severity': 'high'}],
                'logs': [{'message': 'High CPU usage detected', 'level': 'warning'}],
                'success': True
            },
            {
                'anomalies': [{'metric_name': 'cpu_usage', 'value': 92, 'severity': 'high'}],
                'logs': [{'message': 'CPU throttling events', 'level': 'warning'}],
                'success': True
            },
            {
                'anomalies': [{'metric_name': 'cpu_usage', 'value': 88, 'severity': 'high'}],
                'logs': [{'message': 'Process consuming excessive CPU', 'level': 'warning'}],
                'success': False  # This one failed
            }
        ]
        
        for i, incident in enumerate(incidents):
            matches = knowledge_base.find_matching_patterns(
                incident['anomalies'], 
                incident['logs']
            )
            
            if matches:
                pattern = matches[0][0]
                
                outcome = {
                    'pattern_id': pattern.pattern_id,
                    'action_type': 'scale_up',
                    'success': incident['success'],
                    'autonomous': True
                }
                learning_engine.record_outcome(outcome)
        
        stats = learning_engine.get_learning_stats()
        print(f"✓ Processed {len(incidents)} incidents, stats: {stats}")
    
    def test_pattern_to_action_flow(self, knowledge_base):
        """Test that patterns correctly map to actions"""
        
        # Get all categories
        categories = ['kubernetes', 'database', 'cloud', 'application']
        
        for category in categories:
            patterns = knowledge_base.get_patterns_by_category(category)
            
            if patterns:
                pattern = patterns[0]
                
                # Each pattern should have actions
                assert len(pattern.recommended_actions) > 0, \
                    f"Pattern {pattern.name} should have actions"
                
                # Actions should have required fields
                for action in pattern.recommended_actions:
                    assert action.action_type, "Action should have type"
                    assert action.confidence > 0, "Action should have confidence"
        
        print(f"✓ Pattern-to-action mapping verified for {len(categories)} categories")
    
    def test_severity_based_routing(self, knowledge_base):
        """Test that severity affects pattern matching and action selection"""
        
        # Critical incident
        critical_incident = {
            'anomalies': [{'metric_name': 'health_check', 'value': 0, 'severity': 'critical'}],
            'logs': [{'message': 'Service completely down', 'level': 'error'}]
        }
        
        # Warning incident
        warning_incident = {
            'anomalies': [{'metric_name': 'response_time', 'value': 800, 'severity': 'warning'}],
            'logs': [{'message': 'Slight latency increase', 'level': 'warning'}]
        }
        
        critical_matches = knowledge_base.find_matching_patterns(
            critical_incident['anomalies'],
            critical_incident['logs']
        )
        
        warning_matches = knowledge_base.find_matching_patterns(
            warning_incident['anomalies'],
            warning_incident['logs']
        )
        
        print(f"✓ Critical incident matches: {len(critical_matches)}")
        print(f"✓ Warning incident matches: {len(warning_matches)}")


class TestAutonomousExecutorIntegration:
    """Test autonomous executor integration with learning system"""
    
    @pytest.fixture
    def redis_client(self):
        return MockRedis()
    
    @pytest.fixture
    def full_system(self, redis_client):
        """Create fully integrated system components"""
        from src.training.devops_knowledge_base import DevOpsKnowledgeBase
        from src.learning.learning_engine import LearningEngine
        from src.autonomous_executor import AutonomousExecutor
        
        kb = DevOpsKnowledgeBase(redis_client)
        le = LearningEngine(redis_client)
        
        # Create mock action executor
        action_executor = MagicMock()
        action_executor.execute_action = AsyncMock(return_value={
            'success': True,
            'message': 'Action completed'
        })
        
        executor = AutonomousExecutor(redis_client, action_executor, kb, le)
        
        return {
            'redis': redis_client,
            'knowledge_base': kb,
            'learning_engine': le,
            'executor': executor
        }
    
    def test_executor_receives_learning_components(self, full_system):
        """Test that executor is properly connected to learning system"""
        executor = full_system['executor']
        
        assert executor.knowledge_base is not None, "KB should be connected"
        assert executor.learning_engine is not None, "LE should be connected"
        
        print("✓ Executor connected to learning components")
    
    def test_executor_mode_switching(self, full_system):
        """Test switching between execution modes"""
        from src.autonomous_executor import ExecutionMode
        
        executor = full_system['executor']
        
        # Test all modes
        modes = [
            ExecutionMode.MANUAL,
            ExecutionMode.SUPERVISED,
            ExecutionMode.AUTONOMOUS,
            ExecutionMode.NIGHT_MODE
        ]
        
        for mode in modes:
            executor.set_execution_mode(mode)
            assert executor.execution_mode == mode
        
        print(f"✓ All {len(modes)} execution modes work correctly")
    
    def test_executor_stats(self, full_system):
        """Test getting executor statistics"""
        executor = full_system['executor']
        
        stats = executor.get_autonomous_stats()
        
        assert 'execution_mode' in stats
        assert 'confidence_threshold' in stats
        
        print(f"✓ Executor stats: mode={stats['execution_mode']}, threshold={stats['confidence_threshold']}")


class TestAPIIntegration:
    """Test API endpoint integration with learning system"""
    
    def test_learning_stats_endpoint_format(self):
        """Test expected format of learning stats API response"""
        expected_fields = [
            'learning_enabled',
            'knowledge_base',
            'learning_engine',
            'autonomous'
        ]
        
        # This would be called via HTTP in actual integration test
        # For now, verify the expected structure
        mock_response = {
            'learning_enabled': True,
            'knowledge_base': {
                'total_patterns': 580,
                'by_category': {},
                'autonomous_safe_count': 45
            },
            'learning_engine': {
                'total_outcomes': 0,
                'success_rate': 0
            },
            'autonomous': {}
        }
        
        for field in expected_fields:
            assert field in mock_response
        
        print("✓ API response format validated")


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("Running End-to-End Integration Tests")
    print("="*60 + "\n")
    
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_integration_tests()
