"""
Repeat Incident Eliminator
==========================
Detects recurring incidents and automatically applies preventive measures
to eliminate repeat occurrences. Tracks patterns, counts recurrences, and
enforces permanent fixes when thresholds are exceeded.
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repeat_eliminator")


@dataclass
class IncidentPattern:
    """Represents a recurring incident pattern"""
    pattern_id: str
    service: str
    root_cause_hash: str
    symptom_signature: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    successful_fixes: List[Dict]
    failed_fixes: List[Dict]
    permanent_fix_applied: bool
    permanent_fix_details: Optional[Dict]
    escalated: bool


@dataclass 
class PreventiveMeasure:
    """Represents a preventive measure to apply"""
    action_type: str
    params: Dict
    confidence: float
    based_on_incidents: int
    estimated_effectiveness: float


class RepeatIncidentEliminator:
    """
    Tracks recurring incidents and automatically applies preventive measures.
    
    Features:
    - Pattern fingerprinting for incident matching
    - Configurable recurrence thresholds
    - Automatic preventive action application
    - Permanent fix registry
    - Escalation on repeated failures
    """
    
    def __init__(self, redis_client, action_executor=None, production_executor=None):
        self.redis = redis_client
        self.action_executor = action_executor
        self.production_executor = production_executor
        
        # Configuration
        self.recurrence_threshold = 3  # Apply preventive after N occurrences
        self.escalation_threshold = 5  # Escalate if fix doesn't work after N more
        self.pattern_ttl_days = 90  # Keep patterns for 90 days
        self.lookback_window_hours = 24  # Consider incidents within this window as related
        
        # Preventive action mappings
        self.preventive_actions = {
            "latency_spike": [
                PreventiveMeasure("scale_up", {"target_replicas": 6}, 85, 0, 0.8),
                PreventiveMeasure("update_resources", {"cpu_limit": "2000m", "memory_limit": "4Gi"}, 75, 0, 0.7),
            ],
            "memory_issue": [
                PreventiveMeasure("restart_service", {}, 90, 0, 0.85),
                PreventiveMeasure("update_resources", {"memory_limit": "8Gi"}, 80, 0, 0.75),
            ],
            "error_rate_spike": [
                PreventiveMeasure("rollback", {}, 85, 0, 0.8),
                PreventiveMeasure("scale_up", {"target_replicas": 4}, 70, 0, 0.6),
            ],
            "cpu_issue": [
                PreventiveMeasure("scale_up", {"target_replicas": 5}, 80, 0, 0.75),
                PreventiveMeasure("update_resources", {"cpu_limit": "4000m"}, 85, 0, 0.8),
            ],
            "connection_exhaustion": [
                PreventiveMeasure("kill_connections", {"idle_seconds": 300}, 90, 0, 0.9),
                PreventiveMeasure("restart_service", {}, 75, 0, 0.7),
            ],
            "pod_crash": [
                PreventiveMeasure("update_resources", {"memory_limit": "4Gi"}, 85, 0, 0.8),
                PreventiveMeasure("restart_service", {}, 70, 0, 0.65),
            ],
        }
        
        logger.info("[ELIMINATOR] Repeat Incident Eliminator initialized")
    
    def generate_pattern_fingerprint(
        self,
        service: str,
        root_cause: Dict,
        symptoms: Dict
    ) -> str:
        """Generate a unique fingerprint for an incident pattern"""
        
        # Create consistent hash from key attributes
        fingerprint_data = {
            "service": service,
            "root_cause_type": root_cause.get("cause", root_cause.get("description", "unknown")),
            "latency_spike": symptoms.get("latency_spike", False),
            "error_rate_spike": symptoms.get("error_rate_spike", False),
            "memory_issue": symptoms.get("memory_issue", False),
            "cpu_issue": symptoms.get("cpu_issue", False),
        }
        
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    
    def record_incident_occurrence(
        self,
        incident_id: str,
        service: str,
        root_cause: Dict,
        symptoms: Dict,
        actions_taken: List[Dict],
        was_successful: bool
    ) -> Tuple[int, bool]:
        """
        Record an incident occurrence and check if preventive action needed.
        
        Returns:
            Tuple of (occurrence_count, should_apply_preventive)
        """
        pattern_id = self.generate_pattern_fingerprint(service, root_cause, symptoms)
        pattern_key = f"repeat_pattern:{pattern_id}"
        
        # Get or create pattern
        pattern_data = self.redis.get(pattern_key)
        
        if pattern_data:
            pattern = IncidentPattern(**json.loads(pattern_data))
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.now(timezone.utc).isoformat()
            
            if was_successful:
                pattern.successful_fixes.append({
                    "incident_id": incident_id,
                    "actions": actions_taken,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                pattern.failed_fixes.append({
                    "incident_id": incident_id,
                    "actions": actions_taken,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        else:
            pattern = IncidentPattern(
                pattern_id=pattern_id,
                service=service,
                root_cause_hash=hashlib.sha256(
                    json.dumps(root_cause, sort_keys=True).encode()
                ).hexdigest()[:16],
                symptom_signature=json.dumps(symptoms, sort_keys=True),
                occurrence_count=1,
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                successful_fixes=[{
                    "incident_id": incident_id,
                    "actions": actions_taken,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }] if was_successful else [],
                failed_fixes=[{
                    "incident_id": incident_id,
                    "actions": actions_taken,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }] if not was_successful else [],
                permanent_fix_applied=False,
                permanent_fix_details=None,
                escalated=False
            )
        
        # Save pattern
        self.redis.setex(
            pattern_key,
            self.pattern_ttl_days * 86400,
            json.dumps(asdict(pattern))
        )
        
        # Index by service
        self.redis.sadd(f"repeat_patterns:{service}", pattern_id)
        
        # Check if we should apply preventive measures
        should_prevent = (
            pattern.occurrence_count >= self.recurrence_threshold and
            not pattern.permanent_fix_applied
        )
        
        logger.info(
            f"[ELIMINATOR] Pattern {pattern_id}: occurrence #{pattern.occurrence_count} "
            f"(threshold: {self.recurrence_threshold}, prevent: {should_prevent})"
        )
        
        return pattern.occurrence_count, should_prevent
    
    async def apply_preventive_measures(
        self,
        service: str,
        root_cause: Dict,
        symptoms: Dict
    ) -> Dict:
        """
        Automatically apply preventive measures for recurring incidents.
        
        Returns:
            Dict with applied measures and results
        """
        pattern_id = self.generate_pattern_fingerprint(service, root_cause, symptoms)
        pattern_key = f"repeat_pattern:{pattern_id}"
        
        # Get pattern data
        pattern_data = self.redis.get(pattern_key)
        if not pattern_data:
            return {"success": False, "error": "Pattern not found"}
        
        pattern = IncidentPattern(**json.loads(pattern_data))
        
        # Don't re-apply if already applied
        if pattern.permanent_fix_applied:
            return {
                "success": True,
                "message": "Permanent fix already applied",
                "fix_details": pattern.permanent_fix_details
            }
        
        # Determine which symptom type to address
        symptoms_parsed = json.loads(pattern.symptom_signature)
        symptom_type = self._identify_primary_symptom(symptoms_parsed)
        
        # Get best preventive action based on past successes
        preventive = self._select_best_preventive(pattern, symptom_type)
        
        if not preventive:
            return {
                "success": False,
                "error": f"No preventive measure available for {symptom_type}"
            }
        
        logger.info(
            f"[ELIMINATOR] Applying preventive measure for {service}: "
            f"{preventive.action_type} (confidence: {preventive.confidence}%)"
        )
        
        # Execute the preventive action
        result = await self._execute_preventive(service, preventive)
        
        if result.get("success"):
            # Record permanent fix
            pattern.permanent_fix_applied = True
            pattern.permanent_fix_details = {
                "action_type": preventive.action_type,
                "params": preventive.params,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "after_occurrences": pattern.occurrence_count,
                "result": result
            }
            
            # Save updated pattern
            self.redis.setex(
                pattern_key,
                self.pattern_ttl_days * 86400,
                json.dumps(asdict(pattern))
            )
            
            # Record in permanent fix registry
            self._record_permanent_fix(service, pattern, preventive, result)
            
            logger.info(f"[ELIMINATOR] ✓ Permanent fix applied for pattern {pattern_id}")
        else:
            # Check if need to escalate
            if pattern.occurrence_count >= self.escalation_threshold and not pattern.escalated:
                await self._escalate_incident(service, pattern)
                pattern.escalated = True
                self.redis.setex(
                    pattern_key,
                    self.pattern_ttl_days * 86400,
                    json.dumps(asdict(pattern))
                )
        
        return {
            "success": result.get("success", False),
            "pattern_id": pattern_id,
            "occurrence_count": pattern.occurrence_count,
            "action_applied": preventive.action_type,
            "result": result
        }
    
    def _identify_primary_symptom(self, symptoms: Dict) -> str:
        """Identify the primary symptom type from symptoms dict"""
        
        if symptoms.get("memory_issue"):
            return "memory_issue"
        if symptoms.get("latency_spike"):
            return "latency_spike"
        if symptoms.get("error_rate_spike"):
            return "error_rate_spike"
        if symptoms.get("cpu_issue"):
            return "cpu_issue"
        
        return "latency_spike"  # Default
    
    def _select_best_preventive(
        self,
        pattern: IncidentPattern,
        symptom_type: str
    ) -> Optional[PreventiveMeasure]:
        """Select the best preventive measure based on pattern history"""
        
        available = self.preventive_actions.get(symptom_type, [])
        if not available:
            return None
        
        # Check what worked in past fixes for this pattern
        successful_action_types = set()
        for fix in pattern.successful_fixes:
            for action in fix.get("actions", []):
                successful_action_types.add(action.get("action_type"))
        
        # Prefer actions that worked before
        for measure in available:
            if measure.action_type in successful_action_types:
                measure.based_on_incidents = len(pattern.successful_fixes)
                measure.confidence = min(measure.confidence + 10, 100)
                return measure
        
        # Fall back to highest confidence
        return available[0] if available else None
    
    async def _execute_preventive(
        self,
        service: str,
        preventive: PreventiveMeasure
    ) -> Dict:
        """Execute a preventive measure"""
        
        # Use production executor if available
        if self.production_executor:
            return await self.production_executor.execute_action(
                preventive.action_type,
                service,
                preventive.params
            )
        
        # Use action executor if available
        if self.action_executor:
            from src.actions.action_executor import ActionType
            
            action_type_map = {
                "scale_up": ActionType.SCALE_UP,
                "scale_down": ActionType.SCALE_DOWN,
                "restart_service": ActionType.RESTART_SERVICE,
                "rollback": ActionType.ROLLBACK,
                "clear_cache": ActionType.CLEAR_CACHE,
                "kill_connections": ActionType.KILL_CONNECTIONS,
            }
            
            action_type = action_type_map.get(preventive.action_type)
            if action_type:
                action = await self.action_executor.propose_action(
                    action_type=action_type,
                    service=service,
                    params=preventive.params,
                    reasoning=f"Preventive measure for recurring incident (confidence: {preventive.confidence}%)",
                    risk="low",
                    incident_id=f"preventive_{datetime.now(timezone.utc).timestamp()}"
                )
                
                # Auto-approve preventive actions
                await self.action_executor.approve_action(action["id"], "repeat_eliminator")
                return {"success": True, "action_id": action["id"]}
        
        # Dry run if no executor available
        return {
            "success": True,
            "dry_run": True,
            "message": f"Would apply {preventive.action_type} to {service}"
        }
    
    def _record_permanent_fix(
        self,
        service: str,
        pattern: IncidentPattern,
        preventive: PreventiveMeasure,
        result: Dict
    ):
        """Record a permanent fix in the registry"""
        
        fix_record = {
            "pattern_id": pattern.pattern_id,
            "service": service,
            "action_type": preventive.action_type,
            "params": preventive.params,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "after_occurrences": pattern.occurrence_count,
            "confidence": preventive.confidence,
            "first_incident": pattern.first_seen,
            "result": result
        }
        
        # Store in permanent fix registry
        self.redis.lpush("permanent_fixes", json.dumps(fix_record))
        self.redis.lpush(f"permanent_fixes:{service}", json.dumps(fix_record))
        
        # Keep registry bounded
        self.redis.ltrim("permanent_fixes", 0, 999)
        self.redis.ltrim(f"permanent_fixes:{service}", 0, 99)
        
        logger.info(f"[ELIMINATOR] Recorded permanent fix: {preventive.action_type} for {service}")
    
    async def _escalate_incident(self, service: str, pattern: IncidentPattern):
        """Escalate a recurring incident that can't be automatically fixed"""
        
        escalation = {
            "type": "repeat_incident_escalation",
            "service": service,
            "pattern_id": pattern.pattern_id,
            "occurrence_count": pattern.occurrence_count,
            "first_seen": pattern.first_seen,
            "last_seen": pattern.last_seen,
            "failed_fixes": len(pattern.failed_fixes),
            "successful_fixes": len(pattern.successful_fixes),
            "escalated_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Recurring incident on {service} after {pattern.occurrence_count} occurrences - manual intervention required"
        }
        
        # Store escalation
        self.redis.lpush("escalations", json.dumps(escalation))
        self.redis.lpush(f"escalations:{service}", json.dumps(escalation))
        
        logger.warning(
            f"[ELIMINATOR] ⚠️ ESCALATED: Pattern {pattern.pattern_id} on {service} "
            f"- {pattern.occurrence_count} occurrences, {len(pattern.failed_fixes)} failed fixes"
        )
    
    def get_repeat_patterns(self, service: Optional[str] = None) -> List[Dict]:
        """Get all tracked repeat incident patterns"""
        
        if service:
            pattern_ids = self.redis.smembers(f"repeat_patterns:{service}")
        else:
            # Get all patterns across services
            pattern_ids = set()
            for key in self.redis.scan_iter("repeat_patterns:*"):
                pattern_ids.update(self.redis.smembers(key))
        
        patterns = []
        for pattern_id in pattern_ids:
            if isinstance(pattern_id, bytes):
                pattern_id = pattern_id.decode('utf-8')
            
            pattern_data = self.redis.get(f"repeat_pattern:{pattern_id}")
            if pattern_data:
                patterns.append(json.loads(pattern_data))
        
        # Sort by occurrence count
        patterns.sort(key=lambda x: x.get("occurrence_count", 0), reverse=True)
        return patterns
    
    def get_permanent_fixes(self, service: Optional[str] = None) -> List[Dict]:
        """Get all permanent fixes applied"""
        
        key = f"permanent_fixes:{service}" if service else "permanent_fixes"
        fixes_data = self.redis.lrange(key, 0, 99)
        
        return [json.loads(fix) for fix in fixes_data]
    
    def get_stats(self) -> Dict:
        """Get repeat incident elimination statistics"""
        
        patterns = self.get_repeat_patterns()
        permanent_fixes = self.get_permanent_fixes()
        
        total_patterns = len(patterns)
        fixed_patterns = sum(1 for p in patterns if p.get("permanent_fix_applied"))
        escalated_patterns = sum(1 for p in patterns if p.get("escalated"))
        
        total_occurrences = sum(p.get("occurrence_count", 0) for p in patterns)
        prevented_estimate = sum(
            p.get("occurrence_count", 0) 
            for p in patterns 
            if p.get("permanent_fix_applied")
        )
        
        return {
            "total_patterns_tracked": total_patterns,
            "patterns_with_permanent_fix": fixed_patterns,
            "patterns_escalated": escalated_patterns,
            "total_incident_occurrences": total_occurrences,
            "estimated_incidents_prevented": prevented_estimate,
            "permanent_fixes_applied": len(permanent_fixes),
            "recurrence_threshold": self.recurrence_threshold,
            "escalation_threshold": self.escalation_threshold,
            "effectiveness_rate": (fixed_patterns / total_patterns * 100) if total_patterns > 0 else 0
        }


# Convenience function for integration
async def check_and_prevent_repeat_incident(
    redis_client,
    incident_id: str,
    service: str,
    root_cause: Dict,
    symptoms: Dict,
    actions_taken: List[Dict],
    was_successful: bool,
    action_executor=None,
    production_executor=None
) -> Dict:
    """
    Convenience function to check for repeat incidents and apply preventive measures.
    Call this after every incident resolution.
    """
    eliminator = RepeatIncidentEliminator(
        redis_client,
        action_executor,
        production_executor
    )
    
    # Record occurrence
    count, should_prevent = eliminator.record_incident_occurrence(
        incident_id, service, root_cause, symptoms, actions_taken, was_successful
    )
    
    result = {
        "pattern_occurrence": count,
        "threshold": eliminator.recurrence_threshold,
        "preventive_applied": False
    }
    
    # Apply preventive if threshold exceeded
    if should_prevent:
        prevention_result = await eliminator.apply_preventive_measures(
            service, root_cause, symptoms
        )
        result["preventive_applied"] = prevention_result.get("success", False)
        result["preventive_details"] = prevention_result
    
    return result
