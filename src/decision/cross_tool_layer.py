"""
Cross-Tool Decision Layer
==========================
Centralized AI decision layer that reasons across multiple DevOps tools
(metrics, logs, alerts, deploy history, traces) to produce unified
operational decisions.

This acts as the "brain" sitting above all monitoring and observability tools.
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decision_layer")


class SignalType(Enum):
    """Types of signals from monitoring tools"""
    METRIC = "metric"
    LOG = "log"
    ALERT = "alert"
    TRACE = "trace"
    DEPLOYMENT = "deployment"
    INCIDENT = "incident"
    HEALTH_CHECK = "health_check"
    SECURITY_EVENT = "security_event"


class SignalSource(Enum):
    """Source monitoring tools"""
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    DATADOG = "datadog"
    PAGERDUTY = "pagerduty"
    CLOUDWATCH = "cloudwatch"
    ELASTICSEARCH = "elasticsearch"
    JAEGER = "jaeger"
    KUBERNETES = "kubernetes"
    ARGOCD = "argocd"
    JENKINS = "jenkins"
    INTERNAL = "internal"
    

class DecisionType(Enum):
    """Types of operational decisions"""
    NO_ACTION = "no_action"
    INVESTIGATE = "investigate"
    AUTO_REMEDIATE = "auto_remediate"
    MANUAL_APPROVAL = "manual_approval"
    ESCALATE = "escalate"
    ROLLBACK = "rollback"
    SCALE = "scale"
    RESTART = "restart"
    PAGE_ONCALL = "page_oncall"


@dataclass
class Signal:
    """A signal from any monitoring tool"""
    id: str
    type: str  # SignalType
    source: str  # SignalSource
    service: str
    timestamp: str
    severity: str  # low, medium, high, critical
    message: str
    data: Dict
    correlation_id: Optional[str] = None
    

@dataclass
class CorrelatedEvent:
    """A group of correlated signals forming a single event"""
    event_id: str
    signals: List[Dict]
    services_affected: List[str]
    primary_service: str
    severity: str
    correlation_score: float
    first_signal_at: str
    last_signal_at: str
    signal_types: List[str]
    signal_sources: List[str]


@dataclass
class UnifiedDecision:
    """A single operational decision from cross-tool reasoning"""
    decision_id: str
    decision_type: str
    confidence: float
    
    # Context
    correlated_event: Dict
    signals_analyzed: int
    services_affected: List[str]
    
    # Decision details
    primary_action: str
    action_params: Dict
    fallback_actions: List[Dict]
    
    # Reasoning
    reasoning: str
    contributing_factors: List[str]
    risk_assessment: str
    
    # Execution
    requires_approval: bool
    auto_executable: bool
    estimated_impact: str
    estimated_resolution_time: str
    
    # Metadata
    decided_at: str
    expires_at: str


class CrossToolDecisionLayer:
    """
    Centralized AI decision layer that:
    1. Ingests signals from multiple DevOps tools
    2. Correlates related signals across tools and services
    3. Produces unified operational decisions
    4. Orchestrates remediation across tools
    
    This is the "brain" that sits above individual monitoring tools.
    """
    
    def __init__(self, redis_client, llm_client=None):
        self.redis = redis_client
        self.llm_client = llm_client  # Optional AI for complex decisions
        
        # Configuration
        self.correlation_window_seconds = 300  # 5 minutes
        self.min_correlation_score = 0.6
        self.decision_ttl_minutes = 30
        
        # Signal weights for correlation
        self.signal_weights = {
            SignalType.ALERT.value: 1.0,
            SignalType.INCIDENT.value: 1.0,
            SignalType.METRIC.value: 0.8,
            SignalType.DEPLOYMENT.value: 0.9,
            SignalType.LOG.value: 0.6,
            SignalType.TRACE.value: 0.7,
            SignalType.HEALTH_CHECK.value: 0.8,
            SignalType.SECURITY_EVENT.value: 1.0,
        }
        
        # Decision rules (can be extended with ML)
        self.decision_rules = self._initialize_decision_rules()
        
        # Pending signals buffer
        self.signal_buffer: List[Signal] = []
        
        logger.info("[DECISION] Cross-Tool Decision Layer initialized")
    
    def _initialize_decision_rules(self) -> List[Dict]:
        """Initialize decision rules for common scenarios"""
        
        return [
            {
                "name": "deployment_correlation_rollback",
                "condition": lambda signals, event: (
                    any(s["type"] == "deployment" for s in signals) and
                    any(s["type"] in ["alert", "metric"] and s["severity"] in ["high", "critical"] for s in signals)
                ),
                "decision_type": DecisionType.ROLLBACK,
                "confidence_boost": 20,
                "reasoning": "Deployment correlates with high-severity alerts",
            },
            {
                "name": "multi_service_cascade",
                "condition": lambda signals, event: len(event.services_affected) >= 3,
                "decision_type": DecisionType.ESCALATE,
                "confidence_boost": 15,
                "reasoning": "Multiple services affected - potential cascade failure",
            },
            {
                "name": "latency_scale_pattern",
                "condition": lambda signals, event: (
                    any("latency" in s.get("message", "").lower() for s in signals) and
                    any(s["type"] == "metric" for s in signals)
                ),
                "decision_type": DecisionType.SCALE,
                "confidence_boost": 10,
                "reasoning": "Latency issues detected - scaling may help",
            },
            {
                "name": "memory_restart_pattern",
                "condition": lambda signals, event: (
                    any("memory" in s.get("message", "").lower() or "oom" in s.get("message", "").lower() for s in signals)
                ),
                "decision_type": DecisionType.RESTART,
                "confidence_boost": 15,
                "reasoning": "Memory pressure detected - restart may release resources",
            },
            {
                "name": "security_event_escalate",
                "condition": lambda signals, event: (
                    any(s["type"] == "security_event" for s in signals)
                ),
                "decision_type": DecisionType.ESCALATE,
                "confidence_boost": 25,
                "reasoning": "Security event requires immediate attention",
            },
            {
                "name": "single_low_severity",
                "condition": lambda signals, event: (
                    len(signals) == 1 and
                    signals[0].get("severity") == "low"
                ),
                "decision_type": DecisionType.INVESTIGATE,
                "confidence_boost": 0,
                "reasoning": "Single low-severity signal - investigate but no immediate action",
            },
        ]
    
    async def ingest_signal(self, signal: Signal) -> None:
        """
        Ingest a signal from any monitoring tool.
        Signals are buffered and correlated periodically.
        """
        
        # Store signal
        signal_key = f"signal:{signal.id}"
        self.redis.setex(
            signal_key,
            self.correlation_window_seconds * 2,
            json.dumps(asdict(signal))
        )
        
        # Add to service signal stream
        self.redis.lpush(f"signals:{signal.service}", signal.id)
        self.redis.ltrim(f"signals:{signal.service}", 0, 99)
        
        # Add to global signal stream
        self.redis.lpush("signals:all", signal.id)
        self.redis.ltrim("signals:all", 0, 499)
        
        # Add to buffer
        self.signal_buffer.append(signal)
        
        logger.debug(f"[DECISION] Ingested signal: {signal.type} from {signal.source}")
    
    async def ingest_from_prometheus(self, alerts: List[Dict]) -> List[Signal]:
        """Convert Prometheus alerts to signals"""
        signals = []
        for alert in alerts:
            signal = Signal(
                id=f"prom_{hashlib.md5(json.dumps(alert, sort_keys=True).encode()).hexdigest()[:12]}",
                type=SignalType.ALERT.value,
                source=SignalSource.PROMETHEUS.value,
                service=alert.get("labels", {}).get("service", "unknown"),
                timestamp=datetime.now(timezone.utc).isoformat(),
                severity=alert.get("labels", {}).get("severity", "medium"),
                message=alert.get("annotations", {}).get("summary", "Prometheus alert"),
                data=alert,
            )
            await self.ingest_signal(signal)
            signals.append(signal)
        return signals
    
    async def ingest_from_datadog(self, events: List[Dict]) -> List[Signal]:
        """Convert Datadog events to signals"""
        signals = []
        for event in events:
            signal = Signal(
                id=f"dd_{event.get('id', hashlib.md5(str(event).encode()).hexdigest()[:12])}",
                type=SignalType.METRIC.value if event.get("type") == "metric_alert" else SignalType.ALERT.value,
                source=SignalSource.DATADOG.value,
                service=event.get("tags", {}).get("service", "unknown"),
                timestamp=datetime.now(timezone.utc).isoformat(),
                severity=event.get("priority", "medium"),
                message=event.get("title", "Datadog event"),
                data=event,
            )
            await self.ingest_signal(signal)
            signals.append(signal)
        return signals
    
    async def ingest_from_kubernetes(self, events: List[Dict]) -> List[Signal]:
        """Convert Kubernetes events to signals"""
        signals = []
        for event in events:
            # Map K8s event types to severity
            event_type = event.get("type", "Normal")
            severity = "low" if event_type == "Normal" else "high"
            
            reason = event.get("reason", "")
            if reason in ["OOMKilled", "CrashLoopBackOff", "Evicted"]:
                severity = "critical"
            
            signal = Signal(
                id=f"k8s_{event.get('metadata', {}).get('uid', hashlib.md5(str(event).encode()).hexdigest()[:12])}",
                type=SignalType.HEALTH_CHECK.value,
                source=SignalSource.KUBERNETES.value,
                service=event.get("involvedObject", {}).get("name", "unknown"),
                timestamp=event.get("lastTimestamp", datetime.now(timezone.utc).isoformat()),
                severity=severity,
                message=f"{event.get('reason', 'Event')}: {event.get('message', '')}",
                data=event,
            )
            await self.ingest_signal(signal)
            signals.append(signal)
        return signals
    
    async def ingest_deployment(
        self,
        service: str,
        version: str,
        deployer: str,
        status: str = "started"
    ) -> Signal:
        """Ingest a deployment event"""
        signal = Signal(
            id=f"deploy_{service}_{int(datetime.now(timezone.utc).timestamp())}",
            type=SignalType.DEPLOYMENT.value,
            source=SignalSource.ARGOCD.value,  # Could be any deploy tool
            service=service,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="medium",
            message=f"Deployment {status}: {service} -> {version}",
            data={
                "version": version,
                "deployer": deployer,
                "status": status
            }
        )
        await self.ingest_signal(signal)
        return signal
    
    def _correlate_signals(self, signals: List[Dict]) -> List[CorrelatedEvent]:
        """
        Correlate signals into events based on:
        - Time proximity
        - Service relationship
        - Signal type combinations
        """
        
        if not signals:
            return []
        
        events = []
        used_signal_ids = set()
        
        # Sort by timestamp
        signals = sorted(signals, key=lambda s: s.get("timestamp", ""))
        
        for i, primary_signal in enumerate(signals):
            if primary_signal["id"] in used_signal_ids:
                continue
            
            # Start a new event with this signal
            event_signals = [primary_signal]
            used_signal_ids.add(primary_signal["id"])
            
            primary_time = datetime.fromisoformat(
                primary_signal["timestamp"].replace("Z", "+00:00")
            )
            primary_service = primary_signal.get("service", "unknown")
            
            # Find correlated signals
            for other_signal in signals[i+1:]:
                if other_signal["id"] in used_signal_ids:
                    continue
                
                other_time = datetime.fromisoformat(
                    other_signal["timestamp"].replace("Z", "+00:00")
                )
                
                # Check time proximity
                time_diff = abs((other_time - primary_time).total_seconds())
                if time_diff > self.correlation_window_seconds:
                    continue
                
                # Calculate correlation score
                score = self._calculate_correlation_score(
                    primary_signal, other_signal
                )
                
                if score >= self.min_correlation_score:
                    event_signals.append(other_signal)
                    used_signal_ids.add(other_signal["id"])
            
            # Create correlated event
            if event_signals:
                services = list(set(s.get("service", "unknown") for s in event_signals))
                signal_types = list(set(s.get("type", "unknown") for s in event_signals))
                signal_sources = list(set(s.get("source", "unknown") for s in event_signals))
                
                # Determine overall severity
                severities = [s.get("severity", "low") for s in event_signals]
                severity_order = ["critical", "high", "medium", "low"]
                overall_severity = min(severities, key=lambda x: severity_order.index(x) if x in severity_order else 3)
                
                event = CorrelatedEvent(
                    event_id=f"event_{hashlib.md5(str(event_signals).encode()).hexdigest()[:12]}",
                    signals=event_signals,
                    services_affected=services,
                    primary_service=primary_service,
                    severity=overall_severity,
                    correlation_score=len(event_signals) / len(signals) if signals else 0,
                    first_signal_at=event_signals[0]["timestamp"],
                    last_signal_at=event_signals[-1]["timestamp"],
                    signal_types=signal_types,
                    signal_sources=signal_sources
                )
                events.append(event)
        
        return events
    
    def _calculate_correlation_score(self, signal1: Dict, signal2: Dict) -> float:
        """Calculate correlation score between two signals"""
        
        score = 0.0
        
        # Same service = high correlation
        if signal1.get("service") == signal2.get("service"):
            score += 0.4
        
        # Same source = moderate correlation
        if signal1.get("source") == signal2.get("source"):
            score += 0.2
        
        # Complementary types (e.g., deployment + alert)
        types_combo = {signal1.get("type"), signal2.get("type")}
        if SignalType.DEPLOYMENT.value in types_combo and SignalType.ALERT.value in types_combo:
            score += 0.3
        if SignalType.METRIC.value in types_combo and SignalType.LOG.value in types_combo:
            score += 0.2
        
        # Severity alignment
        if signal1.get("severity") == signal2.get("severity"):
            score += 0.1
        
        return min(1.0, score)
    
    async def process_and_decide(self) -> List[UnifiedDecision]:
        """
        Main decision loop:
        1. Get recent signals
        2. Correlate into events
        3. Apply decision rules
        4. Produce unified decisions
        """
        
        # Get recent signals from Redis
        signal_ids = self.redis.lrange("signals:all", 0, 99)
        signals = []
        
        for sid in signal_ids:
            if isinstance(sid, bytes):
                sid = sid.decode("utf-8")
            signal_data = self.redis.get(f"signal:{sid}")
            if signal_data:
                signals.append(json.loads(signal_data))
        
        if not signals:
            return []
        
        # Correlate signals into events
        events = self._correlate_signals(signals)
        
        if not events:
            return []
        
        # Make decisions for each event
        decisions = []
        for event in events:
            decision = await self._make_decision(event)
            if decision.decision_type != DecisionType.NO_ACTION.value:
                decisions.append(decision)
                # Store decision
                self._store_decision(decision)
        
        logger.info(f"[DECISION] Processed {len(signals)} signals -> {len(events)} events -> {len(decisions)} decisions")
        
        return decisions
    
    async def _make_decision(self, event: CorrelatedEvent) -> UnifiedDecision:
        """Make a unified decision for a correlated event"""
        
        signals = event.signals
        
        # Base confidence from signal count and correlation
        base_confidence = min(50 + (len(signals) * 5), 70)
        
        # Apply decision rules
        matched_rule = None
        for rule in self.decision_rules:
            try:
                if rule["condition"](signals, event):
                    matched_rule = rule
                    break
            except Exception as e:
                logger.error(f"[DECISION] Rule {rule['name']} error: {e}")
                continue
        
        if matched_rule:
            decision_type = matched_rule["decision_type"]
            confidence = min(100, base_confidence + matched_rule["confidence_boost"])
            reasoning = matched_rule["reasoning"]
        else:
            # Default decision
            if event.severity in ["critical", "high"]:
                decision_type = DecisionType.AUTO_REMEDIATE
                confidence = base_confidence
                reasoning = "High severity event requires remediation"
            else:
                decision_type = DecisionType.INVESTIGATE
                confidence = base_confidence - 10
                reasoning = "Event requires investigation"
        
        # Determine primary action
        action_mapping = {
            DecisionType.ROLLBACK: ("rollback", {"target": "previous_version"}),
            DecisionType.SCALE: ("scale_up", {"factor": 2}),
            DecisionType.RESTART: ("restart_service", {}),
            DecisionType.ESCALATE: ("page_oncall", {"urgency": "high"}),
            DecisionType.AUTO_REMEDIATE: ("analyze_and_fix", {}),
            DecisionType.INVESTIGATE: ("create_investigation", {}),
            DecisionType.MANUAL_APPROVAL: ("await_approval", {}),
        }
        
        primary_action, action_params = action_mapping.get(
            decision_type, 
            ("investigate", {})
        )
        
        # Build contributing factors
        factors = []
        for s in signals[:5]:
            factors.append(f"{s['source']}: {s['message'][:50]}")
        
        # Determine if auto-executable
        auto_executable = (
            confidence >= 75 and
            decision_type in [DecisionType.SCALE, DecisionType.RESTART] and
            event.severity != "critical"
        )
        
        requires_approval = (
            confidence < 70 or
            decision_type in [DecisionType.ROLLBACK, DecisionType.ESCALATE] or
            event.severity == "critical"
        )
        
        # Create decision
        decision = UnifiedDecision(
            decision_id=f"decision_{event.event_id}_{int(datetime.now(timezone.utc).timestamp())}",
            decision_type=decision_type.value,
            confidence=confidence,
            correlated_event=asdict(event),
            signals_analyzed=len(signals),
            services_affected=event.services_affected,
            primary_action=primary_action,
            action_params=action_params,
            fallback_actions=[
                {"action": "escalate", "condition": "primary_fails"},
                {"action": "page_oncall", "condition": "no_improvement_5min"}
            ],
            reasoning=reasoning,
            contributing_factors=factors,
            risk_assessment=self._assess_decision_risk(event, decision_type),
            requires_approval=requires_approval,
            auto_executable=auto_executable,
            estimated_impact=self._estimate_impact(event),
            estimated_resolution_time=self._estimate_resolution_time(decision_type),
            decided_at=datetime.now(timezone.utc).isoformat(),
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=self.decision_ttl_minutes)).isoformat()
        )
        
        return decision
    
    def _assess_decision_risk(self, event: CorrelatedEvent, decision_type: DecisionType) -> str:
        """Assess the risk of executing a decision"""
        
        risk_factors = []
        
        if len(event.services_affected) > 2:
            risk_factors.append("Multiple services affected")
        
        if decision_type == DecisionType.ROLLBACK:
            risk_factors.append("Rollback may cause brief service interruption")
        
        if event.severity == "critical":
            risk_factors.append("Critical severity - high stakes")
        
        if SignalType.DEPLOYMENT.value in event.signal_types:
            risk_factors.append("Recent deployment involved")
        
        if not risk_factors:
            return "Low risk - standard operation"
        elif len(risk_factors) == 1:
            return f"Moderate risk: {risk_factors[0]}"
        else:
            return f"High risk: {'; '.join(risk_factors)}"
    
    def _estimate_impact(self, event: CorrelatedEvent) -> str:
        """Estimate the impact of the event"""
        
        service_count = len(event.services_affected)
        
        if event.severity == "critical" or service_count >= 3:
            return "High - Significant user impact expected"
        elif event.severity == "high" or service_count == 2:
            return "Medium - Some users may be affected"
        else:
            return "Low - Limited or no user impact"
    
    def _estimate_resolution_time(self, decision_type: DecisionType) -> str:
        """Estimate time to resolution"""
        
        time_estimates = {
            DecisionType.RESTART: "2-5 minutes",
            DecisionType.SCALE: "5-10 minutes",
            DecisionType.ROLLBACK: "5-15 minutes",
            DecisionType.AUTO_REMEDIATE: "5-20 minutes",
            DecisionType.INVESTIGATE: "30-60 minutes",
            DecisionType.ESCALATE: "Depends on oncall response",
        }
        
        return time_estimates.get(decision_type, "Unknown")
    
    def _store_decision(self, decision: UnifiedDecision):
        """Store decision for tracking and audit"""
        
        decision_data = asdict(decision)
        
        # Store individual decision
        self.redis.setex(
            f"decision:{decision.decision_id}",
            3600 * 24,  # 24 hours
            json.dumps(decision_data)
        )
        
        # Add to decision stream
        self.redis.lpush("decisions:all", json.dumps(decision_data))
        self.redis.ltrim("decisions:all", 0, 199)
        
        # Add to service-specific stream
        for service in decision.services_affected:
            self.redis.lpush(f"decisions:{service}", json.dumps(decision_data))
            self.redis.ltrim(f"decisions:{service}", 0, 49)
    
    async def execute_decision(self, decision_id: str, executor=None) -> Dict:
        """Execute a unified decision"""
        
        decision_data = self.redis.get(f"decision:{decision_id}")
        if not decision_data:
            return {"success": False, "error": "Decision not found"}
        
        decision = json.loads(decision_data)
        
        if not decision.get("auto_executable") and decision.get("requires_approval"):
            return {
                "success": False,
                "error": "Decision requires manual approval",
                "decision_id": decision_id
            }
        
        # Execute via provided executor
        if executor:
            result = await executor.execute_action(
                decision["primary_action"],
                decision["services_affected"][0] if decision["services_affected"] else "unknown",
                decision["action_params"]
            )
            
            # Update decision with result
            decision["executed_at"] = datetime.now(timezone.utc).isoformat()
            decision["execution_result"] = result
            
            self.redis.setex(
                f"decision:{decision_id}",
                3600 * 24,
                json.dumps(decision)
            )
            
            return result
        
        return {
            "success": True,
            "dry_run": True,
            "message": f"Would execute {decision['primary_action']} on {decision['services_affected']}"
        }
    
    def get_pending_decisions(self) -> List[Dict]:
        """Get all pending decisions requiring approval"""
        
        decisions_data = self.redis.lrange("decisions:all", 0, 49)
        pending = []
        
        for d in decisions_data:
            try:
                decision = json.loads(d)
                if decision.get("requires_approval") and not decision.get("executed_at"):
                    pending.append(decision)
            except json.JSONDecodeError:
                continue
        
        return pending
    
    def get_decision_stats(self) -> Dict:
        """Get decision layer statistics"""
        
        try:
            # Count signals
            signal_count = self.redis.llen("signals:all")
            
            # Count decisions
            decisions_data = self.redis.lrange("decisions:all", 0, 199)
            total_decisions = len(decisions_data)
            
            # Breakdown by type
            by_type = {}
            executed = 0
            pending = 0
            
            for d in decisions_data:
                try:
                    decision = json.loads(d)
                    dtype = decision.get("decision_type", "unknown")
                    by_type[dtype] = by_type.get(dtype, 0) + 1
                    
                    if decision.get("executed_at"):
                        executed += 1
                    elif decision.get("requires_approval"):
                        pending += 1
                except json.JSONDecodeError:
                    continue
            
            return {
                "signals_processed": signal_count,
                "total_decisions": total_decisions,
                "decisions_by_type": by_type,
                "executed_decisions": executed,
                "pending_approval": pending,
                "correlation_window_seconds": self.correlation_window_seconds,
                "min_correlation_score": self.min_correlation_score
            }
            
        except Exception as e:
            return {"error": str(e)}


# Convenience function
async def make_cross_tool_decision(
    redis_client,
    signals: List[Dict]
) -> List[UnifiedDecision]:
    """Quick function to process signals and get decisions"""
    
    layer = CrossToolDecisionLayer(redis_client)
    
    # Ingest signals
    for s in signals:
        signal = Signal(
            id=s.get("id", f"sig_{datetime.now(timezone.utc).timestamp()}"),
            type=s.get("type", SignalType.ALERT.value),
            source=s.get("source", SignalSource.INTERNAL.value),
            service=s.get("service", "unknown"),
            timestamp=s.get("timestamp", datetime.now(timezone.utc).isoformat()),
            severity=s.get("severity", "medium"),
            message=s.get("message", "Signal received"),
            data=s.get("data", {})
        )
        await layer.ingest_signal(signal)
    
    # Process and get decisions
    return await layer.process_and_decide()
