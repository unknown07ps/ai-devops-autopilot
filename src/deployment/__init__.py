"""
Deployment Module
=================
Deployment risk intelligence and management for AI DevOps Autopilot.

Features:
- Pre-deployment risk assessment
- Service criticality tiers
- Historical failure analysis
- Automatic rollback triggers
"""

from .risk_analyzer import (
    DeploymentRiskAnalyzer,
    DeploymentRiskAssessment,
    RiskFactor,
    RiskLevel,
    ServiceCriticality,
    assess_deployment,
)

__all__ = [
    "DeploymentRiskAnalyzer",
    "DeploymentRiskAssessment",
    "RiskFactor",
    "RiskLevel",
    "ServiceCriticality",
    "assess_deployment",
]
