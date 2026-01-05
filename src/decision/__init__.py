"""
Decision Module
===============
Cross-tool decision intelligence for AI DevOps Autopilot.

Features:
- Multi-tool signal aggregation
- Signal correlation across services
- Unified operational decision making
- Decision execution and tracking
"""

from .cross_tool_layer import (
    CrossToolDecisionLayer,
    UnifiedDecision,
    CorrelatedEvent,
    Signal,
    SignalType,
    SignalSource,
    DecisionType,
    make_cross_tool_decision,
)

__all__ = [
    "CrossToolDecisionLayer",
    "UnifiedDecision",
    "CorrelatedEvent",
    "Signal",
    "SignalType",
    "SignalSource",
    "DecisionType",
    "make_cross_tool_decision",
]
