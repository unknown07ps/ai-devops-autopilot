"""
Learning Engine - Continuous Learning from Incident Outcomes
Tracks pattern effectiveness, adapts confidence scores, and promotes/demotes patterns
This is where your system's intelligence is stored - NOT in the LLM
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib


@dataclass
class LearningOutcome:
    """Record of action outcome for learning"""
    outcome_id: str
    incident_id: str
    pattern_id: str
    action_type: str
    action_category: str
    success: bool
    confidence_at_execution: float
    execution_time_seconds: float
    pre_metrics: Dict = field(default_factory=dict)
    post_metrics: Dict = field(default_factory=dict)
    improvement_score: float = 0.0  # -100 to +100
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class PatternStats:
    """Statistics for a pattern's effectiveness"""
    pattern_id: str
    total_matches: int = 0
    successful_resolutions: int = 0
    failed_resolutions: int = 0
    avg_resolution_time_seconds: float = 0.0
    avg_confidence_score: float = 0.0
    autonomous_executions: int = 0
    autonomous_successes: int = 0
    last_matched: str = None
    last_successful: str = None
    confidence_adjustment: float = 0.0  # Cumulative adjustment
    is_promoted: bool = False  # Promoted to autonomous-safe
    is_demoted: bool = False   # Demoted due to failures
    action_success_rates: Dict[str, float] = field(default_factory=dict)


class LearningEngine:
    """
    Core learning system for DevOps intelligence
    
    Responsibilities:
    1. Track outcomes of all actions (success/failure)
    2. Calculate and update pattern confidence scores
    3. Promote patterns to autonomous-safe after proven reliability
    4. Demote patterns after repeated failures
    5. Recommend optimal actions based on historical success
    """
    
    # Thresholds for pattern promotion/demotion
    PROMOTION_THRESHOLD = {
        "min_executions": 10,           # Minimum times pattern was matched
        "success_rate": 0.90,           # 90% success rate required
        "min_autonomous_attempts": 5,    # Must have some autonomous attempts
        "autonomous_success_rate": 0.95  # 95% autonomous success required
    }
    
    DEMOTION_THRESHOLD = {
        "min_failures": 3,              # At least 3 failures
        "failure_rate": 0.30,           # 30% failure rate triggers demotion
        "consecutive_failures": 2       # 2 consecutive failures triggers immediate review
    }
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pattern_stats: Dict[str, PatternStats] = {}
        self._load_stats()
    
    def _load_stats(self):
        """Load pattern statistics from Redis"""
        try:
            keys = self.redis.keys("learning:pattern_stats:*")
            for key in keys:
                data = self.redis.get(key)
                if data:
                    stats_dict = json.loads(data)
                    pattern_id = stats_dict.get("pattern_id")
                    if pattern_id:
                        self.pattern_stats[pattern_id] = PatternStats(**stats_dict)
        except Exception as e:
            print(f"Error loading pattern stats: {e}")
    
    def _save_stats(self, pattern_id: str):
        """Save pattern statistics to Redis"""
        if pattern_id in self.pattern_stats:
            stats = self.pattern_stats[pattern_id]
            try:
                self.redis.set(
                    f"learning:pattern_stats:{pattern_id}",
                    json.dumps(asdict(stats))
                )
            except Exception as e:
                print(f"Error saving pattern stats: {e}")
    
    def record_outcome(self, outcome: LearningOutcome) -> Dict:
        """
        Record the outcome of an action and update learning
        
        This is the core learning function - called after every action
        Returns insights about what was learned
        """
        insights = {
            "pattern_id": outcome.pattern_id,
            "outcome": "success" if outcome.success else "failure",
            "confidence_change": 0.0,
            "promotion_status": None,
            "recommendations": []
        }
        
        # Get or create pattern stats
        if outcome.pattern_id not in self.pattern_stats:
            self.pattern_stats[outcome.pattern_id] = PatternStats(pattern_id=outcome.pattern_id)
        
        stats = self.pattern_stats[outcome.pattern_id]
        
        # Update basic stats
        stats.total_matches += 1
        stats.last_matched = outcome.timestamp
        
        if outcome.success:
            stats.successful_resolutions += 1
            stats.last_successful = outcome.timestamp
            confidence_delta = self._calculate_positive_learning(outcome, stats)
        else:
            stats.failed_resolutions += 1
            confidence_delta = self._calculate_negative_learning(outcome, stats)
        
        # Update confidence adjustment
        stats.confidence_adjustment += confidence_delta
        insights["confidence_change"] = confidence_delta
        
        # Update action-specific success rates
        action_key = f"{outcome.action_category}:{outcome.action_type}"
        if action_key not in stats.action_success_rates:
            stats.action_success_rates[action_key] = 0.5  # Start neutral
        
        # Exponential moving average for action success rate
        alpha = 0.3  # Learning rate
        current_rate = stats.action_success_rates[action_key]
        new_rate = alpha * (1.0 if outcome.success else 0.0) + (1 - alpha) * current_rate
        stats.action_success_rates[action_key] = new_rate
        
        # Update resolution time average
        if stats.total_matches > 1:
            stats.avg_resolution_time_seconds = (
                (stats.avg_resolution_time_seconds * (stats.total_matches - 1) + outcome.execution_time_seconds)
                / stats.total_matches
            )
        else:
            stats.avg_resolution_time_seconds = outcome.execution_time_seconds
        
        # Check for promotion/demotion
        promotion_check = self._check_promotion(stats)
        demotion_check = self._check_demotion(stats)
        
        if promotion_check["eligible"] and not stats.is_promoted:
            stats.is_promoted = True
            insights["promotion_status"] = "promoted"
            insights["recommendations"].append(
                f"Pattern {outcome.pattern_id} promoted to autonomous-safe based on "
                f"{stats.successful_resolutions}/{stats.total_matches} success rate"
            )
        
        if demotion_check["should_demote"] and not stats.is_demoted:
            stats.is_demoted = True
            insights["promotion_status"] = "demoted"
            insights["recommendations"].append(
                f"Pattern {outcome.pattern_id} demoted due to high failure rate. "
                f"Requires human review."
            )
        
        # Store the outcome in history
        self._store_outcome(outcome)
        
        # Save updated stats
        self._save_stats(outcome.pattern_id)
        
        return insights
    
    def _calculate_positive_learning(self, outcome: LearningOutcome, stats: PatternStats) -> float:
        """Calculate confidence boost from successful outcome"""
        
        # Base boost
        boost = 2.0
        
        # Higher boost if confidence was low (we learned something unexpected)
        if outcome.confidence_at_execution < 60:
            boost += 3.0
        elif outcome.confidence_at_execution < 80:
            boost += 1.5
        
        # Higher boost for fast resolution
        if outcome.execution_time_seconds < stats.avg_resolution_time_seconds * 0.5:
            boost += 1.0
        
        # Bonus for significant metric improvement
        if outcome.improvement_score > 50:
            boost += 2.0
        elif outcome.improvement_score > 25:
            boost += 1.0
        
        # Diminishing returns - patterns with many successes learn less
        if stats.successful_resolutions > 50:
            boost *= 0.5
        elif stats.successful_resolutions > 20:
            boost *= 0.75
        
        return min(boost, 5.0)  # Cap at 5 points per success
    
    def _calculate_negative_learning(self, outcome: LearningOutcome, stats: PatternStats) -> float:
        """Calculate confidence reduction from failed outcome"""
        
        # Base penalty
        penalty = -3.0
        
        # Higher penalty if confidence was high (overconfident)
        if outcome.confidence_at_execution > 90:
            penalty -= 5.0
        elif outcome.confidence_at_execution > 75:
            penalty -= 2.0
        
        # Worse penalty if it made things worse
        if outcome.improvement_score < -25:
            penalty -= 3.0
        
        return max(penalty, -10.0)  # Cap at -10 points per failure
    
    def _check_promotion(self, stats: PatternStats) -> Dict:
        """Check if pattern should be promoted to autonomous-safe"""
        
        thresholds = self.PROMOTION_THRESHOLD
        
        success_rate = (
            stats.successful_resolutions / stats.total_matches 
            if stats.total_matches > 0 else 0
        )
        
        autonomous_success_rate = (
            stats.autonomous_successes / stats.autonomous_executions
            if stats.autonomous_executions > 0 else 0
        )
        
        eligible = (
            stats.total_matches >= thresholds["min_executions"] and
            success_rate >= thresholds["success_rate"] and
            (
                stats.autonomous_executions == 0 or  # No autonomous attempts yet is OK
                autonomous_success_rate >= thresholds["autonomous_success_rate"]
            )
        )
        
        return {
            "eligible": eligible,
            "success_rate": success_rate,
            "total_executions": stats.total_matches,
            "autonomous_success_rate": autonomous_success_rate,
            "missing_requirements": self._get_missing_requirements(stats, thresholds)
        }
    
    def _get_missing_requirements(self, stats: PatternStats, thresholds: Dict) -> List[str]:
        """Get list of requirements not yet met for promotion"""
        missing = []
        
        if stats.total_matches < thresholds["min_executions"]:
            missing.append(f"Need {thresholds['min_executions'] - stats.total_matches} more executions")
        
        success_rate = stats.successful_resolutions / stats.total_matches if stats.total_matches > 0 else 0
        if success_rate < thresholds["success_rate"]:
            missing.append(f"Success rate {success_rate:.1%} below {thresholds['success_rate']:.1%} threshold")
        
        return missing
    
    def _check_demotion(self, stats: PatternStats) -> Dict:
        """Check if pattern should be demoted"""
        
        thresholds = self.DEMOTION_THRESHOLD
        
        failure_rate = (
            stats.failed_resolutions / stats.total_matches
            if stats.total_matches > 0 else 0
        )
        
        should_demote = (
            stats.failed_resolutions >= thresholds["min_failures"] and
            failure_rate >= thresholds["failure_rate"]
        )
        
        return {
            "should_demote": should_demote,
            "failure_rate": failure_rate,
            "failure_count": stats.failed_resolutions
        }
    
    def _store_outcome(self, outcome: LearningOutcome):
        """Store outcome in history for later analysis"""
        try:
            # Store in outcome history (keep last 1000)
            self.redis.lpush(
                f"learning:outcomes:{outcome.pattern_id}",
                json.dumps(asdict(outcome))
            )
            self.redis.ltrim(f"learning:outcomes:{outcome.pattern_id}", 0, 999)
            
            # Also store in global timeline
            self.redis.lpush(
                "learning:outcomes:timeline",
                json.dumps({
                    "outcome_id": outcome.outcome_id,
                    "pattern_id": outcome.pattern_id,
                    "success": outcome.success,
                    "timestamp": outcome.timestamp
                })
            )
            self.redis.ltrim("learning:outcomes:timeline", 0, 9999)
            
        except Exception as e:
            print(f"Error storing outcome: {e}")
    
    def get_pattern_confidence(self, pattern_id: str, base_confidence: float = 50.0) -> float:
        """
        Get adjusted confidence for a pattern based on learning history
        
        Args:
            pattern_id: The pattern to get confidence for
            base_confidence: The base confidence from pattern matching
            
        Returns:
            Adjusted confidence score (0-100)
        """
        if pattern_id not in self.pattern_stats:
            return base_confidence
        
        stats = self.pattern_stats[pattern_id]
        
        # Apply learned adjustment
        adjusted = base_confidence + stats.confidence_adjustment
        
        # Factor in success rate
        if stats.total_matches > 5:
            success_rate = stats.successful_resolutions / stats.total_matches
            # Weighted blend: 70% base, 30% success rate
            adjusted = 0.7 * adjusted + 0.3 * (success_rate * 100)
        
        # Clamp to valid range
        return max(0.0, min(100.0, adjusted))
    
    def get_best_action(
        self,
        pattern_id: str,
        available_actions: List[Dict]
    ) -> Optional[Dict]:
        """
        Get the best action for a pattern based on historical success
        
        Returns the action with highest success rate for this pattern
        """
        if pattern_id not in self.pattern_stats:
            return available_actions[0] if available_actions else None
        
        stats = self.pattern_stats[pattern_id]
        
        best_action = None
        best_score = -1
        
        for action in available_actions:
            action_key = f"{action.get('category', '')}:{action.get('type', '')}"
            
            if action_key in stats.action_success_rates:
                score = stats.action_success_rates[action_key]
                if score > best_score:
                    best_score = score
                    best_action = action
        
        return best_action if best_action else (available_actions[0] if available_actions else None)
    
    def is_autonomous_safe(self, pattern_id: str) -> Tuple[bool, str]:
        """
        Check if pattern is safe for autonomous execution
        
        Returns: (is_safe, reason)
        """
        if pattern_id not in self.pattern_stats:
            return False, "No learning history for this pattern"
        
        stats = self.pattern_stats[pattern_id]
        
        if stats.is_demoted:
            return False, f"Pattern demoted due to high failure rate ({stats.failed_resolutions} failures)"
        
        if stats.is_promoted:
            return True, f"Pattern promoted based on {stats.successful_resolutions}/{stats.total_matches} success rate"
        
        # Check if it meets promotion threshold
        promotion = self._check_promotion(stats)
        if promotion["eligible"]:
            return True, f"Pattern eligible for autonomous execution (success rate: {promotion['success_rate']:.1%})"
        
        return False, f"Not enough history: {', '.join(promotion['missing_requirements'])}"
    
    def get_action_success_rate(self, pattern_id: str, action_type: str, action_category: str) -> float:
        """Get historical success rate for a specific action on a pattern"""
        if pattern_id not in self.pattern_stats:
            return 0.5  # Unknown - neutral score
        
        action_key = f"{action_category}:{action_type}"
        return self.pattern_stats[pattern_id].action_success_rates.get(action_key, 0.5)
    
    def get_learning_summary(self) -> Dict:
        """Get overall learning summary statistics"""
        total_patterns = len(self.pattern_stats)
        promoted = sum(1 for s in self.pattern_stats.values() if s.is_promoted)
        demoted = sum(1 for s in self.pattern_stats.values() if s.is_demoted)
        
        total_outcomes = sum(s.total_matches for s in self.pattern_stats.values())
        total_successes = sum(s.successful_resolutions for s in self.pattern_stats.values())
        
        return {
            "tracked_patterns": total_patterns,
            "promoted_patterns": promoted,
            "demoted_patterns": demoted,
            "total_outcomes_recorded": total_outcomes,
            "overall_success_rate": total_successes / total_outcomes if total_outcomes > 0 else 0,
            "patterns_by_confidence": self._group_by_confidence(),
            "top_performing_patterns": self._get_top_patterns(5),
            "patterns_needing_attention": self._get_problem_patterns(5)
        }
    
    def _group_by_confidence(self) -> Dict[str, int]:
        """Group patterns by confidence level"""
        groups = {"excellent (90+)": 0, "good (70-89)": 0, "fair (50-69)": 0, "poor (<50)": 0}
        
        for pattern_id, stats in self.pattern_stats.items():
            conf = self.get_pattern_confidence(pattern_id, 50.0)
            if conf >= 90:
                groups["excellent (90+)"] += 1
            elif conf >= 70:
                groups["good (70-89)"] += 1
            elif conf >= 50:
                groups["fair (50-69)"] += 1
            else:
                groups["poor (<50)"] += 1
        
        return groups
    
    def _get_top_patterns(self, limit: int) -> List[Dict]:
        """Get top performing patterns"""
        patterns = []
        for pattern_id, stats in self.pattern_stats.items():
            if stats.total_matches >= 5:
                success_rate = stats.successful_resolutions / stats.total_matches
                patterns.append({
                    "pattern_id": pattern_id,
                    "success_rate": success_rate,
                    "total_matches": stats.total_matches
                })
        
        patterns.sort(key=lambda x: x["success_rate"], reverse=True)
        return patterns[:limit]
    
    def _get_problem_patterns(self, limit: int) -> List[Dict]:
        """Get patterns that need attention"""
        patterns = []
        for pattern_id, stats in self.pattern_stats.items():
            if stats.failed_resolutions >= 2:
                failure_rate = stats.failed_resolutions / stats.total_matches if stats.total_matches > 0 else 0
                patterns.append({
                    "pattern_id": pattern_id,
                    "failure_rate": failure_rate,
                    "failures": stats.failed_resolutions,
                    "is_demoted": stats.is_demoted
                })
        
        patterns.sort(key=lambda x: x["failure_rate"], reverse=True)
        return patterns[:limit]
    
    def export_training_data(self) -> List[Dict]:
        """Export all learning data for external analysis or backup"""
        data = []
        
        for pattern_id, stats in self.pattern_stats.items():
            # Get outcomes for this pattern
            try:
                outcomes_raw = self.redis.lrange(f"learning:outcomes:{pattern_id}", 0, -1)
                outcomes = [json.loads(o) for o in outcomes_raw]
            except:
                outcomes = []
            
            data.append({
                "pattern_id": pattern_id,
                "stats": asdict(stats),
                "outcomes": outcomes,
                "current_confidence": self.get_pattern_confidence(pattern_id, 50.0)
            })
        
        return data
    
    def create_incident_fingerprint(self, anomalies: List[Dict], service: str) -> str:
        """
        Create a unique fingerprint for an incident based on its characteristics
        Used to find similar historical incidents
        """
        # Extract key features
        features = []
        
        # Service
        features.append(f"service:{service}")
        
        # Anomaly types and metrics
        for anomaly in anomalies:
            if "metric_name" in anomaly:
                features.append(f"metric:{anomaly['metric_name']}")
            if "type" in anomaly:
                features.append(f"type:{anomaly['type']}")
            if "severity" in anomaly:
                features.append(f"severity:{anomaly['severity']}")
        
        # Sort for consistency
        features.sort()
        
        # Create hash
        fingerprint = hashlib.md5("|".join(features).encode()).hexdigest()[:16]
        return fingerprint


# Convenience function
def get_learning_engine(redis_client) -> LearningEngine:
    """Get learning engine instance"""
    return LearningEngine(redis_client)
