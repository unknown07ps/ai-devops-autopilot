"""
Decision Logger - Explainable AI for Autonomous Mode
Logs every decision with detailed reasoning, making the AI's thinking transparent
Stores decision trails for audit, review, and learning
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid


class DecisionType(str, Enum):
    """Types of decisions the system can make"""
    ACTION_APPROVED = "action_approved"
    ACTION_DENIED = "action_denied"
    ACTION_DEFERRED = "action_deferred"
    PATTERN_MATCHED = "pattern_matched"
    CONFIDENCE_CALCULATED = "confidence_calculated"
    SAFETY_CHECK = "safety_check"
    ESCALATION = "escalation"
    LEARNING_UPDATE = "learning_update"


class ConfidenceSource(str, Enum):
    """Sources that contribute to confidence"""
    RULE_BASED = "rule_based"
    AI_ANALYSIS = "ai_analysis"
    HISTORICAL = "historical"
    PATTERN_MATCH = "pattern_match"
    LEARNING_ENGINE = "learning_engine"


@dataclass
class ConfidenceContribution:
    """A single contribution to the confidence score"""
    source: str
    value: float
    weight: float
    weighted_value: float
    reasoning: str
    factors: List[str] = field(default_factory=list)


@dataclass
class DecisionLog:
    """Complete log of a decision with full reasoning trail"""
    decision_id: str
    timestamp: str
    decision_type: str
    
    # Context
    incident_id: str
    service: str
    action_type: str
    
    # Decision
    decision: str  # approved/denied/deferred
    final_confidence: float
    confidence_threshold: float
    
    # Reasoning breakdown
    reasoning_summary: str
    confidence_contributions: List[Dict]
    
    # Factors considered
    factors_for: List[str] = field(default_factory=list)      # Reasons to approve
    factors_against: List[str] = field(default_factory=list)  # Reasons to deny
    safety_checks: List[Dict] = field(default_factory=list)
    
    # Pattern information
    matched_pattern: Optional[str] = None
    pattern_confidence: float = 0.0
    similar_incidents_count: int = 0
    historical_success_rate: float = 0.0
    
    # Execution context
    execution_mode: str = ""
    was_autonomous: bool = False
    required_approval: bool = False
    
    # Learning feedback (filled after execution)
    outcome: Optional[str] = None
    outcome_recorded_at: Optional[str] = None
    
    def to_human_readable(self) -> str:
        """Generate human-readable explanation of the decision"""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append(f"🤖 AUTONOMOUS DECISION LOG")
        lines.append("=" * 70)
        lines.append(f"Decision ID: {self.decision_id}")
        lines.append(f"Time: {self.timestamp}")
        lines.append(f"Service: {self.service}")
        lines.append(f"Action: {self.action_type}")
        lines.append("")
        
        # Decision
        decision_emoji = "✅" if self.decision == "approved" else "❌" if self.decision == "denied" else "⏸️"
        lines.append(f"{decision_emoji} DECISION: {self.decision.upper()}")
        lines.append(f"   Confidence: {self.final_confidence:.1f}% (threshold: {self.confidence_threshold}%)")
        lines.append("")
        
        # Reasoning summary
        lines.append("📋 REASONING:")
        lines.append(f"   {self.reasoning_summary}")
        lines.append("")
        
        # Confidence breakdown
        lines.append("📊 CONFIDENCE BREAKDOWN:")
        for contrib in self.confidence_contributions:
            source = contrib.get('source', 'unknown')
            value = contrib.get('value', 0)
            weight = contrib.get('weight', 0)
            weighted = contrib.get('weighted_value', 0)
            reason = contrib.get('reasoning', '')
            
            lines.append(f"   • {source}: {value:.1f}% × {weight:.0%} = {weighted:.1f}%")
            if reason:
                lines.append(f"     └─ {reason}")
            
            for factor in contrib.get('factors', []):
                lines.append(f"        • {factor}")
        lines.append("")
        
        # Pattern match
        if self.matched_pattern:
            lines.append("🎯 PATTERN MATCHED:")
            lines.append(f"   Pattern: {self.matched_pattern}")
            lines.append(f"   Pattern Confidence: {self.pattern_confidence:.1f}%")
            lines.append(f"   Similar Past Incidents: {self.similar_incidents_count}")
            lines.append(f"   Historical Success Rate: {self.historical_success_rate:.1%}")
            lines.append("")
        
        # Factors
        if self.factors_for:
            lines.append("✓ FACTORS SUPPORTING ACTION:")
            for factor in self.factors_for:
                lines.append(f"   + {factor}")
            lines.append("")
        
        if self.factors_against:
            lines.append("✗ FACTORS AGAINST ACTION:")
            for factor in self.factors_against:
                lines.append(f"   - {factor}")
            lines.append("")
        
        # Safety checks
        if self.safety_checks:
            lines.append("🛡️ SAFETY CHECKS:")
            for check in self.safety_checks:
                status = "✓" if check.get('passed') else "✗"
                lines.append(f"   {status} {check.get('name')}: {check.get('result')}")
            lines.append("")
        
        # Execution context
        lines.append("⚙️ EXECUTION CONTEXT:")
        lines.append(f"   Mode: {self.execution_mode}")
        lines.append(f"   Autonomous: {'Yes' if self.was_autonomous else 'No'}")
        lines.append(f"   Required Approval: {'Yes' if self.required_approval else 'No'}")
        
        if self.outcome:
            lines.append("")
            lines.append("📈 OUTCOME:")
            lines.append(f"   Result: {self.outcome}")
            lines.append(f"   Recorded: {self.outcome_recorded_at}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


class DecisionLogger:
    """
    Logs and explains all autonomous decisions
    Provides full transparency into AI reasoning
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.max_logs_per_service = 1000
        self.max_global_logs = 10000
    
    def log_decision(
        self,
        incident: Dict,
        action: Dict,
        decision: str,
        confidence: float,
        confidence_breakdown: Dict,
        execution_mode: str,
        safety_checks: List[Dict] = None,
        pattern_info: Dict = None,
        similar_incidents: List[Dict] = None
    ) -> DecisionLog:
        """
        Log a decision with full reasoning trail
        
        Args:
            incident: The incident being addressed
            action: The proposed action
            decision: "approved", "denied", or "deferred"
            confidence: Final confidence score (0-100)
            confidence_breakdown: Dict with rule_conf, ai_conf, historical_conf, etc.
            execution_mode: Current execution mode
            safety_checks: List of safety check results
            pattern_info: Matched pattern information
            similar_incidents: List of similar past incidents
        """
        
        # Build confidence contributions
        contributions = self._build_confidence_contributions(confidence_breakdown)
        
        # Build factors for/against
        factors_for, factors_against = self._analyze_factors(
            incident, action, confidence_breakdown, safety_checks
        )
        
        # Build reasoning summary
        reasoning = self._build_reasoning_summary(
            decision, confidence, factors_for, factors_against, pattern_info
        )
        
        # Create decision log
        log = DecisionLog(
            decision_id=str(uuid.uuid4())[:16],
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_type=DecisionType.ACTION_APPROVED.value if decision == "approved" 
                         else DecisionType.ACTION_DENIED.value,
            incident_id=incident.get('id', 'unknown'),
            service=action.get('service', 'unknown'),
            action_type=action.get('action_type', 'unknown'),
            decision=decision,
            final_confidence=confidence,
            confidence_threshold=75,  # Default, can be passed in
            reasoning_summary=reasoning,
            confidence_contributions=[asdict(c) if hasattr(c, '__dict__') else c for c in contributions],
            factors_for=factors_for,
            factors_against=factors_against,
            safety_checks=safety_checks or [],
            matched_pattern=pattern_info.get('pattern_name') if pattern_info else None,
            pattern_confidence=pattern_info.get('confidence', 0) if pattern_info else 0,
            similar_incidents_count=len(similar_incidents) if similar_incidents else 0,
            historical_success_rate=self._calc_historical_rate(similar_incidents),
            execution_mode=execution_mode,
            was_autonomous=(decision == "approved"),
            required_approval=(decision != "approved")
        )
        
        # Store the log
        self._store_log(log)
        
        # Print human-readable version
        print(log.to_human_readable())
        
        return log
    
    def _build_confidence_contributions(self, breakdown: Dict) -> List[ConfidenceContribution]:
        """Build detailed confidence contributions from breakdown"""
        contributions = []
        
        # Rule-based
        if 'rule_confidence' in breakdown:
            rule_conf = breakdown['rule_confidence']
            rule_weight = breakdown.get('rule_weight', 0.35)
            
            rule_factors = []
            if breakdown.get('risk_level') == 'low':
                rule_factors.append("Low risk action (+20 confidence)")
            if breakdown.get('recent_deployment'):
                rule_factors.append("Recent deployment detected - rollback applicable (+25)")
            if breakdown.get('latency_issue'):
                rule_factors.append("Latency spike detected - scale up applicable (+15)")
            if breakdown.get('memory_issue'):
                rule_factors.append("Memory issue detected - restart applicable (+15)")
            if breakdown.get('critical_severity'):
                rule_factors.append("Critical severity incident (+10)")
            
            contributions.append(ConfidenceContribution(
                source="Rule-Based Analysis",
                value=rule_conf,
                weight=rule_weight,
                weighted_value=rule_conf * rule_weight,
                reasoning="Deterministic rules based on incident type and action risk",
                factors=rule_factors
            ))
        
        # AI Analysis
        if 'ai_confidence' in breakdown:
            ai_conf = breakdown['ai_confidence']
            ai_weight = breakdown.get('ai_weight', 0.35)
            
            ai_factors = []
            if breakdown.get('ai_recommended'):
                ai_factors.append("Action was recommended by AI analysis")
            if breakdown.get('ai_priority'):
                ai_factors.append(f"AI priority: {breakdown['ai_priority']} (higher = more urgent)")
            if breakdown.get('root_cause_identified'):
                ai_factors.append(f"Root cause identified: {breakdown.get('root_cause', 'unknown')}")
            
            contributions.append(ConfidenceContribution(
                source="AI Analysis",
                value=ai_conf,
                weight=ai_weight,
                weighted_value=ai_conf * ai_weight,
                reasoning="LLM-based root cause analysis and action recommendation",
                factors=ai_factors
            ))
        
        # Historical
        if 'historical_confidence' in breakdown:
            hist_conf = breakdown['historical_confidence']
            hist_weight = breakdown.get('historical_weight', 0.15)
            
            hist_factors = []
            similar_count = breakdown.get('similar_incidents_count', 0)
            if similar_count > 0:
                hist_factors.append(f"Found {similar_count} similar past incidents")
                hist_factors.append(f"Success rate with this action: {breakdown.get('success_rate', 0):.0%}")
            else:
                hist_factors.append("No similar incidents found - using neutral baseline")
            
            contributions.append(ConfidenceContribution(
                source="Historical Analysis",
                value=hist_conf,
                weight=hist_weight,
                weighted_value=hist_conf * hist_weight,
                reasoning="Based on outcomes of similar past incidents",
                factors=hist_factors
            ))
        
        # Pattern-based (from learning engine)
        if 'pattern_confidence' in breakdown:
            pattern_conf = breakdown['pattern_confidence']
            pattern_weight = breakdown.get('pattern_weight', 0.15)
            
            pattern_factors = []
            if breakdown.get('pattern_name'):
                pattern_factors.append(f"Matched pattern: {breakdown['pattern_name']}")
            if breakdown.get('pattern_autonomous_safe'):
                pattern_factors.append("Pattern is marked autonomous-safe")
            if breakdown.get('pattern_promoted'):
                pattern_factors.append("Pattern promoted based on learning history")
            
            contributions.append(ConfidenceContribution(
                source="Pattern Matching (Knowledge Base)",
                value=pattern_conf,
                weight=pattern_weight,
                weighted_value=pattern_conf * pattern_weight,
                reasoning="Based on 580+ DevOps patterns in knowledge base",
                factors=pattern_factors
            ))
        
        return contributions
    
    def _analyze_factors(
        self,
        incident: Dict,
        action: Dict,
        breakdown: Dict,
        safety_checks: List[Dict]
    ) -> tuple:
        """Analyze factors for and against the action"""
        factors_for = []
        factors_against = []
        
        # Confidence factors
        if breakdown.get('rule_confidence', 0) >= 70:
            factors_for.append("High rule-based confidence indicates clear action path")
        
        if breakdown.get('ai_confidence', 0) >= 75:
            factors_for.append("AI analysis strongly recommends this action")
        elif breakdown.get('ai_confidence', 0) < 50:
            factors_against.append("AI analysis has low confidence in this action")
        
        if breakdown.get('historical_confidence', 0) >= 80:
            factors_for.append("This action has high historical success rate")
        elif breakdown.get('historical_confidence', 0) < 40:
            factors_against.append("Limited or poor historical performance with this action")
        
        # Pattern factors
        if breakdown.get('pattern_autonomous_safe'):
            factors_for.append("Pattern is trusted for autonomous execution")
        
        if breakdown.get('pattern_promoted'):
            factors_for.append("Pattern has been promoted through successful executions")
        
        if breakdown.get('pattern_demoted'):
            factors_against.append("Pattern has been demoted due to failures - requires review")
        
        # Safety factors
        if safety_checks:
            failed_checks = [c for c in safety_checks if not c.get('passed')]
            if failed_checks:
                for check in failed_checks:
                    factors_against.append(f"Safety check failed: {check.get('name')}")
            else:
                factors_for.append("All safety checks passed")
        
        # Incident factors
        severity = incident.get('severity', 'medium')
        if severity == 'critical':
            factors_for.append("Critical incident - faster action preferred")
        
        # Action risk factors
        risk = action.get('risk', 'medium')
        if risk == 'low':
            factors_for.append("Low-risk action with minimal blast radius")
        elif risk == 'high':
            factors_against.append("High-risk action - caution required")
        
        return factors_for, factors_against
    
    def _build_reasoning_summary(
        self,
        decision: str,
        confidence: float,
        factors_for: List[str],
        factors_against: List[str],
        pattern_info: Dict
    ) -> str:
        """Build a human-readable reasoning summary"""
        
        if decision == "approved":
            summary = f"Action APPROVED for autonomous execution. "
            summary += f"Confidence of {confidence:.1f}% exceeds threshold. "
            
            if factors_for:
                summary += f"Key supporting factors: {factors_for[0]}"
                if len(factors_for) > 1:
                    summary += f" and {len(factors_for)-1} more."
            
            if pattern_info and pattern_info.get('pattern_name'):
                summary += f" Matched known pattern: {pattern_info['pattern_name']}."
                
        elif decision == "denied":
            summary = f"Action DENIED for autonomous execution. "
            summary += f"Confidence of {confidence:.1f}% below threshold. "
            
            if factors_against:
                summary += f"Key concerns: {factors_against[0]}"
                if len(factors_against) > 1:
                    summary += f" and {len(factors_against)-1} more."
                    
        else:  # deferred
            summary = f"Action DEFERRED for manual review. "
            summary += f"Confidence of {confidence:.1f}% is borderline. "
            summary += "Human judgment recommended for this decision."
        
        return summary
    
    def _calc_historical_rate(self, similar_incidents: Optional[List[Dict]]) -> float:
        """Calculate historical success rate from similar incidents"""
        if not similar_incidents:
            return 0.0
        
        successful = sum(1 for inc in similar_incidents if inc.get('was_successful'))
        return successful / len(similar_incidents) if similar_incidents else 0.0
    
    def _store_log(self, log: DecisionLog):
        """Store decision log in Redis"""
        try:
            log_json = json.dumps(asdict(log))
            
            # Store in service-specific list
            service_key = f"decision_logs:{log.service}"
            self.redis.lpush(service_key, log_json)
            self.redis.ltrim(service_key, 0, self.max_logs_per_service - 1)
            
            # Store in global timeline
            self.redis.lpush("decision_logs:timeline", log_json)
            self.redis.ltrim("decision_logs:timeline", 0, self.max_global_logs - 1)
            
            # Store by decision ID for quick lookup
            self.redis.set(f"decision_log:{log.decision_id}", log_json)
            self.redis.expire(f"decision_log:{log.decision_id}", 86400 * 30)  # 30 days
            
        except Exception as e:
            print(f"Error storing decision log: {e}")
    
    def get_decision(self, decision_id: str) -> Optional[DecisionLog]:
        """Retrieve a decision by ID"""
        try:
            data = self.redis.get(f"decision_log:{decision_id}")
            if data:
                return DecisionLog(**json.loads(data))
        except Exception as e:
            print(f"Error retrieving decision: {e}")
        return None
    
    def get_recent_decisions(self, service: str = None, limit: int = 50) -> List[DecisionLog]:
        """Get recent decisions, optionally filtered by service"""
        try:
            if service:
                key = f"decision_logs:{service}"
            else:
                key = "decision_logs:timeline"
            
            logs_json = self.redis.lrange(key, 0, limit - 1)
            return [DecisionLog(**json.loads(log)) for log in logs_json]
        except Exception as e:
            print(f"Error getting recent decisions: {e}")
            return []
    
    def get_decision_stats(self, service: str = None) -> Dict:
        """Get statistics about decisions"""
        decisions = self.get_recent_decisions(service, limit=100)
        
        if not decisions:
            return {"total": 0}
        
        approved = sum(1 for d in decisions if d.decision == "approved")
        denied = sum(1 for d in decisions if d.decision == "denied")
        deferred = sum(1 for d in decisions if d.decision == "deferred")
        
        avg_confidence = sum(d.final_confidence for d in decisions) / len(decisions)
        
        return {
            "total": len(decisions),
            "approved": approved,
            "denied": denied,
            "deferred": deferred,
            "approval_rate": approved / len(decisions) if decisions else 0,
            "average_confidence": avg_confidence,
            "by_action_type": self._group_by_action(decisions)
        }
    
    def _group_by_action(self, decisions: List[DecisionLog]) -> Dict:
        """Group decisions by action type"""
        by_action = {}
        for d in decisions:
            if d.action_type not in by_action:
                by_action[d.action_type] = {"total": 0, "approved": 0}
            by_action[d.action_type]["total"] += 1
            if d.decision == "approved":
                by_action[d.action_type]["approved"] += 1
        return by_action
    
    def record_outcome(self, decision_id: str, outcome: str):
        """Record the outcome of a decision for learning"""
        try:
            log = self.get_decision(decision_id)
            if log:
                log.outcome = outcome
                log.outcome_recorded_at = datetime.now(timezone.utc).isoformat()
                
                # Update stored log
                self.redis.set(
                    f"decision_log:{decision_id}",
                    json.dumps(asdict(log))
                )
                
                print(f"[DECISION LOG] Recorded outcome for {decision_id}: {outcome}")
        except Exception as e:
            print(f"Error recording outcome: {e}")
