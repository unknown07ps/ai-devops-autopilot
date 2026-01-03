"""
Action Recorder - Comprehensive action logging and analysis
Records pre/post action metrics for effectiveness scoring
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict


@dataclass
class ActionRecord:
    """Complete record of an action execution"""
    record_id: str
    incident_id: str
    incident_fingerprint: str
    pattern_id: str
    action_type: str
    action_category: str
    params: Dict = field(default_factory=dict)
    
    # Confidence & decision info
    confidence_score: float = 0.0
    was_autonomous: bool = False
    reasoning: str = ""
    
    # Timing
    started_at: str = None
    completed_at: str = None
    execution_time_seconds: float = 0.0
    
    # Pre-action state
    pre_metrics: Dict = field(default_factory=dict)
    pre_health_status: str = "unknown"
    
    # Post-action state
    post_metrics: Dict = field(default_factory=dict)
    post_health_status: str = "unknown"
    
    # Results
    success: bool = False
    error_message: str = None
    rollback_performed: bool = False
    rollback_success: bool = False
    
    # Analysis
    effectiveness_score: float = 0.0  # -100 to +100
    user_feedback: str = None
    similar_action_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()
        if not self.record_id:
            self.record_id = str(uuid.uuid4())


class ActionRecorder:
    """
    Records and analyzes all action executions
    
    Provides:
    - Complete action audit trail
    - Pre/post metric comparison
    - Effectiveness scoring
    - Training data export
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_records: Dict[str, ActionRecord] = {}
    
    def start_recording(
        self,
        incident_id: str,
        incident_fingerprint: str,
        pattern_id: str,
        action_type: str,
        action_category: str,
        params: Dict = None,
        confidence_score: float = 0.0,
        was_autonomous: bool = False,
        reasoning: str = "",
        pre_metrics: Dict = None
    ) -> str:
        """
        Start recording an action execution
        
        Returns: record_id to use for completing the record
        """
        record = ActionRecord(
            record_id=str(uuid.uuid4()),
            incident_id=incident_id,
            incident_fingerprint=incident_fingerprint,
            pattern_id=pattern_id,
            action_type=action_type,
            action_category=action_category,
            params=params or {},
            confidence_score=confidence_score,
            was_autonomous=was_autonomous,
            reasoning=reasoning,
            pre_metrics=pre_metrics or {}
        )
        
        # Capture pre-action health status
        record.pre_health_status = self._assess_health(pre_metrics)
        
        # Store in active records
        self.active_records[record.record_id] = record
        
        # Also persist to Redis in case of crash
        self._save_active_record(record)
        
        return record.record_id
    
    def complete_recording(
        self,
        record_id: str,
        success: bool,
        post_metrics: Dict = None,
        error_message: str = None,
        rollback_performed: bool = False,
        rollback_success: bool = False
    ) -> ActionRecord:
        """
        Complete an action recording with results
        
        Returns: The completed ActionRecord
        """
        if record_id not in self.active_records:
            # Try to load from Redis
            record = self._load_active_record(record_id)
            if not record:
                raise ValueError(f"No active record found for {record_id}")
            self.active_records[record_id] = record
        
        record = self.active_records[record_id]
        
        # Update completion data
        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.success = success
        record.post_metrics = post_metrics or {}
        record.error_message = error_message
        record.rollback_performed = rollback_performed
        record.rollback_success = rollback_success
        
        # Calculate execution time
        started = datetime.fromisoformat(record.started_at.replace('Z', '+00:00'))
        completed = datetime.fromisoformat(record.completed_at.replace('Z', '+00:00'))
        record.execution_time_seconds = (completed - started).total_seconds()
        
        # Assess post-action health
        record.post_health_status = self._assess_health(post_metrics)
        
        # Calculate effectiveness score
        record.effectiveness_score = self._calculate_effectiveness(record)
        
        # Find similar past actions
        record.similar_action_ids = self._find_similar_actions(record)
        
        # Store completed record
        self._store_completed_record(record)
        
        # Remove from active
        del self.active_records[record_id]
        self._remove_active_record(record_id)
        
        return record
    
    def _assess_health(self, metrics: Dict) -> str:
        """Assess overall health from metrics"""
        if not metrics:
            return "unknown"
        
        # Check for critical indicators
        if metrics.get("error_rate", 0) > 10:
            return "critical"
        if metrics.get("cpu_usage", 0) > 95:
            return "critical"
        if metrics.get("memory_usage", 0) > 95:
            return "critical"
        
        if metrics.get("error_rate", 0) > 5:
            return "degraded"
        if metrics.get("cpu_usage", 0) > 80:
            return "degraded"
        if metrics.get("memory_usage", 0) > 85:
            return "degraded"
        
        if metrics.get("latency_p99_ms", 0) > 5000:
            return "slow"
        
        return "healthy"
    
    def _calculate_effectiveness(self, record: ActionRecord) -> float:
        """
        Calculate effectiveness score (-100 to +100)
        
        Positive = improved the situation
        Negative = made things worse
        Zero = no change
        """
        if not record.pre_metrics or not record.post_metrics:
            return 0.0 if record.success else -25.0
        
        score = 0.0
        comparisons = []
        
        # Compare key metrics (lower is better for these)
        lower_is_better = ["error_rate", "cpu_usage", "memory_usage", "latency_p99_ms", 
                          "active_connections", "queue_depth"]
        
        for metric in lower_is_better:
            pre_val = record.pre_metrics.get(metric)
            post_val = record.post_metrics.get(metric)
            
            if pre_val is not None and post_val is not None and pre_val > 0:
                improvement = (pre_val - post_val) / pre_val * 100
                comparisons.append(improvement)
        
        # Compare key metrics (higher is better for these)
        higher_is_better = ["throughput", "success_rate", "healthy_instances"]
        
        for metric in higher_is_better:
            pre_val = record.pre_metrics.get(metric)
            post_val = record.post_metrics.get(metric)
            
            if pre_val is not None and post_val is not None and pre_val > 0:
                improvement = (post_val - pre_val) / pre_val * 100
                comparisons.append(improvement)
        
        if comparisons:
            score = sum(comparisons) / len(comparisons)
        
        # Health status change bonus/penalty
        health_order = ["critical", "degraded", "slow", "unknown", "healthy"]
        pre_idx = health_order.index(record.pre_health_status) if record.pre_health_status in health_order else 3
        post_idx = health_order.index(record.post_health_status) if record.post_health_status in health_order else 3
        
        health_change = (post_idx - pre_idx) * 10
        score += health_change
        
        # Success/failure factor
        if not record.success:
            score = min(score, 0) - 25
        
        # Rollback penalty
        if record.rollback_performed:
            score -= 20
            if record.rollback_success:
                score += 10  # Partial recovery
        
        return max(-100, min(100, score))
    
    def _find_similar_actions(self, record: ActionRecord) -> List[str]:
        """Find similar past actions for comparison"""
        similar = []
        try:
            # Look for actions with same pattern and action type
            key = f"action_records:by_pattern:{record.pattern_id}:{record.action_type}"
            similar_ids = self.redis.lrange(key, 0, 4)
            similar = [id.decode() if isinstance(id, bytes) else id for id in similar_ids]
        except:
            pass
        return similar
    
    def _save_active_record(self, record: ActionRecord):
        """Save active record to Redis"""
        try:
            self.redis.setex(
                f"action_records:active:{record.record_id}",
                3600,  # 1 hour TTL for active records
                json.dumps(asdict(record))
            )
        except Exception as e:
            print(f"Error saving active record: {e}")
    
    def _load_active_record(self, record_id: str) -> Optional[ActionRecord]:
        """Load active record from Redis"""
        try:
            data = self.redis.get(f"action_records:active:{record_id}")
            if data:
                return ActionRecord(**json.loads(data))
        except:
            pass
        return None
    
    def _remove_active_record(self, record_id: str):
        """Remove active record from Redis"""
        try:
            self.redis.delete(f"action_records:active:{record_id}")
        except:
            pass
    
    def _store_completed_record(self, record: ActionRecord):
        """Store completed record in Redis"""
        try:
            record_json = json.dumps(asdict(record))
            
            # Main record storage
            self.redis.setex(
                f"action_records:completed:{record.record_id}",
                86400 * 90,  # Keep for 90 days
                record_json
            )
            
            # Index by incident
            self.redis.lpush(
                f"action_records:by_incident:{record.incident_id}",
                record.record_id
            )
            self.redis.ltrim(f"action_records:by_incident:{record.incident_id}", 0, 99)
            
            # Index by pattern
            self.redis.lpush(
                f"action_records:by_pattern:{record.pattern_id}:{record.action_type}",
                record.record_id
            )
            self.redis.ltrim(f"action_records:by_pattern:{record.pattern_id}:{record.action_type}", 0, 99)
            
            # Index by date
            date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.redis.lpush(f"action_records:by_date:{date_key}", record.record_id)
            
            # Success/failure indexes
            status = "success" if record.success else "failure"
            self.redis.lpush(f"action_records:by_status:{status}", record.record_id)
            self.redis.ltrim(f"action_records:by_status:{status}", 0, 999)
            
        except Exception as e:
            print(f"Error storing completed record: {e}")
    
    def get_record(self, record_id: str) -> Optional[ActionRecord]:
        """Get a specific action record"""
        try:
            data = self.redis.get(f"action_records:completed:{record_id}")
            if data:
                return ActionRecord(**json.loads(data))
        except:
            pass
        return None
    
    def get_records_for_incident(self, incident_id: str) -> List[ActionRecord]:
        """Get all action records for an incident"""
        records = []
        try:
            record_ids = self.redis.lrange(f"action_records:by_incident:{incident_id}", 0, -1)
            for record_id in record_ids:
                rid = record_id.decode() if isinstance(record_id, bytes) else record_id
                record = self.get_record(rid)
                if record:
                    records.append(record)
        except:
            pass
        return records
    
    def get_pattern_effectiveness(self, pattern_id: str, action_type: str = None) -> Dict:
        """Get effectiveness statistics for a pattern"""
        try:
            if action_type:
                key = f"action_records:by_pattern:{pattern_id}:{action_type}"
            else:
                # Get for all action types
                key = f"action_records:by_pattern:{pattern_id}:*"
            
            record_ids = self.redis.lrange(key, 0, 99)
            
            if not record_ids:
                return {"total": 0, "success_rate": 0, "avg_effectiveness": 0}
            
            successes = 0
            total_effectiveness = 0
            
            for record_id in record_ids:
                rid = record_id.decode() if isinstance(record_id, bytes) else record_id
                record = self.get_record(rid)
                if record:
                    if record.success:
                        successes += 1
                    total_effectiveness += record.effectiveness_score
            
            total = len(record_ids)
            return {
                "total": total,
                "successes": successes,
                "success_rate": successes / total if total > 0 else 0,
                "avg_effectiveness": total_effectiveness / total if total > 0 else 0
            }
        except:
            return {"total": 0, "success_rate": 0, "avg_effectiveness": 0}
    
    def get_action_replay(self, record_id: str) -> Dict:
        """Get detailed replay information for an action"""
        record = self.get_record(record_id)
        if not record:
            return {}
        
        return {
            "record": asdict(record),
            "metric_changes": self._calculate_metric_changes(record),
            "timeline": [
                {"time": record.started_at, "event": "started", "details": record.reasoning},
                {"time": record.completed_at, "event": "completed", "details": "success" if record.success else record.error_message}
            ],
            "similar_actions": [self.get_record(rid) for rid in record.similar_action_ids[:3] if self.get_record(rid)]
        }
    
    def _calculate_metric_changes(self, record: ActionRecord) -> List[Dict]:
        """Calculate changes in each metric"""
        changes = []
        
        all_metrics = set(record.pre_metrics.keys()) | set(record.post_metrics.keys())
        
        for metric in all_metrics:
            pre_val = record.pre_metrics.get(metric)
            post_val = record.post_metrics.get(metric)
            
            if pre_val is not None and post_val is not None:
                change = post_val - pre_val
                change_pct = (change / pre_val * 100) if pre_val != 0 else 0
                
                changes.append({
                    "metric": metric,
                    "before": pre_val,
                    "after": post_val,
                    "change": change,
                    "change_percent": change_pct,
                    "improved": (change < 0 if metric in ["error_rate", "cpu_usage", "latency_p99_ms"] else change > 0)
                })
        
        return changes
    
    def export_training_data(self, days: int = 30) -> List[Dict]:
        """Export action records for training/analysis"""
        export_data = []
        
        try:
            # Get recent dates
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            current = start_date
            while current <= end_date:
                date_key = current.strftime("%Y-%m-%d")
                record_ids = self.redis.lrange(f"action_records:by_date:{date_key}", 0, -1)
                
                for record_id in record_ids:
                    rid = record_id.decode() if isinstance(record_id, bytes) else record_id
                    record = self.get_record(rid)
                    if record:
                        export_data.append(asdict(record))
                
                current += timedelta(days=1)
        except:
            pass
        
        return export_data
    
    def get_stats_summary(self) -> Dict:
        """Get overall statistics summary"""
        try:
            success_count = self.redis.llen("action_records:by_status:success") or 0
            failure_count = self.redis.llen("action_records:by_status:failure") or 0
            total = success_count + failure_count
            
            return {
                "total_actions_recorded": total,
                "successes": success_count,
                "failures": failure_count,
                "success_rate": success_count / total if total > 0 else 0,
                "autonomous_actions": self._count_autonomous_actions(),
                "avg_execution_time_seconds": self._get_avg_execution_time()
            }
        except:
            return {"total_actions_recorded": 0}
    
    def _count_autonomous_actions(self) -> int:
        """Count autonomous actions"""
        # This would require additional indexing in a production system
        return 0
    
    def _get_avg_execution_time(self) -> float:
        """Get average execution time"""
        # Simplified - would need proper aggregation in production
        return 0.0


# Convenience function
def get_action_recorder(redis_client) -> ActionRecorder:
    """Get action recorder instance"""
    return ActionRecorder(redis_client)
