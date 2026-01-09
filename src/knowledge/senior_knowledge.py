"""
Senior Knowledge Replication
=============================
Encodes senior engineer operational wisdom into safe-action rules.
Enables autonomous remediation without senior approval for known-safe scenarios.

This module captures the judgment that senior engineers apply:
- When is an action safe to auto-execute?
- What conditions make an action risky?
- What guardrails should be enforced?
- What is the "common sense" of production operations?
"""

import json
from typing import Dict, List, Optional, Tuple, Callable, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("senior_knowledge")


class ActionSafetyLevel(Enum):
    """Safety classification for actions"""
    ALWAYS_SAFE = "always_safe"           # Can always auto-execute
    CONDITIONALLY_SAFE = "conditionally_safe"  # Safe if conditions met
    REQUIRES_REVIEW = "requires_review"   # Needs human review
    DANGEROUS = "dangerous"               # Never auto-execute
    FORBIDDEN = "forbidden"               # Block entirely


class ContextFactor(Enum):
    """Contextual factors affecting safety decisions"""
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    SERVICE_TIER = "service_tier"
    CURRENT_LOAD = "current_load"
    RECENT_INCIDENTS = "recent_incidents"
    DEPLOYMENT_ACTIVE = "deployment_active"
    MAINTENANCE_WINDOW = "maintenance_window"
    TEAM_CAPACITY = "team_capacity"


@dataclass
class SafetyRule:
    """A single safety rule encoding senior knowledge"""
    id: str
    name: str
    description: str
    
    # What this rule applies to
    action_types: List[str]  # Which action types
    services: List[str]  # Which services ("*" for all)
    
    # Safety classification
    safety_level: str  # ActionSafetyLevel
    
    # Conditions for conditional safety
    safe_conditions: List[Dict]
    unsafe_conditions: List[Dict]
    
    # Guardrails
    max_concurrent: int
    cooldown_seconds: int
    max_per_hour: int
    
    # Senior wisdom encoded
    rationale: str
    common_mistakes: List[str]
    what_to_check_first: List[str]
    when_to_escalate: List[str]
    
    # Metadata
    created_by: str
    approved_by: str
    last_reviewed: str


@dataclass
class SafetyDecision:
    """Result of safety evaluation"""
    action_type: str
    service: str
    is_safe: bool
    safety_level: str
    confidence: float
    
    rules_applied: List[str]
    conditions_checked: List[Dict]
    
    can_auto_execute: bool
    requires_approval: bool
    blocked: bool
    
    reasoning: str
    recommendations: List[str]
    escalation_path: Optional[str]


class SeniorKnowledgeEngine:
    """
    Encodes senior engineer operational wisdom for autonomous remediation.
    
    This is the "common sense" layer that knows:
    - A restart during peak hours is riskier than at 3am
    - Tier-1 services need more caution than Tier-4
    - Don't scale down during an active incident
    - Rollback is safe if deployment was < 15 minutes ago
    - etc.
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        
        # Load default rules
        self.rules: Dict[str, SafetyRule] = {}
        self._load_default_rules()
        
        # Service tier configuration
        self.service_tiers = self._initialize_service_tiers()
        
        # Context evaluators
        self.context_evaluators = self._initialize_context_evaluators()
        
        logger.info(f"[SENIOR] Loaded {len(self.rules)} safety rules")
    
    def _initialize_service_tiers(self) -> Dict[str, int]:
        """Initialize service tier mappings (1=most critical)"""
        return {
            # Tier 1 - Critical: Direct revenue/user impact
            "payment": 1, "checkout": 1, "auth": 1, "api-gateway": 1,
            "database-primary": 1, "user-auth": 1,
            
            # Tier 2 - Important: Core functionality
            "order": 2, "inventory": 2, "user-service": 2, "cart": 2,
            "redis-cluster": 2, "kafka-brokers": 2,
            
            # Tier 3 - Standard: Supporting services
            "notification": 3, "email": 3, "search": 3, "recommendation": 3,
            "analytics": 3, "logging": 3,
            
            # Tier 4 - Low: Non-critical
            "dev": 4, "staging": 4, "test": 4, "internal-tools": 4,
        }
    
    def _initialize_context_evaluators(self) -> Dict[str, Callable]:
        """Initialize context evaluation functions"""
        return {
            ContextFactor.TIME_OF_DAY.value: self._evaluate_time_of_day,
            ContextFactor.DAY_OF_WEEK.value: self._evaluate_day_of_week,
            ContextFactor.SERVICE_TIER.value: self._evaluate_service_tier,
            ContextFactor.CURRENT_LOAD.value: self._evaluate_current_load,
            ContextFactor.RECENT_INCIDENTS.value: self._evaluate_recent_incidents,
            ContextFactor.DEPLOYMENT_ACTIVE.value: self._evaluate_deployment_active,
        }
    
    def _load_default_rules(self):
        """Load default senior engineer safety rules"""
        
        default_rules = [
            # ===== RESTART RULES =====
            SafetyRule(
                id="restart_tier4_always",
                name="Restart Tier-4 Services",
                description="Tier-4 services can always be safely restarted",
                action_types=["restart_service", "rollout_restart"],
                services=["dev", "staging", "test", "internal-*"],
                safety_level=ActionSafetyLevel.ALWAYS_SAFE.value,
                safe_conditions=[],
                unsafe_conditions=[],
                max_concurrent=5,
                cooldown_seconds=60,
                max_per_hour=10,
                rationale="Non-production and internal tools have no user impact",
                common_mistakes=[],
                what_to_check_first=[],
                when_to_escalate=[],
                created_by="system",
                approved_by="system",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            SafetyRule(
                id="restart_offpeak_safe",
                name="Restart During Off-Peak",
                description="Restarts are safe during off-peak hours with healthy dependencies",
                action_types=["restart_service", "rollout_restart"],
                services=["*"],
                safety_level=ActionSafetyLevel.CONDITIONALLY_SAFE.value,
                safe_conditions=[
                    {"factor": "time_of_day", "value": "off_peak"},
                    {"factor": "dependencies_healthy", "value": True},
                    {"factor": "no_active_incidents", "value": True}
                ],
                unsafe_conditions=[
                    {"factor": "service_tier", "value": 1, "is_forbidden": True},
                    {"factor": "active_deployment", "value": True}
                ],
                max_concurrent=2,
                cooldown_seconds=300,
                max_per_hour=4,
                rationale="Off-peak hours minimize user impact, healthy deps ensure quick recovery",
                common_mistakes=[
                    "Restarting during deployment window",
                    "Restarting when dependencies are unhealthy"
                ],
                what_to_check_first=[
                    "Check if any deployments in progress",
                    "Verify dependency health",
                    "Check current error rate"
                ],
                when_to_escalate=[
                    "Service doesn't come back within 5 minutes",
                    "Error rate increases after restart",
                    "Multiple pods fail to start"
                ],
                created_by="senior_sre",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            # ===== SCALING RULES =====
            SafetyRule(
                id="scale_up_always_safe",
                name="Scale Up is Generally Safe",
                description="Scaling up adds capacity and rarely causes issues",
                action_types=["scale_up"],
                services=["*"],
                safety_level=ActionSafetyLevel.CONDITIONALLY_SAFE.value,
                safe_conditions=[
                    {"factor": "scale_factor", "max_value": 2},  # Max 2x
                    {"factor": "target_replicas", "max_value": 20}
                ],
                unsafe_conditions=[
                    {"factor": "scale_factor", "min_value": 3},  # >3x is risky
                    {"factor": "cost_impact", "value": "high"}
                ],
                max_concurrent=3,
                cooldown_seconds=120,
                max_per_hour=6,
                rationale="Scaling up is additive - worst case is cost, not outage",
                common_mistakes=[
                    "Scaling up without checking if problem is actually load",
                    "Scaling up during database connection exhaustion (makes it worse)"
                ],
                what_to_check_first=[
                    "Is this actually a load issue?",
                    "Are pods healthy after scaling?",
                    "Are there enough resources in cluster?"
                ],
                when_to_escalate=[
                    "New pods crash immediately",
                    "Scaling doesn't improve metrics",
                    "Database connections become exhausted"
                ],
                created_by="senior_sre",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            SafetyRule(
                id="scale_down_dangerous",
                name="Scale Down During Incident",
                description="Never scale down during an active incident",
                action_types=["scale_down"],
                services=["*"],
                safety_level=ActionSafetyLevel.DANGEROUS.value,
                safe_conditions=[],
                unsafe_conditions=[
                    {"factor": "active_incident", "value": True}
                ],
                max_concurrent=1,
                cooldown_seconds=600,
                max_per_hour=2,
                rationale="Scaling down removes capacity when you might need it",
                common_mistakes=[
                    "Scaling down because metrics 'look ok' during incident",
                    "Scaling down right after incident without buffer"
                ],
                what_to_check_first=[
                    "Confirm no active incidents",
                    "Check if load is genuinely low",
                    "Verify this won't impact upcoming traffic"
                ],
                when_to_escalate=[
                    "Any sign of service degradation after scale-down"
                ],
                created_by="senior_sre",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            # ===== ROLLBACK RULES =====
            SafetyRule(
                id="rollback_recent_deploy",
                name="Rollback Recent Deployment",
                description="Rollback is safe if deployment was within 15 minutes",
                action_types=["rollback", "rollback_deployment"],
                services=["*"],
                safety_level=ActionSafetyLevel.CONDITIONALLY_SAFE.value,
                safe_conditions=[
                    {"factor": "deployment_age_minutes", "max_value": 15},
                    {"factor": "previous_version_healthy", "value": True}
                ],
                unsafe_conditions=[
                    {"factor": "deployment_age_minutes", "min_value": 60},
                    {"factor": "database_migration", "value": True},
                    {"factor": "data_format_change", "value": True}
                ],
                max_concurrent=1,
                cooldown_seconds=300,
                max_per_hour=3,
                rationale="Recent deployments have low data divergence, rollback is usually safe",
                common_mistakes=[
                    "Rolling back after database migration",
                    "Rolling back when previous version has known issues",
                    "Rolling back without checking what changed"
                ],
                what_to_check_first=[
                    "Was there a database migration?",
                    "Is the previous version still safe?",
                    "How long has current version been running?"
                ],
                when_to_escalate=[
                    "Deployment included database changes",
                    "Previous version has known vulnerabilities",
                    "Rollback fails or causes errors"
                ],
                created_by="senior_sre",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            # ===== CACHE RULES =====
            SafetyRule(
                id="clear_cache_safe",
                name="Clear Cache is Safe with Warming",
                description="Cache clearing is safe if cache can be warmed or is non-critical",
                action_types=["clear_cache", "flush_cache"],
                services=["*"],
                safety_level=ActionSafetyLevel.CONDITIONALLY_SAFE.value,
                safe_conditions=[
                    {"factor": "cache_warming_enabled", "value": True},
                    {"factor": "off_peak", "value": True}
                ],
                unsafe_conditions=[
                    {"factor": "service_tier", "value": 1},
                    {"factor": "peak_hours", "value": True}
                ],
                max_concurrent=1,
                cooldown_seconds=600,
                max_per_hour=2,
                rationale="Cache clearing can cause load spike on backend",
                common_mistakes=[
                    "Clearing cache during peak traffic",
                    "Clearing cache without warming strategy"
                ],
                what_to_check_first=[
                    "Is there a cache warming process?",
                    "What's the current traffic level?",
                    "Can backend handle the load?"
                ],
                when_to_escalate=[
                    "Database load spikes after cache clear",
                    "Response times don't recover within 10 mins"
                ],
                created_by="senior_sre",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            # ===== CONNECTION RULES =====
            SafetyRule(
                id="kill_idle_connections_safe",
                name="Kill Idle Database Connections",
                description="Killing idle connections is safe for long-idle connections",
                action_types=["kill_connections", "terminate_connections"],
                services=["database-*", "postgresql-*", "mysql-*"],
                safety_level=ActionSafetyLevel.CONDITIONALLY_SAFE.value,
                safe_conditions=[
                    {"factor": "connection_idle_seconds", "min_value": 300}
                ],
                unsafe_conditions=[
                    {"factor": "connection_idle_seconds", "max_value": 60}
                ],
                max_concurrent=1,
                cooldown_seconds=120,
                max_per_hour=4,
                rationale="Long-idle connections are likely leaked, killing them is safe",
                common_mistakes=[
                    "Killing active connections",
                    "Killing connections during batch job window"
                ],
                what_to_check_first=[
                    "Are these genuinely idle connections?",
                    "Are any batch jobs running?"
                ],
                when_to_escalate=[
                    "Connection pool becomes fully depleted",
                    "Services start failing to connect"
                ],
                created_by="senior_dba",
                approved_by="platform_lead",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            # ===== NEVER AUTO-EXECUTE =====
            SafetyRule(
                id="database_failover_forbidden",
                name="Database Failover",
                description="Database failover must never be automated without human approval",
                action_types=["database_failover", "rds_failover", "db_promote"],
                services=["*"],
                safety_level=ActionSafetyLevel.FORBIDDEN.value,
                safe_conditions=[],
                unsafe_conditions=[],
                max_concurrent=1,
                cooldown_seconds=3600,
                max_per_hour=1,
                rationale="Database failover can cause data loss if not done carefully",
                common_mistakes=[
                    "Triggering failover without checking replication lag",
                    "Failover during high write load"
                ],
                what_to_check_first=[
                    "What is the replication lag?",
                    "Are there any long-running transactions?",
                    "Is the standby truly in sync?"
                ],
                when_to_escalate=["Always - this should never be automated"],
                created_by="senior_dba",
                approved_by="cto",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
            
            SafetyRule(
                id="data_deletion_forbidden",
                name="Data Deletion",
                description="Any action that deletes data is forbidden without approval",
                action_types=["delete_data", "truncate_table", "drop_*"],
                services=["*"],
                safety_level=ActionSafetyLevel.FORBIDDEN.value,
                safe_conditions=[],
                unsafe_conditions=[],
                max_concurrent=0,
                cooldown_seconds=86400,
                max_per_hour=0,
                rationale="Data deletion is irreversible",
                common_mistakes=["Deleting production data"],
                what_to_check_first=["Do NOT proceed without explicit approval"],
                when_to_escalate=["Always - never auto-execute"],
                created_by="senior_sre",
                approved_by="cto",
                last_reviewed=datetime.now(timezone.utc).isoformat()
            ),
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
    
    def evaluate_action_safety(
        self,
        action_type: str,
        service: str,
        context: Optional[Dict] = None
    ) -> SafetyDecision:
        """
        Evaluate whether an action is safe to auto-execute.
        
        This is the main entry point that encodes senior engineer judgment.
        
        Args:
            action_type: Type of action (restart, scale_up, rollback, etc.)
            service: Service to act on
            context: Optional context (current load, time, incidents, etc.)
        
        Returns:
            SafetyDecision with verdict and reasoning
        """
        
        context = context or {}
        rules_applied = []
        conditions_checked = []
        
        # Collect context
        context = self._enrich_context(context, service)
        
        # Find applicable rules
        applicable_rules = self._find_applicable_rules(action_type, service)
        
        if not applicable_rules:
            # No rules = conservative default
            return SafetyDecision(
                action_type=action_type,
                service=service,
                is_safe=False,
                safety_level=ActionSafetyLevel.REQUIRES_REVIEW.value,
                confidence=50,
                rules_applied=[],
                conditions_checked=[],
                can_auto_execute=False,
                requires_approval=True,
                blocked=False,
                reasoning="No safety rules defined for this action/service combination",
                recommendations=["Define safety rules for this action type"],
                escalation_path="oncall_engineer"
            )
        
        # Check each rule
        final_safety_level = ActionSafetyLevel.ALWAYS_SAFE
        final_blocked = False
        all_reasoning = []
        all_recommendations = []
        
        for rule in applicable_rules:
            rules_applied.append(rule.id)
            rule_safety = ActionSafetyLevel(rule.safety_level)
            
            # Check if rule blocks this action
            if rule_safety == ActionSafetyLevel.FORBIDDEN:
                final_blocked = True
                final_safety_level = ActionSafetyLevel.FORBIDDEN
                all_reasoning.append(f"BLOCKED by rule '{rule.name}': {rule.rationale}")
                all_recommendations.extend(rule.when_to_escalate)
                continue
            
            # Check safe conditions
            safe_conditions_met = True
            for condition in rule.safe_conditions:
                result = self._check_condition(condition, context)
                conditions_checked.append({
                    "rule": rule.id,
                    "condition": condition,
                    "result": result
                })
                if not result:
                    safe_conditions_met = False
            
            # Check unsafe conditions
            unsafe_conditions_met = False
            for condition in rule.unsafe_conditions:
                result = self._check_condition(condition, context)
                conditions_checked.append({
                    "rule": rule.id,
                    "condition": condition,
                    "result": result,
                    "is_unsafe": True
                })
                if result:
                    unsafe_conditions_met = True
                    all_reasoning.append(f"Unsafe condition met: {condition}")
            
            # Determine final safety for this rule
            if rule_safety == ActionSafetyLevel.ALWAYS_SAFE:
                # Always safe, no conditions needed
                pass
            elif rule_safety == ActionSafetyLevel.CONDITIONALLY_SAFE:
                if unsafe_conditions_met:
                    final_safety_level = max(
                        final_safety_level,
                        ActionSafetyLevel.DANGEROUS,
                        key=lambda x: list(ActionSafetyLevel).index(x)
                    )
                elif not safe_conditions_met:
                    final_safety_level = max(
                        final_safety_level,
                        ActionSafetyLevel.REQUIRES_REVIEW,
                        key=lambda x: list(ActionSafetyLevel).index(x)
                    )
            else:
                final_safety_level = max(
                    final_safety_level,
                    rule_safety,
                    key=lambda x: list(ActionSafetyLevel).index(x)
                )
            
            all_recommendations.extend(rule.what_to_check_first)
        
        # Build final decision
        can_auto_execute = final_safety_level in [
            ActionSafetyLevel.ALWAYS_SAFE,
            ActionSafetyLevel.CONDITIONALLY_SAFE
        ] and not final_blocked
        
        requires_approval = final_safety_level in [
            ActionSafetyLevel.REQUIRES_REVIEW,
            ActionSafetyLevel.DANGEROUS
        ]
        
        # Calculate confidence based on how many conditions were checked
        confidence = 80 if can_auto_execute else 60
        if len(conditions_checked) > 3:
            confidence += 10  # More thorough check = higher confidence
        
        # Build reasoning
        if not all_reasoning:
            if can_auto_execute:
                all_reasoning.append("All safety conditions met - safe for autonomous execution")
            else:
                all_reasoning.append("Safety conditions not fully satisfied")
        
        return SafetyDecision(
            action_type=action_type,
            service=service,
            is_safe=can_auto_execute,
            safety_level=final_safety_level.value,
            confidence=confidence,
            rules_applied=rules_applied,
            conditions_checked=conditions_checked,
            can_auto_execute=can_auto_execute,
            requires_approval=requires_approval,
            blocked=final_blocked,
            reasoning=" | ".join(all_reasoning),
            recommendations=list(set(all_recommendations))[:5],
            escalation_path="senior_engineer" if final_blocked else ("oncall" if requires_approval else None)
        )
    
    def _find_applicable_rules(self, action_type: str, service: str) -> List[SafetyRule]:
        """Find rules that apply to this action/service combination"""
        
        applicable = []
        
        for rule in self.rules.values():
            # Check action type match
            action_match = False
            for rule_action in rule.action_types:
                if rule_action == "*" or action_type.startswith(rule_action.replace("*", "")):
                    action_match = True
                    break
                if action_type == rule_action:
                    action_match = True
                    break
            
            if not action_match:
                continue
            
            # Check service match
            service_match = False
            for rule_service in rule.services:
                if rule_service == "*":
                    service_match = True
                    break
                if rule_service.endswith("*"):
                    if service.startswith(rule_service[:-1]):
                        service_match = True
                        break
                elif service == rule_service:
                    service_match = True
                    break
            
            if service_match:
                applicable.append(rule)
        
        return applicable
    
    def _enrich_context(self, context: Dict, service: str) -> Dict:
        """Enrich context with evaluated factors"""
        
        enriched = dict(context)
        
        # Add time context
        now = datetime.now(timezone.utc)
        enriched["current_hour"] = now.hour
        enriched["current_day"] = now.weekday()
        enriched["is_weekend"] = now.weekday() >= 5
        enriched["is_off_peak"] = now.hour < 8 or now.hour > 22
        enriched["is_peak"] = 9 <= now.hour <= 17 and now.weekday() < 5
        
        # Add service tier
        service_lower = service.lower()
        tier = 2  # Default
        for pattern, t in self.service_tiers.items():
            if pattern in service_lower:
                tier = t
                break
        enriched["service_tier"] = tier
        
        # Add other enrichments from Redis if available
        if self.redis:
            try:
                # Check for active incidents
                incidents = self.redis.lrange(f"active_incidents:{service}", 0, 5)
                enriched["active_incidents"] = len(incidents) > 0
                enriched["incident_count"] = len(incidents)
                
                # Check for recent deployment
                deploy_time = self.redis.get(f"last_deployment:{service}")
                if deploy_time:
                    deploy_ts = float(deploy_time)
                    age_minutes = (datetime.now(timezone.utc).timestamp() - deploy_ts) / 60
                    enriched["deployment_age_minutes"] = age_minutes
                    enriched["recent_deployment"] = age_minutes < 15
            except Exception:
                pass
        
        return enriched
    
    def _check_condition(self, condition: Dict, context: Dict) -> bool:
        """Check if a condition is met given the context"""
        
        factor = condition.get("factor")
        value = condition.get("value")
        min_value = condition.get("min_value")
        max_value = condition.get("max_value")
        
        context_value = context.get(factor)
        
        if context_value is None:
            return False  # Unknown = don't match
        
        # Exact match
        if value is not None:
            return context_value == value
        
        # Range match
        if min_value is not None and max_value is not None:
            return min_value <= context_value <= max_value
        
        if min_value is not None:
            return context_value >= min_value
        
        if max_value is not None:
            return context_value <= max_value
        
        return False
    
    def _evaluate_time_of_day(self, context: Dict) -> str:
        """Evaluate time of day safety"""
        hour = datetime.now(timezone.utc).hour
        if hour < 8 or hour > 22:
            return "off_peak"
        elif 9 <= hour <= 17:
            return "peak"
        else:
            return "normal"
    
    def _evaluate_day_of_week(self, context: Dict) -> str:
        """Evaluate day of week safety"""
        day = datetime.now(timezone.utc).weekday()
        if day >= 5:
            return "weekend"
        elif day == 4 and datetime.now(timezone.utc).hour >= 14:
            return "friday_afternoon"
        else:
            return "weekday"
    
    def _evaluate_service_tier(self, service: str) -> int:
        """Get service tier (1=most critical)"""
        for pattern, tier in self.service_tiers.items():
            if pattern in service.lower():
                return tier
        return 2  # Default tier
    
    def _evaluate_current_load(self, context: Dict) -> str:
        """Evaluate current system load"""
        cpu = context.get("cpu_usage", 50)
        if cpu > 80:
            return "high"
        elif cpu > 50:
            return "medium"
        else:
            return "low"
    
    def _evaluate_recent_incidents(self, context: Dict) -> bool:
        """Check for recent incidents"""
        return context.get("incident_count", 0) > 0
    
    def _evaluate_deployment_active(self, context: Dict) -> bool:
        """Check if deployment is active"""
        return context.get("recent_deployment", False)
    
    def add_rule(self, rule: SafetyRule):
        """Add a new safety rule"""
        self.rules[rule.id] = rule
        
        # Persist to Redis if available
        if self.redis:
            self.redis.set(
                f"safety_rule:{rule.id}",
                json.dumps(asdict(rule))
            )
        
        logger.info(f"[SENIOR] Added rule: {rule.name}")
    
    def get_rule(self, rule_id: str) -> Optional[SafetyRule]:
        """Get a rule by ID"""
        return self.rules.get(rule_id)
    
    def list_rules(self) -> List[Dict]:
        """List all safety rules"""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "safety_level": rule.safety_level,
                "actions": rule.action_types,
                "services": rule.services
            }
            for rule in self.rules.values()
        ]
    
    def get_wisdom_for_action(self, action_type: str) -> Dict:
        """Get senior engineer wisdom for an action type"""
        
        applicable_rules = [
            r for r in self.rules.values()
            if action_type in r.action_types or "*" in r.action_types
        ]
        
        if not applicable_rules:
            return {"message": "No specific wisdom encoded for this action"}
        
        return {
            "action_type": action_type,
            "rules_count": len(applicable_rules),
            "common_mistakes": list(set(
                mistake
                for r in applicable_rules
                for mistake in r.common_mistakes
            )),
            "what_to_check_first": list(set(
                check
                for r in applicable_rules
                for check in r.what_to_check_first
            )),
            "when_to_escalate": list(set(
                escalate
                for r in applicable_rules
                for escalate in r.when_to_escalate
            )),
            "rationale": [r.rationale for r in applicable_rules]
        }


# Convenience function
def is_action_safe(
    redis_client,
    action_type: str,
    service: str,
    context: Optional[Dict] = None
) -> Tuple[bool, str]:
    """Quick check if an action is safe"""
    engine = SeniorKnowledgeEngine(redis_client)
    decision = engine.evaluate_action_safety(action_type, service, context)
    return decision.can_auto_execute, decision.reasoning
