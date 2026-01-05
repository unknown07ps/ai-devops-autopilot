"""
Alert Noise Suppression
========================
Intelligently suppresses low-value alerts based on context and historical outcomes.
Triages alerts to escalate only actionable incidents.

This module reduces alert fatigue by:
- Deduplicating similar alerts
- Detecting flapping patterns
- Learning from historical outcomes
- Evaluating actionability scores
- Grouping related alerts
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert_suppression")


class AlertDisposition(Enum):
    """What to do with an alert"""
    ESCALATE = "escalate"         # High priority, create incident
    PAGE = "page"                 # Page on-call immediately
    NOTIFY = "notify"             # Slack/email notification
    AGGREGATE = "aggregate"       # Group with related alerts
    SUPPRESS = "suppress"         # Drop, don't notify anyone
    DEFER = "defer"               # Wait for more data
    LOG_ONLY = "log_only"         # Log but don't alert


class SuppressionReason(Enum):
    """Reasons for suppressing an alert"""
    DUPLICATE = "duplicate"
    FLAPPING = "flapping"
    LOW_ACTIONABILITY = "low_actionability"
    KNOWN_ISSUE = "known_issue"
    MAINTENANCE_WINDOW = "maintenance_window"
    AUTO_RESOLVED = "auto_resolved"
    EXPECTED_BEHAVIOR = "expected_behavior"
    LOW_IMPACT = "low_impact"


@dataclass
class AlertFingerprint:
    """Unique fingerprint for deduplication"""
    fingerprint: str
    alert_name: str
    service: str
    labels_hash: str


@dataclass
class AlertContext:
    """Context for evaluating an alert"""
    service: str
    alert_name: str
    severity: str
    labels: Dict
    value: float
    threshold: float
    message: str
    source: str
    timestamp: str


@dataclass
class TriageDecision:
    """Result of alert triage"""
    alert_id: str
    disposition: str
    actionability_score: float
    
    # Suppression info
    suppressed: bool
    suppression_reason: Optional[str]
    
    # Grouping info
    grouped_with: List[str]
    is_group_leader: bool
    
    # Context
    similar_alerts_24h: int
    historical_action_rate: float
    flapping_detected: bool
    
    # Recommendation
    recommended_action: Optional[str]
    escalation_delay_seconds: int
    
    # Reasoning
    reasoning: str


@dataclass
class AlertGroup:
    """A group of related alerts"""
    group_id: str
    leader_alert_id: str
    alert_ids: List[str]
    service: str
    severity: str
    created_at: str
    last_updated: str
    alert_count: int
    consolidated_message: str


class AlertNoiseSuppressor:
    """
    Intelligent alert noise suppression and triage.
    
    Features:
    - Deduplication by fingerprint
    - Flapping detection
    - Actionability scoring
    - Historical outcome learning
    - Alert grouping/aggregation
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
        # Configuration
        self.dedup_window_seconds = 300  # 5 minutes
        self.flap_threshold = 5  # Changes in 10 minutes = flapping
        self.flap_window_seconds = 600
        self.min_actionability_score = 40  # Below this = suppress
        self.group_window_seconds = 60  # Group alerts within 1 minute
        
        # Severity weights
        self.severity_scores = {
            "critical": 100,
            "high": 75,
            "warning": 50,
            "low": 25,
            "info": 10
        }
        
        # Alert patterns that are often non-actionable
        self.low_value_patterns = [
            "disk space warning",
            "cpu spike",
            "memory warning",
            "connection timeout",
            "retry succeeded"
        ]
        
        # Alerts to never suppress
        self.never_suppress = [
            "security",
            "data loss",
            "corruption",
            "breach",
            "pii",
            "payment failure",
            "database down"
        ]
        
        # In-memory tracking
        self.recent_alerts: Dict[str, List[float]] = defaultdict(list)
        self.alert_groups: Dict[str, AlertGroup] = {}
        
        # Historical outcomes
        self.alert_outcomes: Dict[str, Dict] = {}
        self._load_outcomes()
        
        logger.info("[SUPPRESS] Alert Noise Suppressor initialized")
    
    def _load_outcomes(self):
        """Load historical alert outcomes"""
        try:
            data = self.redis.get("alert_outcomes")
            if data:
                self.alert_outcomes = json.loads(data)
        except:
            pass
    
    def _save_outcomes(self):
        """Save historical alert outcomes"""
        try:
            self.redis.set("alert_outcomes", json.dumps(self.alert_outcomes))
        except:
            pass
    
    def triage_alert(self, alert: AlertContext) -> TriageDecision:
        """
        Triage an alert and determine its disposition.
        
        Returns:
            TriageDecision with disposition and reasoning
        """
        
        alert_id = self._generate_alert_id(alert)
        fingerprint = self._generate_fingerprint(alert)
        now = datetime.now(timezone.utc)
        
        # Check if this should never be suppressed
        if self._is_critical_alert(alert):
            return self._create_decision(
                alert_id, AlertDisposition.PAGE,
                actionability=100,
                reasoning="Critical alert pattern - immediate escalation"
            )
        
        # Check for duplicate
        is_dup, dup_reason = self._check_duplicate(fingerprint)
        if is_dup:
            return self._create_decision(
                alert_id, AlertDisposition.SUPPRESS,
                actionability=0,
                suppressed=True,
                suppression_reason=SuppressionReason.DUPLICATE.value,
                reasoning=dup_reason
            )
        
        # Check for flapping
        is_flapping = self._check_flapping(fingerprint)
        if is_flapping:
            return self._create_decision(
                alert_id, AlertDisposition.AGGREGATE,
                actionability=30,
                suppressed=True,
                suppression_reason=SuppressionReason.FLAPPING.value,
                flapping_detected=True,
                reasoning="Alert is flapping - aggregating instead of escalating"
            )
        
        # Check maintenance window
        if self._in_maintenance_window(alert.service):
            return self._create_decision(
                alert_id, AlertDisposition.LOG_ONLY,
                actionability=20,
                suppressed=True,
                suppression_reason=SuppressionReason.MAINTENANCE_WINDOW.value,
                reasoning="Service is in maintenance window"
            )
        
        # Calculate actionability score
        actionability = self._calculate_actionability(alert, fingerprint)
        
        # Check historical outcomes
        hist_action_rate = self._get_historical_action_rate(fingerprint)
        if hist_action_rate < 0.1 and actionability < 50:
            return self._create_decision(
                alert_id, AlertDisposition.SUPPRESS,
                actionability=actionability,
                suppressed=True,
                suppression_reason=SuppressionReason.LOW_ACTIONABILITY.value,
                historical_action_rate=hist_action_rate,
                reasoning=f"Low historical action rate ({hist_action_rate:.0%}) - suppressing"
            )
        
        # Check if low-value pattern
        if self._is_low_value_pattern(alert):
            if actionability < self.min_actionability_score:
                return self._create_decision(
                    alert_id, AlertDisposition.SUPPRESS,
                    actionability=actionability,
                    suppressed=True,
                    suppression_reason=SuppressionReason.LOW_ACTIONABILITY.value,
                    reasoning="Matches low-value alert pattern"
                )
        
        # Try to group with related alerts
        group_id = self._try_group_alert(alert_id, alert)
        if group_id:
            return self._create_decision(
                alert_id, AlertDisposition.AGGREGATE,
                actionability=actionability,
                grouped_with=[group_id],
                reasoning="Grouped with related alerts"
            )
        
        # Determine final disposition based on severity and actionability
        disposition = self._determine_disposition(alert, actionability)
        
        # Record this alert for future dedup
        self._record_alert(fingerprint, now)
        
        # Get similar alerts count
        similar_count = self._count_similar_alerts_24h(fingerprint)
        
        return self._create_decision(
            alert_id, disposition,
            actionability=actionability,
            similar_alerts_24h=similar_count,
            historical_action_rate=hist_action_rate,
            recommended_action=self._get_recommended_action(alert),
            reasoning=f"Actionability score {actionability:.0f}% - {disposition.value}"
        )
    
    def _generate_alert_id(self, alert: AlertContext) -> str:
        """Generate unique alert ID"""
        return f"alert_{alert.service}_{int(datetime.now(timezone.utc).timestamp())}"
    
    def _generate_fingerprint(self, alert: AlertContext) -> str:
        """Generate deduplication fingerprint"""
        fp_data = f"{alert.service}:{alert.alert_name}:{json.dumps(alert.labels, sort_keys=True)}"
        return hashlib.md5(fp_data.encode()).hexdigest()[:12]
    
    def _is_critical_alert(self, alert: AlertContext) -> bool:
        """Check if alert should never be suppressed"""
        message_lower = alert.message.lower()
        name_lower = alert.alert_name.lower()
        
        for pattern in self.never_suppress:
            if pattern in message_lower or pattern in name_lower:
                return True
        
        return alert.severity == "critical"
    
    def _check_duplicate(self, fingerprint: str) -> Tuple[bool, str]:
        """Check if this is a duplicate alert"""
        
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - self.dedup_window_seconds
        
        # Get recent alerts with this fingerprint
        if fingerprint in self.recent_alerts:
            recent = [t for t in self.recent_alerts[fingerprint] if t > cutoff]
            if recent:
                age = now - max(recent)
                return True, f"Duplicate alert (seen {age:.0f}s ago)"
        
        return False, ""
    
    def _check_flapping(self, fingerprint: str) -> bool:
        """Check if alert is flapping (rapid on/off)"""
        
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - self.flap_window_seconds
        
        if fingerprint in self.recent_alerts:
            recent = [t for t in self.recent_alerts[fingerprint] if t > cutoff]
            if len(recent) >= self.flap_threshold:
                return True
        
        return False
    
    def _in_maintenance_window(self, service: str) -> bool:
        """Check if service is in maintenance window"""
        
        try:
            window = self.redis.get(f"maintenance:{service}")
            if window:
                end_time = float(window)
                return datetime.now(timezone.utc).timestamp() < end_time
        except:
            pass
        
        return False
    
    def _calculate_actionability(self, alert: AlertContext, fingerprint: str) -> float:
        """
        Calculate actionability score (0-100).
        
        Higher = more likely to require action
        """
        
        score = 50.0  # Base score
        
        # Severity contribution
        severity_score = self.severity_scores.get(alert.severity, 25)
        score += (severity_score - 50) * 0.3
        
        # Threshold breach magnitude
        if alert.threshold > 0 and alert.value > 0:
            breach_ratio = alert.value / alert.threshold
            if breach_ratio > 2:
                score += 20  # Way over threshold
            elif breach_ratio > 1.5:
                score += 10
            elif breach_ratio < 1.1:
                score -= 15  # Barely over threshold
        
        # Historical action rate
        action_rate = self._get_historical_action_rate(fingerprint)
        if action_rate > 0.7:
            score += 20  # High historical action rate
        elif action_rate < 0.2 and action_rate > 0:
            score -= 20  # Low historical action rate
        
        # Service criticality (would integrate with production model)
        if any(critical in alert.service.lower() for critical in ["payment", "auth", "database"]):
            score += 15
        
        # Time of day (business hours = more actionable)
        hour = datetime.now(timezone.utc).hour
        if 9 <= hour <= 17:
            score += 5
        else:
            score -= 5
        
        return max(0, min(100, score))
    
    def _get_historical_action_rate(self, fingerprint: str) -> float:
        """Get historical rate at which this alert type led to action"""
        
        if fingerprint in self.alert_outcomes:
            outcomes = self.alert_outcomes[fingerprint]
            total = outcomes.get("total", 0)
            actioned = outcomes.get("actioned", 0)
            if total > 10:  # Need enough samples
                return actioned / total
        
        return 0.5  # Default - unknown
    
    def _is_low_value_pattern(self, alert: AlertContext) -> bool:
        """Check if alert matches low-value patterns"""
        
        message_lower = alert.message.lower()
        name_lower = alert.alert_name.lower()
        
        for pattern in self.low_value_patterns:
            if pattern in message_lower or pattern in name_lower:
                return True
        
        return False
    
    def _try_group_alert(self, alert_id: str, alert: AlertContext) -> Optional[str]:
        """Try to add alert to an existing group"""
        
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(seconds=self.group_window_seconds)).isoformat()
        
        # Look for existing group for this service/severity
        for group in self.alert_groups.values():
            if (group.service == alert.service and 
                group.severity == alert.severity and
                group.created_at > cutoff):
                # Add to group
                group.alert_ids.append(alert_id)
                group.alert_count += 1
                group.last_updated = now.isoformat()
                self._save_group(group)
                return group.group_id
        
        return None
    
    def _determine_disposition(
        self,
        alert: AlertContext,
        actionability: float
    ) -> AlertDisposition:
        """Determine final disposition based on all factors"""
        
        if alert.severity == "critical" or actionability >= 90:
            return AlertDisposition.PAGE
        elif alert.severity == "high" or actionability >= 70:
            return AlertDisposition.ESCALATE
        elif actionability >= 50:
            return AlertDisposition.NOTIFY
        elif actionability >= 30:
            return AlertDisposition.DEFER
        else:
            return AlertDisposition.LOG_ONLY
    
    def _record_alert(self, fingerprint: str, timestamp: datetime):
        """Record alert for deduplication and flapping detection"""
        
        ts = timestamp.timestamp()
        self.recent_alerts[fingerprint].append(ts)
        
        # Prune old entries
        cutoff = ts - self.flap_window_seconds * 2
        self.recent_alerts[fingerprint] = [
            t for t in self.recent_alerts[fingerprint] if t > cutoff
        ]
    
    def _count_similar_alerts_24h(self, fingerprint: str) -> int:
        """Count similar alerts in last 24 hours"""
        
        try:
            count = self.redis.get(f"alert_count_24h:{fingerprint}")
            return int(count) if count else 0
        except:
            return 0
    
    def _get_recommended_action(self, alert: AlertContext) -> Optional[str]:
        """Get recommended action for this alert type"""
        
        name_lower = alert.alert_name.lower()
        
        if "memory" in name_lower:
            return "Consider restarting the service or scaling up"
        elif "cpu" in name_lower:
            return "Check for runaway processes or scale up"
        elif "latency" in name_lower:
            return "Check dependencies and database performance"
        elif "error rate" in name_lower:
            return "Check recent deployments and logs"
        elif "disk" in name_lower:
            return "Clean up old logs or scale storage"
        
        return None
    
    def _create_decision(
        self,
        alert_id: str,
        disposition: AlertDisposition,
        actionability: float = 0,
        suppressed: bool = False,
        suppression_reason: str = None,
        grouped_with: List[str] = None,
        similar_alerts_24h: int = 0,
        historical_action_rate: float = 0.5,
        flapping_detected: bool = False,
        recommended_action: str = None,
        reasoning: str = ""
    ) -> TriageDecision:
        """Create a triage decision"""
        
        # Calculate escalation delay based on severity/actionability
        if disposition == AlertDisposition.PAGE:
            delay = 0
        elif disposition == AlertDisposition.ESCALATE:
            delay = 60
        elif disposition == AlertDisposition.NOTIFY:
            delay = 300
        else:
            delay = 600
        
        return TriageDecision(
            alert_id=alert_id,
            disposition=disposition.value,
            actionability_score=actionability,
            suppressed=suppressed,
            suppression_reason=suppression_reason,
            grouped_with=grouped_with or [],
            is_group_leader=False,
            similar_alerts_24h=similar_alerts_24h,
            historical_action_rate=historical_action_rate,
            flapping_detected=flapping_detected,
            recommended_action=recommended_action,
            escalation_delay_seconds=delay,
            reasoning=reasoning
        )
    
    def _save_group(self, group: AlertGroup):
        """Save alert group to Redis"""
        try:
            self.redis.setex(
                f"alert_group:{group.group_id}",
                3600,  # 1 hour
                json.dumps(asdict(group))
            )
        except:
            pass
    
    def record_outcome(
        self,
        fingerprint: str,
        was_actioned: bool,
        action_taken: str = None
    ):
        """Record outcome of an alert for learning"""
        
        if fingerprint not in self.alert_outcomes:
            self.alert_outcomes[fingerprint] = {
                "total": 0,
                "actioned": 0,
                "actions": {}
            }
        
        self.alert_outcomes[fingerprint]["total"] += 1
        if was_actioned:
            self.alert_outcomes[fingerprint]["actioned"] += 1
            if action_taken:
                actions = self.alert_outcomes[fingerprint]["actions"]
                actions[action_taken] = actions.get(action_taken, 0) + 1
        
        self._save_outcomes()
        logger.info(f"[SUPPRESS] Recorded outcome for {fingerprint}: actioned={was_actioned}")
    
    def set_maintenance_window(
        self,
        service: str,
        duration_minutes: int
    ):
        """Set maintenance window for a service"""
        
        end_time = (
            datetime.now(timezone.utc) + 
            timedelta(minutes=duration_minutes)
        ).timestamp()
        
        self.redis.setex(
            f"maintenance:{service}",
            duration_minutes * 60,
            str(end_time)
        )
        
        logger.info(f"[SUPPRESS] Maintenance window set for {service}: {duration_minutes}min")
    
    def get_suppression_stats(self) -> Dict:
        """Get suppression statistics"""
        
        try:
            stats_data = self.redis.get("suppression_stats")
            stats = json.loads(stats_data) if stats_data else {}
        except:
            stats = {}
        
        # Calculate outcome rates
        total_alerts = sum(o.get("total", 0) for o in self.alert_outcomes.values())
        total_actioned = sum(o.get("actioned", 0) for o in self.alert_outcomes.values())
        
        return {
            "total_alerts_evaluated": total_alerts,
            "total_actioned": total_actioned,
            "action_rate": total_actioned / total_alerts if total_alerts > 0 else 0,
            "unique_fingerprints": len(self.alert_outcomes),
            "active_groups": len(self.alert_groups),
            "low_value_patterns": self.low_value_patterns,
            "never_suppress_patterns": self.never_suppress
        }


# Convenience function
def triage_alert(
    redis_client,
    service: str,
    alert_name: str,
    severity: str,
    message: str,
    value: float = 0,
    threshold: float = 0,
    labels: Dict = None
) -> TriageDecision:
    """Quick function to triage an alert"""
    
    suppressor = AlertNoiseSuppressor(redis_client)
    
    alert = AlertContext(
        service=service,
        alert_name=alert_name,
        severity=severity,
        labels=labels or {},
        value=value,
        threshold=threshold,
        message=message,
        source="prometheus",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    return suppressor.triage_alert(alert)
