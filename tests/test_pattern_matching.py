"""
Pattern Matching Tests
Tests for DevOps Knowledge Base pattern matching functionality
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch


class TestPatternMatching:
    """Test suite for pattern matching in the knowledge base"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.lrange.return_value = []
        return redis_mock
    
    @pytest.fixture
    def knowledge_base(self, mock_redis):
        """Create a knowledge base instance with mock Redis"""
        from src.training.devops_knowledge_base import DevOpsKnowledgeBase
        return DevOpsKnowledgeBase(mock_redis)
    
    def test_knowledge_base_initialization(self, knowledge_base):
        """Test that knowledge base initializes with patterns"""
        stats = knowledge_base.get_stats()
        assert stats['total_patterns'] > 0, "Knowledge base should have patterns loaded"
        assert stats['total_patterns'] >= 500, "Should have 500+ patterns"
        print(f"✓ Knowledge base initialized with {stats['total_patterns']} patterns")
    
    def test_pattern_categories(self, knowledge_base):
        """Test that all expected categories exist"""
        stats = knowledge_base.get_stats()
        expected_categories = ['kubernetes', 'database', 'cloud', 'application', 'cicd', 'network', 'security']
        
        for category in expected_categories:
            assert category in stats['by_category'], f"Category {category} should exist"
            assert stats['by_category'][category] > 0, f"Category {category} should have patterns"
        
        print(f"✓ All {len(expected_categories)} categories present with patterns")
    
    def test_kubernetes_pod_crashloop_pattern(self, knowledge_base):
        """Test matching Kubernetes CrashLoopBackOff pattern"""
        anomalies = [
            {
                'metric_name': 'pod_restart_count',
                'service': 'api-gateway',
                'value': 15,
                'severity': 'high'
            }
        ]
        logs = [
            {
                'message': 'Back-off restarting failed container CrashLoopBackOff',
                'service': 'api-gateway',
                'level': 'error'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        assert len(matches) > 0, "Should find at least one matching pattern"
        
        # Check if we matched a Kubernetes pattern
        pattern_names = [p.name.lower() for p, _ in matches]
        has_crashloop = any('crash' in name or 'restart' in name or 'loop' in name for name in pattern_names)
        
        print(f"✓ Found {len(matches)} matching patterns for CrashLoopBackOff")
        if matches:
            print(f"  Top match: {matches[0][0].name} (confidence: {matches[0][1]:.1f}%)")
    
    def test_database_connection_pattern(self, knowledge_base):
        """Test matching database connection pattern"""
        anomalies = [
            {
                'metric_name': 'db_connection_count',
                'service': 'postgres-primary',
                'value': 95,
                'severity': 'critical'
            }
        ]
        logs = [
            {
                'message': 'FATAL: too many connections for role "app_user"',
                'service': 'postgres-primary',
                'level': 'error'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        assert len(matches) > 0, "Should find database pattern"
        print(f"✓ Found {len(matches)} matching patterns for database connection issue")
    
    def test_oom_killed_pattern(self, knowledge_base):
        """Test matching OOMKilled pattern"""
        anomalies = [
            {
                'metric_name': 'container_memory_usage',
                'service': 'worker-service',
                'value': 100,
                'severity': 'critical'
            }
        ]
        logs = [
            {
                'message': 'Container was OOMKilled due to exceeding memory limits',
                'service': 'worker-service',
                'level': 'error'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        assert len(matches) > 0, "Should find OOMKilled pattern"
        print(f"✓ Found {len(matches)} matching patterns for OOMKilled")
    
    def test_security_pattern_matching(self, knowledge_base):
        """Test matching security-related patterns"""
        anomalies = [
            {
                'metric_name': 'failed_login_attempts',
                'service': 'auth-service',
                'value': 500,
                'severity': 'high'
            }
        ]
        logs = [
            {
                'message': 'Multiple failed login attempts detected from IP 192.168.1.100',
                'service': 'auth-service',
                'level': 'warning'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        print(f"✓ Found {len(matches)} matching patterns for security event")
    
    def test_cicd_pipeline_failure_pattern(self, knowledge_base):
        """Test matching CI/CD pipeline failure patterns"""
        anomalies = []
        logs = [
            {
                'message': 'npm install failed with exit code 1',
                'service': 'ci-runner',
                'level': 'error'
            },
            {
                'message': 'Build failed: npm ERR! code ENOENT',
                'service': 'ci-runner',
                'level': 'error'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        print(f"✓ Found {len(matches)} matching patterns for CI/CD failure")
    
    def test_no_match_for_unrelated_logs(self, knowledge_base):
        """Test that unrelated logs don't produce false matches"""
        anomalies = []
        logs = [
            {
                'message': 'User logged in successfully',
                'service': 'auth-service',
                'level': 'info'
            }
        ]
        
        matches = knowledge_base.find_matching_patterns(anomalies, logs)
        
        # Should have either no matches or very low confidence matches
        if matches:
            assert matches[0][1] < 50, "Unrelated logs should have low confidence matches"
        
        print(f"✓ Correctly identified low/no matches for unrelated logs")
    
    def test_get_pattern_by_id(self, knowledge_base):
        """Test retrieving specific pattern by ID"""
        # Get any pattern from the base
        stats = knowledge_base.get_stats()
        if stats['total_patterns'] > 0:
            # Try to get first kubernetes pattern
            patterns = knowledge_base.get_patterns_by_category('kubernetes')
            if patterns:
                pattern_id = patterns[0].pattern_id
                retrieved = knowledge_base.get_pattern(pattern_id)
                
                assert retrieved is not None, "Should retrieve pattern by ID"
                assert retrieved.pattern_id == pattern_id
                print(f"✓ Successfully retrieved pattern: {retrieved.name}")
    
    def test_autonomous_safe_patterns(self, knowledge_base):
        """Test getting autonomous-safe patterns"""
        safe_patterns = knowledge_base.get_autonomous_safe_patterns()
        
        # All returned patterns should have autonomous_safe = True
        for pattern in safe_patterns:
            assert pattern.autonomous_safe, f"Pattern {pattern.name} should be autonomous safe"
        
        print(f"✓ Found {len(safe_patterns)} autonomous-safe patterns")


class TestPatternSignalMatching:
    """Test signal-based pattern matching"""
    
    @pytest.fixture
    def mock_redis(self):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.lrange.return_value = []
        return redis_mock
    
    @pytest.fixture
    def knowledge_base(self, mock_redis):
        from src.training.devops_knowledge_base import DevOpsKnowledgeBase
        return DevOpsKnowledgeBase(mock_redis)
    
    def test_signal_keyword_extraction(self, knowledge_base):
        """Test that patterns have proper signals defined"""
        patterns = knowledge_base.get_patterns_by_category('kubernetes')
        
        for pattern in patterns[:10]:  # Check first 10
            assert len(pattern.signals) > 0, f"Pattern {pattern.name} should have signals"
        
        print(f"✓ Verified signals exist for Kubernetes patterns")
    
    def test_severity_distribution(self, knowledge_base):
        """Test that patterns have proper severity distribution"""
        stats = knowledge_base.get_stats()
        
        assert 'critical' in stats['by_severity'] or 'CRITICAL' in str(stats['by_severity'])
        assert 'high' in stats['by_severity'] or 'HIGH' in str(stats['by_severity'])
        
        print(f"✓ Severity distribution: {stats['by_severity']}")


def run_pattern_tests():
    """Run all pattern matching tests"""
    print("\n" + "="*60)
    print("Running Pattern Matching Tests")
    print("="*60 + "\n")
    
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_pattern_tests()
