"""
Knowledge Module
================
Senior engineer knowledge replication for AI DevOps Autopilot.

Features:
- Safe-action rule encoding
- Context-aware safety evaluation
- Senior engineer wisdom repository
- Autonomous remediation boundaries
"""

from .senior_knowledge import (
    SeniorKnowledgeEngine,
    SafetyRule,
    SafetyDecision,
    ActionSafetyLevel,
    ContextFactor,
    is_action_safe,
)

__all__ = [
    "SeniorKnowledgeEngine",
    "SafetyRule",
    "SafetyDecision",
    "ActionSafetyLevel",
    "ContextFactor",
    "is_action_safe",
]
