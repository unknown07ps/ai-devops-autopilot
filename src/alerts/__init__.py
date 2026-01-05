"""
Alerts Module
=============
Alert noise suppression and triage for AI DevOps Autopilot.

Features:
- Intelligent alert deduplication
- Flapping detection
- Actionability scoring
- Historical outcome learning
- Alert grouping and aggregation
"""

from .noise_suppressor import (
    AlertNoiseSuppressor,
    AlertContext,
    TriageDecision,
    AlertDisposition,
    SuppressionReason,
    AlertGroup,
    triage_alert,
)

__all__ = [
    "AlertNoiseSuppressor",
    "AlertContext",
    "TriageDecision",
    "AlertDisposition",
    "SuppressionReason",
    "AlertGroup",
    "triage_alert",
]
