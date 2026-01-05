"""
Prevention Module
=================
Proactive incident prevention capabilities for AI DevOps Autopilot.

Features:
- Repeat Incident Elimination
- Automatic preventive measure application  
- Permanent fix registry
- Escalation handling
"""

from .repeat_eliminator import (
    RepeatIncidentEliminator,
    IncidentPattern,
    PreventiveMeasure,
    check_and_prevent_repeat_incident,
)

__all__ = [
    "RepeatIncidentEliminator",
    "IncidentPattern", 
    "PreventiveMeasure",
    "check_and_prevent_repeat_incident",
]
