"""
Timeline Module
===============
Incident timeline generation for AI DevOps Autopilot.

Features:
- Unified incident timeline generation
- Multi-source event correlation
- Root cause candidate detection
- Human-readable markdown output
"""

from .incident_timeline import (
    IncidentTimelineGenerator,
    IncidentTimeline,
    TimelineEvent,
    TimelineEventType,
    EventSource,
    generate_incident_timeline,
)

__all__ = [
    "IncidentTimelineGenerator",
    "IncidentTimeline",
    "TimelineEvent",
    "TimelineEventType",
    "EventSource",
    "generate_incident_timeline",
]
