"""
Acceleration Module
===================
MTTR acceleration engine for AI DevOps Autopilot.

Features:
- Parallel root cause analysis
- Speculative remediation planning
- Concurrent data gathering
- Consensus building from multiple strategies
"""

from .mttr_engine import (
    MTTRAccelerator,
    AcceleratedResolution,
    AnalysisResult,
    RemediationPlan,
    AnalysisStrategy,
    RemediationPhase,
    accelerate_incident,
)

__all__ = [
    "MTTRAccelerator",
    "AcceleratedResolution",
    "AnalysisResult",
    "RemediationPlan",
    "AnalysisStrategy",
    "RemediationPhase",
    "accelerate_incident",
]
