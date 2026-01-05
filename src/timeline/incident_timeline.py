"""
Incident Timeline Generator
============================
Produces unified, neutral incident timelines correlating deployments,
alerts, metrics, actions, and resolutions into a single authoritative view.

This is essential for:
- Post-incident reviews
- Root cause analysis
- Regulatory compliance
- Team learning
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incident_timeline")


class TimelineEventType(Enum):
    """Types of events in an incident timeline"""
    DEPLOYMENT = "deployment"
    METRIC_ANOMALY = "metric_anomaly"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    LOG_ERROR = "log_error"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    ACTION_PROPOSED = "action_proposed"
    ACTION_APPROVED = "action_approved"
    ACTION_EXECUTED = "action_executed"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    ROLLBACK = "rollback"
    ESCALATION = "escalation"
    HUMAN_INTERVENTION = "human_intervention"
    SYSTEM_RECOVERY = "system_recovery"
    COMMUNICATION = "communication"


class EventSource(Enum):
    """Source systems for timeline events"""
    PROMETHEUS = "prometheus"
    KUBERNETES = "kubernetes"
    CLOUDWATCH = "cloudwatch"
    DATADOG = "datadog"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    CI_CD = "ci_cd"
    AI_AUTOPILOT = "ai_autopilot"
    HUMAN = "human"
    INTERNAL = "internal"


@dataclass
class TimelineEvent:
    """A single event in the incident timeline"""
    event_id: str
    timestamp: str
    event_type: str
    source: str
    
    # Description
    title: str
    description: str
    severity: str  # info, warning, error, critical
    
    # Context
    service: str
    component: Optional[str] = None
    
    # Related data
    data: Dict = field(default_factory=dict)
    related_event_ids: List[str] = field(default_factory=list)
    
    # Attribution
    actor: Optional[str] = None  # System/Human who caused the event
    actor_type: str = "system"  # system, human, automation
    
    # Analysis
    is_root_cause_candidate: bool = False
    impact_description: Optional[str] = None


@dataclass
class IncidentTimeline:
    """Complete incident timeline"""
    timeline_id: str
    incident_id: str
    incident_title: str
    
    # Timespan
    start_time: str
    end_time: Optional[str]
    duration_minutes: float
    
    # Events in chronological order
    events: List[Dict]
    event_count: int
    
    # Summary
    services_affected: List[str]
    primary_service: str
    root_cause_event_id: Optional[str]
    resolution_event_id: Optional[str]
    
    # Statistics
    deployment_count: int
    alert_count: int
    action_count: int
    escalation_count: int
    
    # Status
    is_resolved: bool
    resolution_summary: Optional[str]
    
    # Metadata
    generated_at: str
    generated_by: str


class IncidentTimelineGenerator:
    """
    Generates unified, neutral incident timelines by correlating
    events from multiple sources into a single chronological view.
    
    Features:
    - Multi-source event correlation
    - Automatic root cause candidate detection
    - Impact analysis
    - Human-readable summaries
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
        # Lookback window for timeline reconstruction
        self.default_lookback_minutes = 60
        self.max_lookback_minutes = 1440  # 24 hours
        
        logger.info("[TIMELINE] Incident Timeline Generator initialized")
    
    async def generate_timeline(
        self,
        incident_id: str,
        lookback_minutes: int = None,
        include_related_services: bool = True
    ) -> IncidentTimeline:
        """
        Generate a complete incident timeline.
        
        Args:
            incident_id: The incident to generate timeline for
            lookback_minutes: How far back to look for related events
            include_related_services: Include events from related services
        
        Returns:
            IncidentTimeline with all correlated events
        """
        
        lookback = lookback_minutes or self.default_lookback_minutes
        
        # Get incident details
        incident = self._get_incident(incident_id)
        if not incident:
            # Create timeline from scratch for new incident
            incident = {
                "id": incident_id,
                "title": f"Incident {incident_id}",
                "service": "unknown",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        
        primary_service = incident.get("service", "unknown")
        incident_time = incident.get("created_at", datetime.now(timezone.utc).isoformat())
        
        try:
            start_time = datetime.fromisoformat(incident_time.replace("Z", "+00:00"))
        except:
            start_time = datetime.now(timezone.utc)
        
        # Collect events from all sources
        all_events = []
        
        # 1. Deployment events
        deployments = self._get_deployment_events(
            primary_service, start_time, lookback
        )
        all_events.extend(deployments)
        
        # 2. Metric anomalies
        anomalies = self._get_anomaly_events(
            primary_service, start_time, lookback
        )
        all_events.extend(anomalies)
        
        # 3. Alerts
        alerts = self._get_alert_events(
            primary_service, start_time, lookback
        )
        all_events.extend(alerts)
        
        # 4. Actions taken
        actions = self._get_action_events(incident_id, primary_service)
        all_events.extend(actions)
        
        # 5. Decisions logged
        decisions = self._get_decision_events(incident_id, primary_service)
        all_events.extend(decisions)
        
        # 6. Log errors
        log_errors = self._get_log_error_events(
            primary_service, start_time, lookback
        )
        all_events.extend(log_errors)
        
        # 7. Incident lifecycle events
        lifecycle = self._get_incident_lifecycle_events(incident_id, incident)
        all_events.extend(lifecycle)
        
        # Sort all events chronologically
        all_events.sort(key=lambda e: e.get("timestamp", ""))
        
        # Identify root cause candidate
        root_cause_event_id = self._identify_root_cause(all_events)
        
        # Identify resolution event
        resolution_event_id = self._identify_resolution(all_events)
        
        # Calculate statistics
        deployment_count = sum(1 for e in all_events if e.get("event_type") == TimelineEventType.DEPLOYMENT.value)
        alert_count = sum(1 for e in all_events if e.get("event_type") == TimelineEventType.ALERT_TRIGGERED.value)
        action_count = sum(1 for e in all_events if e.get("event_type") in [
            TimelineEventType.ACTION_PROPOSED.value,
            TimelineEventType.ACTION_EXECUTED.value
        ])
        escalation_count = sum(1 for e in all_events if e.get("event_type") == TimelineEventType.ESCALATION.value)
        
        # Get all affected services
        services = list(set(e.get("service", "unknown") for e in all_events))
        
        # Calculate duration
        end_time = None
        is_resolved = False
        if resolution_event_id:
            for e in all_events:
                if e.get("event_id") == resolution_event_id:
                    end_time = e.get("timestamp")
                    is_resolved = True
                    break
        
        duration = 0
        if end_time and all_events:
            try:
                first_time = datetime.fromisoformat(all_events[0]["timestamp"].replace("Z", "+00:00"))
                last_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                duration = (last_time - first_time).total_seconds() / 60
            except:
                pass
        
        # Build timeline
        timeline = IncidentTimeline(
            timeline_id=f"timeline_{incident_id}_{int(datetime.now(timezone.utc).timestamp())}",
            incident_id=incident_id,
            incident_title=incident.get("title", f"Incident {incident_id}"),
            start_time=all_events[0]["timestamp"] if all_events else start_time.isoformat(),
            end_time=end_time,
            duration_minutes=round(duration, 1),
            events=all_events,
            event_count=len(all_events),
            services_affected=services,
            primary_service=primary_service,
            root_cause_event_id=root_cause_event_id,
            resolution_event_id=resolution_event_id,
            deployment_count=deployment_count,
            alert_count=alert_count,
            action_count=action_count,
            escalation_count=escalation_count,
            is_resolved=is_resolved,
            resolution_summary=self._generate_resolution_summary(all_events, is_resolved),
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by="ai_autopilot"
        )
        
        # Store timeline
        self._store_timeline(timeline)
        
        logger.info(f"[TIMELINE] Generated timeline for {incident_id}: {len(all_events)} events")
        
        return timeline
    
    def _get_incident(self, incident_id: str) -> Optional[Dict]:
        """Get incident details from Redis"""
        try:
            data = self.redis.get(f"incident:{incident_id}")
            if data:
                return json.loads(data)
        except:
            pass
        return None
    
    def _get_deployment_events(
        self,
        service: str,
        incident_time: datetime,
        lookback: int
    ) -> List[Dict]:
        """Get deployment events"""
        
        events = []
        start_time = (incident_time - timedelta(minutes=lookback)).timestamp()
        
        try:
            # Get deployments from Redis
            deployments = self.redis.zrangebyscore(
                f"deployments:{service}",
                start_time,
                "+inf",
                withscores=True
            )
            
            for version, timestamp in deployments:
                version_str = version.decode() if isinstance(version, bytes) else version
                event_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                
                event = TimelineEvent(
                    event_id=f"deploy_{service}_{int(timestamp)}",
                    timestamp=event_time.isoformat(),
                    event_type=TimelineEventType.DEPLOYMENT.value,
                    source=EventSource.CI_CD.value,
                    title=f"Deployment: {service} → {version_str}",
                    description=f"Version {version_str} deployed to {service}",
                    severity="info",
                    service=service,
                    data={"version": version_str, "timestamp": timestamp},
                    is_root_cause_candidate=True,  # Deployments are always candidates
                    impact_description="Deployment may have introduced changes affecting service behavior"
                )
                events.append(asdict(event))
                
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting deployments: {e}")
        
        return events
    
    def _get_anomaly_events(
        self,
        service: str,
        incident_time: datetime,
        lookback: int
    ) -> List[Dict]:
        """Get metric anomaly events"""
        
        events = []
        
        try:
            # Get anomalies from Redis
            anomalies_data = self.redis.lrange(f"recent_anomalies:{service}", 0, 49)
            
            cutoff = (incident_time - timedelta(minutes=lookback)).isoformat()
            
            for anomaly_json in anomalies_data:
                try:
                    anomaly = json.loads(anomaly_json)
                    timestamp = anomaly.get("timestamp", "")
                    
                    if timestamp < cutoff:
                        continue
                    
                    severity = anomaly.get("severity", "warning")
                    metric = anomaly.get("metric_name", "unknown")
                    value = anomaly.get("current_value", 0)
                    baseline = anomaly.get("baseline_mean", 0)
                    
                    event = TimelineEvent(
                        event_id=f"anomaly_{anomaly.get('id', hash(anomaly_json))}",
                        timestamp=timestamp,
                        event_type=TimelineEventType.METRIC_ANOMALY.value,
                        source=EventSource.PROMETHEUS.value,
                        title=f"Metric Anomaly: {metric}",
                        description=f"{metric} = {value:.2f} (baseline: {baseline:.2f})",
                        severity=severity,
                        service=service,
                        data=anomaly,
                        is_root_cause_candidate=severity in ["critical", "high"]
                    )
                    events.append(asdict(event))
                    
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting anomalies: {e}")
        
        return events
    
    def _get_alert_events(
        self,
        service: str,
        incident_time: datetime,
        lookback: int
    ) -> List[Dict]:
        """Get alert events"""
        
        events = []
        
        try:
            # Get alerts from Redis
            alerts_data = self.redis.lrange(f"alerts:{service}", 0, 49)
            
            cutoff = (incident_time - timedelta(minutes=lookback)).isoformat()
            
            for alert_json in alerts_data:
                try:
                    alert = json.loads(alert_json)
                    timestamp = alert.get("timestamp", alert.get("triggered_at", ""))
                    
                    if timestamp < cutoff:
                        continue
                    
                    event = TimelineEvent(
                        event_id=f"alert_{alert.get('id', hash(alert_json))}",
                        timestamp=timestamp,
                        event_type=TimelineEventType.ALERT_TRIGGERED.value,
                        source=alert.get("source", EventSource.PROMETHEUS.value),
                        title=f"Alert: {alert.get('name', 'Unknown Alert')}",
                        description=alert.get("message", alert.get("description", "")),
                        severity=alert.get("severity", "warning"),
                        service=service,
                        data=alert
                    )
                    events.append(asdict(event))
                    
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting alerts: {e}")
        
        return events
    
    def _get_action_events(
        self,
        incident_id: str,
        service: str
    ) -> List[Dict]:
        """Get action events for incident"""
        
        events = []
        
        try:
            # Get actions from Redis
            action_ids = self.redis.lrange(f"actions:by_incident:{incident_id}", 0, 49)
            
            for action_id in action_ids:
                try:
                    aid = action_id.decode() if isinstance(action_id, bytes) else action_id
                    action_data = self.redis.get(f"action:{aid}")
                    
                    if action_data:
                        action = json.loads(action_data)
                        
                        # Proposed event
                        events.append(asdict(TimelineEvent(
                            event_id=f"action_proposed_{aid}",
                            timestamp=action.get("proposed_at", ""),
                            event_type=TimelineEventType.ACTION_PROPOSED.value,
                            source=EventSource.AI_AUTOPILOT.value,
                            title=f"Action Proposed: {action.get('action_type', 'unknown')}",
                            description=action.get("reasoning", ""),
                            severity="info",
                            service=action.get("service", service),
                            data=action,
                            actor=action.get("proposed_by", "ai_autopilot"),
                            actor_type="automation"
                        )))
                        
                        # Executed event (if executed)
                        if action.get("executed_at"):
                            events.append(asdict(TimelineEvent(
                                event_id=f"action_executed_{aid}",
                                timestamp=action.get("executed_at", ""),
                                event_type=TimelineEventType.ACTION_EXECUTED.value,
                                source=EventSource.AI_AUTOPILOT.value,
                                title=f"Action Executed: {action.get('action_type', 'unknown')}",
                                description=f"Executed by {action.get('approved_by', 'unknown')}",
                                severity="info",
                                service=action.get("service", service),
                                data=action,
                                actor=action.get("approved_by", "system"),
                                actor_type="automation" if action.get("auto_executed") else "human"
                            )))
                            
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting actions: {e}")
        
        return events
    
    def _get_decision_events(
        self,
        incident_id: str,
        service: str
    ) -> List[Dict]:
        """Get decision log events"""
        
        events = []
        
        try:
            # Get decisions from Redis
            decisions_data = self.redis.lrange(f"decision_logs:{service}", 0, 49)
            
            for decision_json in decisions_data:
                try:
                    decision = json.loads(decision_json)
                    
                    if decision.get("incident_id") != incident_id:
                        continue
                    
                    event = TimelineEvent(
                        event_id=f"decision_{decision.get('decision_id', '')}",
                        timestamp=decision.get("timestamp", ""),
                        event_type=TimelineEventType.ACTION_APPROVED.value if decision.get("decision") == "approved" else TimelineEventType.HUMAN_INTERVENTION.value,
                        source=EventSource.AI_AUTOPILOT.value,
                        title=f"Decision: {decision.get('action_type', 'unknown')} {decision.get('decision', '').upper()}",
                        description=decision.get("reasoning_summary", ""),
                        severity="info",
                        service=service,
                        data={
                            "confidence": decision.get("final_confidence"),
                            "was_autonomous": decision.get("was_autonomous"),
                            "factors_for": decision.get("factors_for", []),
                            "factors_against": decision.get("factors_against", [])
                        },
                        actor="ai_autopilot" if decision.get("was_autonomous") else "human",
                        actor_type="automation" if decision.get("was_autonomous") else "human"
                    )
                    events.append(asdict(event))
                    
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting decisions: {e}")
        
        return events
    
    def _get_log_error_events(
        self,
        service: str,
        incident_time: datetime,
        lookback: int
    ) -> List[Dict]:
        """Get error log events"""
        
        events = []
        
        try:
            # Get logs from Redis
            logs_data = self.redis.lrange(f"logs:{service}", 0, 99)
            
            cutoff = (incident_time - timedelta(minutes=lookback)).isoformat()
            
            for log_json in logs_data:
                try:
                    log = json.loads(log_json)
                    
                    if log.get("level") not in ["ERROR", "CRITICAL"]:
                        continue
                    
                    timestamp = log.get("timestamp", "")
                    if timestamp < cutoff:
                        continue
                    
                    event = TimelineEvent(
                        event_id=f"log_{hash(log_json)}",
                        timestamp=timestamp,
                        event_type=TimelineEventType.LOG_ERROR.value,
                        source=EventSource.INTERNAL.value,
                        title=f"Error Log: {log.get('message', '')[:50]}",
                        description=log.get("message", ""),
                        severity="error" if log.get("level") == "ERROR" else "critical",
                        service=service,
                        data=log
                    )
                    events.append(asdict(event))
                    
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"[TIMELINE] Error getting logs: {e}")
        
        return events
    
    def _get_incident_lifecycle_events(
        self,
        incident_id: str,
        incident: Dict
    ) -> List[Dict]:
        """Get incident lifecycle events"""
        
        events = []
        service = incident.get("service", "unknown")
        
        # Incident created
        if incident.get("created_at"):
            events.append(asdict(TimelineEvent(
                event_id=f"incident_created_{incident_id}",
                timestamp=incident.get("created_at"),
                event_type=TimelineEventType.INCIDENT_CREATED.value,
                source=EventSource.AI_AUTOPILOT.value,
                title=f"Incident Created: {incident.get('title', incident_id)}",
                description=f"Initial severity: {incident.get('severity', 'unknown')}",
                severity=incident.get("severity", "warning"),
                service=service,
                data=incident
            )))
        
        # Incident resolved
        if incident.get("resolved_at"):
            events.append(asdict(TimelineEvent(
                event_id=f"incident_resolved_{incident_id}",
                timestamp=incident.get("resolved_at"),
                event_type=TimelineEventType.INCIDENT_RESOLVED.value,
                source=EventSource.AI_AUTOPILOT.value,
                title="Incident Resolved",
                description=incident.get("resolution_notes", ""),
                severity="info",
                service=service,
                data={"resolution": incident.get("resolution_notes")}
            )))
        
        return events
    
    def _identify_root_cause(self, events: List[Dict]) -> Optional[str]:
        """Identify the most likely root cause event"""
        
        # Candidates are marked events
        candidates = [e for e in events if e.get("is_root_cause_candidate")]
        
        if not candidates:
            # Fall back to first deployment or critical anomaly
            for e in events:
                if e.get("event_type") == TimelineEventType.DEPLOYMENT.value:
                    return e.get("event_id")
                if e.get("severity") == "critical":
                    return e.get("event_id")
            return None
        
        # Return earliest candidate
        candidates.sort(key=lambda e: e.get("timestamp", ""))
        return candidates[0].get("event_id") if candidates else None
    
    def _identify_resolution(self, events: List[Dict]) -> Optional[str]:
        """Identify the resolution event"""
        
        for e in reversed(events):
            if e.get("event_type") == TimelineEventType.INCIDENT_RESOLVED.value:
                return e.get("event_id")
            if e.get("event_type") == TimelineEventType.SYSTEM_RECOVERY.value:
                return e.get("event_id")
        
        return None
    
    def _generate_resolution_summary(self, events: List[Dict], is_resolved: bool) -> Optional[str]:
        """Generate a summary of how the incident was resolved"""
        
        if not is_resolved:
            return None
        
        actions_taken = [
            e for e in events 
            if e.get("event_type") in [
                TimelineEventType.ACTION_EXECUTED.value,
                TimelineEventType.ROLLBACK.value
            ]
        ]
        
        if actions_taken:
            action_types = [e.get("title", "unknown action") for e in actions_taken]
            return f"Resolved via: {', '.join(action_types[:3])}"
        
        return "Incident resolved - see timeline for details"
    
    def _store_timeline(self, timeline: IncidentTimeline):
        """Store timeline in Redis"""
        
        try:
            timeline_json = json.dumps(asdict(timeline))
            
            # Store by timeline ID
            self.redis.setex(
                f"timeline:{timeline.timeline_id}",
                86400 * 30,  # 30 days
                timeline_json
            )
            
            # Store by incident ID
            self.redis.setex(
                f"incident_timeline:{timeline.incident_id}",
                86400 * 30,
                timeline_json
            )
            
            # Add to timeline list
            self.redis.lpush("timelines:all", timeline.timeline_id)
            self.redis.ltrim("timelines:all", 0, 499)
            
        except Exception as e:
            logger.error(f"[TIMELINE] Error storing timeline: {e}")
    
    def get_timeline(self, incident_id: str) -> Optional[IncidentTimeline]:
        """Get timeline for an incident"""
        
        try:
            data = self.redis.get(f"incident_timeline:{incident_id}")
            if data:
                return IncidentTimeline(**json.loads(data))
        except:
            pass
        return None
    
    def format_timeline_markdown(self, timeline: IncidentTimeline) -> str:
        """Format timeline as human-readable markdown"""
        
        lines = []
        
        lines.append(f"# Incident Timeline: {timeline.incident_title}")
        lines.append("")
        lines.append(f"**Incident ID:** {timeline.incident_id}")
        lines.append(f"**Primary Service:** {timeline.primary_service}")
        lines.append(f"**Duration:** {timeline.duration_minutes:.1f} minutes")
        lines.append(f"**Status:** {'✅ Resolved' if timeline.is_resolved else '🔴 Active'}")
        lines.append("")
        
        # Statistics
        lines.append("## Summary")
        lines.append(f"- **Total Events:** {timeline.event_count}")
        lines.append(f"- **Deployments:** {timeline.deployment_count}")
        lines.append(f"- **Alerts:** {timeline.alert_count}")
        lines.append(f"- **Actions Taken:** {timeline.action_count}")
        lines.append(f"- **Escalations:** {timeline.escalation_count}")
        lines.append(f"- **Services Affected:** {', '.join(timeline.services_affected)}")
        lines.append("")
        
        # Timeline
        lines.append("## Event Timeline")
        lines.append("")
        
        for event in timeline.events:
            timestamp = event.get("timestamp", "")[:19].replace("T", " ")
            event_type = event.get("event_type", "unknown")
            title = event.get("title", "")
            severity = event.get("severity", "info")
            
            # Emoji for event type
            emoji = {
                "deployment": "🚀",
                "metric_anomaly": "📊",
                "alert_triggered": "🚨",
                "log_error": "❌",
                "incident_created": "🔥",
                "incident_resolved": "✅",
                "action_proposed": "💡",
                "action_executed": "⚡",
                "rollback": "⏪",
                "escalation": "📢",
                "human_intervention": "👤"
            }.get(event_type, "•")
            
            # Root cause marker
            root_marker = " **[ROOT CAUSE]**" if event.get("event_id") == timeline.root_cause_event_id else ""
            
            lines.append(f"{emoji} **{timestamp}** | {title}{root_marker}")
            if event.get("description"):
                lines.append(f"   _{event.get('description')[:100]}_")
            lines.append("")
        
        # Resolution
        if timeline.is_resolved and timeline.resolution_summary:
            lines.append("## Resolution")
            lines.append(f"_{timeline.resolution_summary}_")
        
        return "\n".join(lines)


# Convenience function
async def generate_incident_timeline(
    redis_client,
    incident_id: str
) -> IncidentTimeline:
    """Quick function to generate incident timeline"""
    generator = IncidentTimelineGenerator(redis_client)
    return await generator.generate_timeline(incident_id)
