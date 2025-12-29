"""
Phase 3: Autonomous Mode - Intelligent Automation
Rule-based + AI hybrid execution with confidence scoring and safety guardrails
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, time as dt_time
from enum import Enum
import redis

class ExecutionMode(Enum):
    """Execution modes for autonomous system"""
    MANUAL = "manual"  # All actions require approval
    SUPERVISED = "supervised"  # Low-risk auto-approved, others manual
    AUTONOMOUS = "autonomous"  # High-confidence actions auto-executed
    NIGHT_MODE = "night_mode"  # Autonomous during off-hours only

class ConfidenceLevel(Enum):
    """Confidence levels for action execution"""
    VERY_HIGH = 90  # Execute immediately
    HIGH = 75  # Execute with monitoring
    MEDIUM = 60  # Require approval
    LOW = 40  # Suggest but don't execute
    VERY_LOW = 0  # Don't recommend

class SafetyRail(Enum):
    """Safety guardrails to prevent dangerous actions"""
    MAX_CONCURRENT_ACTIONS = "max_concurrent_actions"
    ACTION_COOLDOWN = "action_cooldown"
    ROLLBACK_LIMIT = "rollback_limit"
    SCALE_LIMIT = "scale_limit"
    SERVICE_HEALTH_CHECK = "service_health_check"
    BLAST_RADIUS_CHECK = "blast_radius_check"

class AutonomousExecutor:
    """
    Intelligent autonomous executor with hybrid rule + AI decision making
    """
    
    def __init__(self, redis_client, action_executor):
        self.redis = redis_client
        self.action_executor = action_executor
        
        # Configuration
        self.execution_mode = ExecutionMode.SUPERVISED
        self.confidence_threshold = 75  # Minimum confidence for autonomous execution
        self.night_hours = (22, 6)  # 10 PM - 6 AM
        
        # Safety limits
        self.max_concurrent_actions = 3
        self.action_cooldown_seconds = 300  # 5 minutes
        self.max_rollbacks_per_hour = 2
        self.max_scale_factor = 3  # Max 3x current replicas
        
        # State tracking
        self.active_actions = {}
        self.action_history = []
        self.last_action_time = {}
        
        # Learning weights (updated over time)
        self.rule_weight = 0.4
        self.ai_weight = 0.4
        self.historical_weight = 0.2
    
    async def evaluate_action(
        self,
        action: Dict,
        incident: Dict,
        analysis: Dict,
        similar_incidents: List[Dict] = None
    ) -> Tuple[bool, float, str]:
        """
        Evaluate if action should be executed autonomously
        Returns: (should_execute, confidence, reasoning)
        """
        
        # Check if in autonomous mode
        if not self._is_autonomous_mode_active():
            return False, 0, "Autonomous mode not active"
        
        # Safety checks first (hard stops)
        safety_passed, safety_reason = await self._check_safety_rails(action)
        if not safety_passed:
            return False, 0, f"Safety check failed: {safety_reason}"
        
        # Calculate confidence score from multiple sources
        rule_confidence = self._calculate_rule_based_confidence(action, incident)
        ai_confidence = self._extract_ai_confidence(analysis, action)
        historical_confidence = self._calculate_historical_confidence(
            action, similar_incidents
        )
        
        # Weighted combination
        overall_confidence = (
            rule_confidence * self.rule_weight +
            ai_confidence * self.ai_weight +
            historical_confidence * self.historical_weight
        )
        
        # Decision reasoning
        reasoning = self._build_reasoning(
            rule_confidence, ai_confidence, historical_confidence, overall_confidence
        )
        
        # Determine if should execute
        should_execute = overall_confidence >= self.confidence_threshold
        
        print(f"[AUTONOMOUS] Action evaluation: {action['action_type']}")
        print(f"  Rule confidence: {rule_confidence:.1f}%")
        print(f"  AI confidence: {ai_confidence:.1f}%")
        print(f"  Historical confidence: {historical_confidence:.1f}%")
        print(f"  Overall confidence: {overall_confidence:.1f}%")
        print(f"  Decision: {'EXECUTE' if should_execute else 'REQUIRE APPROVAL'}")
        
        return should_execute, overall_confidence, reasoning
    
    def _is_autonomous_mode_active(self) -> bool:
        """Check if autonomous mode is currently active"""
        
        if self.execution_mode == ExecutionMode.MANUAL:
            return False
        
        if self.execution_mode == ExecutionMode.SUPERVISED:
            return True  # Handles low-risk only
        
        if self.execution_mode == ExecutionMode.AUTONOMOUS:
            return True
        
        if self.execution_mode == ExecutionMode.NIGHT_MODE:
            return self._is_night_hours()
        
        return False
    
    def _is_night_hours(self) -> bool:
        """Check if current time is within night hours"""
        current_hour = datetime.now(timezone.utc).hour
        start_hour, end_hour = self.night_hours
        
        if start_hour > end_hour:  # Crosses midnight
            return current_hour >= start_hour or current_hour < end_hour
        else:
            return start_hour <= current_hour < end_hour
    
    async def _check_safety_rails(self, action: Dict) -> Tuple[bool, str]:
        """
        Check all safety guardrails
        Returns: (passed, reason_if_failed)
        """
        
        # Check 1: Concurrent actions limit
        if len(self.active_actions) >= self.max_concurrent_actions:
            return False, f"Max concurrent actions ({self.max_concurrent_actions}) reached"
        
        # Check 2: Action cooldown
        service = action['service']
        action_type = action['action_type']
        cooldown_key = f"{service}:{action_type}"
        
        if cooldown_key in self.last_action_time:
            time_since_last = (
                datetime.now(timezone.utc).timestamp() - 
                self.last_action_time[cooldown_key]
            )
            if time_since_last < self.action_cooldown_seconds:
                return False, f"Cooldown active ({int(self.action_cooldown_seconds - time_since_last)}s remaining)"
        
        # Check 3: Rollback limits
        if action_type == 'rollback':
            recent_rollbacks = self._count_recent_actions('rollback', hours=1)
            if recent_rollbacks >= self.max_rollbacks_per_hour:
                return False, f"Rollback limit reached ({self.max_rollbacks_per_hour}/hour)"
        
        # Check 4: Scale limits
        if action_type in ['scale_up', 'scale_down']:
            current = action['params'].get('current_replicas', 3)
            target = action['params'].get('target_replicas', 6)
            
            if target > current * self.max_scale_factor:
                return False, f"Scale factor too high (max {self.max_scale_factor}x)"
            
            if target < 1:
                return False, "Cannot scale below 1 replica"
        
        # Check 5: Service health
        service_health = await self._check_service_health(service)
        if service_health == 'critical':
            return False, "Service in critical state - manual intervention required"
        
        # Check 6: Blast radius (prevent cascading failures)
        blast_radius = self._calculate_blast_radius(action)
        if blast_radius > 50:  # Affects >50% of infrastructure
            return False, f"Blast radius too high ({blast_radius}%)"
        
        return True, ""
    
    def _calculate_rule_based_confidence(
        self, 
        action: Dict, 
        incident: Dict
    ) -> float:
        """
        Calculate confidence using deterministic rules
        """
        confidence = 50.0  # Base confidence
        
        action_type = action['action_type']
        risk = action.get('risk', 'medium')
        
        # Rule 1: Low risk actions get higher confidence
        if risk == 'low':
            confidence += 20
        elif risk == 'high':
            confidence -= 20
        
        # Rule 2: Rollback after deployment gets high confidence
        if action_type == 'rollback':
            recent_deployments = incident.get('recent_deployments', [])
            if recent_deployments and len(recent_deployments) > 0:
                # Check if deployment was recent (< 10 min)
                deploy_time = datetime.fromisoformat(
                    recent_deployments[-1]['timestamp'].replace('Z', '+00:00')
                )
                time_since = (datetime.now(timezone.utc) - deploy_time).total_seconds()
                if time_since < 600:  # < 10 minutes
                    confidence += 25
        
        # Rule 3: Scale up during latency spike
        if action_type == 'scale_up':
            has_latency_issue = any(
                'latency' in a.get('metric_name', '').lower()
                for a in incident.get('anomalies', [])
            )
            if has_latency_issue:
                confidence += 15
        
        # Rule 4: Restart for memory leaks
        if action_type == 'restart_service':
            has_memory_issue = any(
                'memory' in a.get('metric_name', '').lower()
                for a in incident.get('anomalies', [])
            )
            if has_memory_issue:
                confidence += 15
        
        # Rule 5: Critical severity increases confidence for any action
        severity = incident.get('analysis', {}).get('severity', 'medium')
        if severity == 'critical':
            confidence += 10
        
        return min(100.0, max(0.0, confidence))
    
    def _extract_ai_confidence(self, analysis: Dict, action: Dict) -> float:
        """
        Extract confidence from AI analysis
        """
        # Get overall AI confidence in root cause
        ai_confidence = analysis.get('root_cause', {}).get('confidence', 50)
        
        # Find matching recommended action
        recommended_actions = analysis.get('recommended_actions', [])
        
        for rec_action in recommended_actions:
            if rec_action.get('action', '').lower() in action['action_type'].lower():
                # This action was recommended by AI
                # Check priority (higher priority = higher confidence)
                priority = rec_action.get('priority', 5)
                priority_boost = (6 - priority) * 5  # Priority 1 = +25, Priority 5 = +5
                
                return min(100.0, ai_confidence + priority_boost)
        
        # Action not recommended by AI
        return ai_confidence * 0.6  # Reduce confidence
    
    def _calculate_historical_confidence(
        self,
        action: Dict,
        similar_incidents: Optional[List[Dict]]
    ) -> float:
        """
        Calculate confidence based on historical success
        """
        if not similar_incidents:
            return 50.0  # Neutral when no history
        
        action_type = action['action_type']
        
        # Count successes with this action
        total_similar = 0
        successful_with_action = 0
        
        for incident in similar_incidents:
            total_similar += 1
            
            if not incident.get('was_successful'):
                continue
            
            actions_taken = incident.get('actions_taken', [])
            
            for taken_action in actions_taken:
                if taken_action.get('action_type') == action_type:
                    successful_with_action += 1
                    break
        
        if total_similar == 0:
            return 50.0
        
        # Calculate success rate
        success_rate = (successful_with_action / total_similar) * 100
        
        # Weight by similarity score
        avg_similarity = sum(
            inc.get('similarity_score', 0.5) for inc in similar_incidents
        ) / len(similar_incidents)
        
        weighted_confidence = success_rate * avg_similarity
        
        return min(100.0, weighted_confidence)
    
    def _build_reasoning(
        self,
        rule_conf: float,
        ai_conf: float,
        hist_conf: float,
        overall: float
    ) -> str:
        """Build human-readable reasoning"""
        reasoning = f"Confidence breakdown:\n"
        reasoning += f"  • Rule-based analysis: {rule_conf:.1f}%\n"
        reasoning += f"  • AI recommendation: {ai_conf:.1f}%\n"
        reasoning += f"  • Historical success: {hist_conf:.1f}%\n"
        reasoning += f"  • Overall confidence: {overall:.1f}%\n"
        
        if overall >= 90:
            reasoning += "\n✓ Very high confidence - safe for autonomous execution"
        elif overall >= 75:
            reasoning += "\n✓ High confidence - approved for autonomous execution"
        elif overall >= 60:
            reasoning += "\n⚠ Medium confidence - requires manual approval"
        else:
            reasoning += "\n✗ Low confidence - not recommended"
        
        return reasoning
    
    async def _check_service_health(self, service: str) -> str:
        """Check current service health"""
        try:
            # Get recent anomalies
            anomalies = self.redis.lrange(f"recent_anomalies:{service}", 0, 9)
            
            critical_count = 0
            high_count = 0
            
            for anomaly_json in anomalies:
                anomaly = json.loads(anomaly_json)
                severity = anomaly.get('severity', 'low')
                
                if severity == 'critical':
                    critical_count += 1
                elif severity == 'high':
                    high_count += 1
            
            if critical_count >= 3:
                return 'critical'
            elif critical_count >= 1 or high_count >= 3:
                return 'degraded'
            else:
                return 'healthy'
        except:
            return 'unknown'
    
    def _calculate_blast_radius(self, action: Dict) -> float:
        """
        Estimate blast radius (percentage of infrastructure affected)
        """
        action_type = action['action_type']
        
        # Rough estimates
        blast_radius_map = {
            'rollback': 100,  # Affects entire service
            'restart_service': 100,
            'scale_up': 30,  # Additive, less risky
            'scale_down': 50,
            'clear_cache': 80,
            'kill_connections': 60
        }
        
        return blast_radius_map.get(action_type, 50)
    
    def _count_recent_actions(self, action_type: str, hours: int = 1) -> int:
        """Count recent actions of specific type"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        count = 0
        for action in self.action_history:
            if action.get('action_type') == action_type:
                action_time = datetime.fromisoformat(
                    action['executed_at'].replace('Z', '+00:00')
                ).timestamp()
                
                if action_time > cutoff_time:
                    count += 1
        
        return count
    
    async def execute_autonomous_action(
        self,
        action: Dict,
        confidence: float,
        reasoning: str
    ) -> Dict:
        """
        Execute action autonomously with monitoring
        """
        action_id = action['id']
        
        print(f"[AUTONOMOUS] Executing action {action_id} autonomously")
        print(f"  Confidence: {confidence:.1f}%")
        print(f"  Mode: {self.execution_mode.value}")
        
        # Mark as executing
        self.active_actions[action_id] = {
            'action': action,
            'started_at': datetime.now(timezone.utc),
            'confidence': confidence
        }
        
        # Update action status
        action['status'] = 'executing_autonomous'
        action['autonomous_confidence'] = confidence
        action['autonomous_reasoning'] = reasoning
        action['executed_at'] = datetime.now(timezone.utc).isoformat()
        
        self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
        
        try:
            # Execute via action executor
            result = await self.action_executor.execute_action(action_id)
            
            # Update state
            action['completed_at'] = datetime.now(timezone.utc).isoformat()
            action['result'] = result
            
            if result['success']:
                action['status'] = 'success_autonomous'
                print(f"[AUTONOMOUS] ✓ Action completed successfully")
                
                # Learn from success
                await self._record_autonomous_success(action, confidence)
            else:
                action['status'] = 'failed_autonomous'
                print(f"[AUTONOMOUS] ✗ Action failed: {result.get('error')}")
                
                # Learn from failure
                await self._record_autonomous_failure(action, confidence)
            
            # Update tracking
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            self.action_history.append(action)
            
            # Update last action time for cooldown
            cooldown_key = f"{action['service']}:{action['action_type']}"
            self.last_action_time[cooldown_key] = datetime.now(timezone.utc).timestamp()
            
            return result
            
        except Exception as e:
            print(f"[AUTONOMOUS] ✗ Execution error: {e}")
            action['status'] = 'failed_autonomous'
            action['error'] = str(e)
            
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            
            return {"success": False, "error": str(e)}
        
        finally:
            # Remove from active
            if action_id in self.active_actions:
                del self.active_actions[action_id]
    
    async def _record_autonomous_success(self, action: Dict, confidence: float):
        """Learn from successful autonomous action"""
        # Increase weights for successful predictions
        if confidence >= 90:
            # Very high confidence was correct - reinforce
            self._adjust_learning_weights(success=True, confidence_level='very_high')
        
        # Store success for future learning
        success_record = {
            'action_id': action['id'],
            'action_type': action['action_type'],
            'confidence': confidence,
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.redis.lpush('autonomous_outcomes', json.dumps(success_record))
        print(f"[LEARNING] Recorded autonomous success: {action['action_type']}")
    
    async def _record_autonomous_failure(self, action: Dict, confidence: float):
        """Learn from failed autonomous action"""
        # Decrease weights when high confidence was wrong
        if confidence >= 75:
            self._adjust_learning_weights(success=False, confidence_level='high')
        
        # Store failure for learning
        failure_record = {
            'action_id': action['id'],
            'action_type': action['action_type'],
            'confidence': confidence,
            'success': False,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.redis.lpush('autonomous_outcomes', json.dumps(failure_record))
        print(f"[LEARNING] Recorded autonomous failure: {action['action_type']}")
    
    def _adjust_learning_weights(self, success: bool, confidence_level: str):
        """Adjust learning weights based on outcomes"""
        adjustment = 0.02 if success else -0.02
        
        # This is a simple approach - in production, use proper ML
        if confidence_level in ['very_high', 'high']:
            # Successful high-confidence predictions reinforce all weights
            self.rule_weight += adjustment
            self.ai_weight += adjustment
            self.historical_weight += adjustment
            
            # Normalize to sum to 1.0
            total = self.rule_weight + self.ai_weight + self.historical_weight
            self.rule_weight /= total
            self.ai_weight /= total
            self.historical_weight /= total
    
    def set_execution_mode(self, mode: ExecutionMode):
        """Change execution mode"""
        self.execution_mode = mode
        print(f"[AUTONOMOUS] Execution mode changed to: {mode.value}")
    
    def get_autonomous_stats(self) -> Dict:
        """Get autonomous execution statistics"""
        try:
            # Get recent outcomes
            outcomes = self.redis.lrange('autonomous_outcomes', 0, 99)
            
            total = len(outcomes)
            successes = 0
            
            for outcome_json in outcomes:
                outcome = json.loads(outcome_json)
                if outcome.get('success'):
                    successes += 1
            
            success_rate = (successes / total * 100) if total > 0 else 0
            
            return {
                'execution_mode': self.execution_mode.value,
                'total_autonomous_actions': total,
                'successful_actions': successes,
                'success_rate': success_rate,
                'active_actions': len(self.active_actions),
                'confidence_threshold': self.confidence_threshold,
                'learning_weights': {
                    'rule_based': round(self.rule_weight, 2),
                    'ai': round(self.ai_weight, 2),
                    'historical': round(self.historical_weight, 2)
                },
                'is_night_mode_active': self._is_night_hours() if self.execution_mode == ExecutionMode.NIGHT_MODE else None
            }
        except:
            return {
                'execution_mode': self.execution_mode.value,
                'error': 'Failed to get stats'
            }