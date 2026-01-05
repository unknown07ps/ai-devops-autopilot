"""
Deployment Risk Intelligence
=============================
Pre-deployment risk assessment using historical failures, metrics, and service criticality.
Scores deployment risk and enables automatic rollback based on confidence thresholds.
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deployment_risk")


class RiskLevel(Enum):
    """Deployment risk levels"""
    CRITICAL = "critical"  # >80 - Block deployment
    HIGH = "high"          # 60-80 - Require manual approval
    MEDIUM = "medium"      # 40-60 - Deploy with monitoring
    LOW = "low"            # 20-40 - Safe to deploy
    MINIMAL = "minimal"    # <20 - Very safe


class ServiceCriticality(Enum):
    """Service criticality tiers"""
    TIER_1 = "tier_1"  # Critical - User-facing, revenue-impacting
    TIER_2 = "tier_2"  # Important - Backend services, data pipelines
    TIER_3 = "tier_3"  # Standard - Internal tools, non-critical
    TIER_4 = "tier_4"  # Low - Dev/test, experimental


@dataclass
class RiskFactor:
    """Individual risk factor contributing to overall score"""
    name: str
    score: float  # 0-100
    weight: float  # How much this factor contributes
    details: str
    mitigations: List[str]


@dataclass
class DeploymentRiskAssessment:
    """Complete risk assessment for a deployment"""
    deployment_id: str
    service: str
    version: str
    previous_version: Optional[str]
    overall_risk_score: float
    risk_level: str
    risk_factors: List[Dict]
    should_proceed: bool
    requires_approval: bool
    auto_rollback_enabled: bool
    rollback_threshold_minutes: int
    rollback_confidence: float
    recommendations: List[str]
    assessed_at: str
    
    # Historical context
    past_failures_count: int
    avg_recovery_time_minutes: float
    service_criticality: str
    current_health_score: float


class DeploymentRiskAnalyzer:
    """
    Analyzes deployment risk using multiple factors:
    - Historical failure rates
    - Service criticality
    - Current system health
    - Deployment timing
    - Change magnitude
    - Dependencies health
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
        # Risk thresholds
        self.auto_rollback_threshold = 70  # Auto-rollback if error rate exceeds this %
        self.block_deployment_threshold = 80  # Block deployment above this risk score
        self.require_approval_threshold = 60  # Require approval above this
        
        # Rollback configuration
        self.default_rollback_window_minutes = 15
        self.rollback_metrics_check_interval = 60  # seconds
        
        # Service criticality configuration
        self.service_criticality_map = self._load_service_criticality()
        
        # Risk weights
        self.weights = {
            "historical_failures": 0.25,
            "service_criticality": 0.20,
            "current_health": 0.15,
            "change_magnitude": 0.15,
            "deployment_timing": 0.10,
            "dependencies_health": 0.10,
            "recent_incidents": 0.05,
        }
        
        logger.info("[RISK] Deployment Risk Analyzer initialized")
    
    def _load_service_criticality(self) -> Dict[str, ServiceCriticality]:
        """Load or generate service criticality mapping"""
        
        # Default criticality based on service type
        criticality_patterns = {
            # Tier 1 - Critical
            "payment": ServiceCriticality.TIER_1,
            "auth": ServiceCriticality.TIER_1,
            "checkout": ServiceCriticality.TIER_1,
            "api-gateway": ServiceCriticality.TIER_1,
            "database-primary": ServiceCriticality.TIER_1,
            
            # Tier 2 - Important
            "order": ServiceCriticality.TIER_2,
            "user": ServiceCriticality.TIER_2,
            "inventory": ServiceCriticality.TIER_2,
            "kafka": ServiceCriticality.TIER_2,
            "redis": ServiceCriticality.TIER_2,
            
            # Tier 3 - Standard
            "notification": ServiceCriticality.TIER_3,
            "analytics": ServiceCriticality.TIER_3,
            "logging": ServiceCriticality.TIER_3,
            "monitoring": ServiceCriticality.TIER_3,
            
            # Tier 4 - Low
            "dev": ServiceCriticality.TIER_4,
            "test": ServiceCriticality.TIER_4,
            "staging": ServiceCriticality.TIER_4,
        }
        
        return criticality_patterns
    
    def get_service_criticality(self, service: str) -> ServiceCriticality:
        """Get criticality tier for a service"""
        
        service_lower = service.lower()
        
        # Check exact match first
        if service_lower in self.service_criticality_map:
            return self.service_criticality_map[service_lower]
        
        # Check partial matches
        for pattern, criticality in self.service_criticality_map.items():
            if pattern in service_lower:
                return criticality
        
        # Default to Tier 2
        return ServiceCriticality.TIER_2
    
    async def assess_deployment_risk(
        self,
        service: str,
        new_version: str,
        previous_version: Optional[str] = None,
        change_details: Optional[Dict] = None
    ) -> DeploymentRiskAssessment:
        """
        Perform comprehensive pre-deployment risk assessment.
        
        Args:
            service: Service being deployed
            new_version: Version being deployed
            previous_version: Current running version
            change_details: Optional details about the changes
        
        Returns:
            DeploymentRiskAssessment with risk score and recommendations
        """
        
        deployment_id = f"deploy_{service}_{int(datetime.now(timezone.utc).timestamp())}"
        risk_factors = []
        
        logger.info(f"[RISK] Assessing deployment: {service} -> {new_version}")
        
        # Factor 1: Historical Failures
        historical_factor = self._assess_historical_failures(service)
        risk_factors.append(historical_factor)
        
        # Factor 2: Service Criticality
        criticality_factor = self._assess_service_criticality(service)
        risk_factors.append(criticality_factor)
        
        # Factor 3: Current System Health
        health_factor = await self._assess_current_health(service)
        risk_factors.append(health_factor)
        
        # Factor 4: Change Magnitude
        magnitude_factor = self._assess_change_magnitude(
            previous_version, new_version, change_details
        )
        risk_factors.append(magnitude_factor)
        
        # Factor 5: Deployment Timing
        timing_factor = self._assess_deployment_timing()
        risk_factors.append(timing_factor)
        
        # Factor 6: Dependencies Health
        dependencies_factor = await self._assess_dependencies_health(service)
        risk_factors.append(dependencies_factor)
        
        # Factor 7: Recent Incidents
        incidents_factor = self._assess_recent_incidents(service)
        risk_factors.append(incidents_factor)
        
        # Calculate overall risk score (weighted average)
        overall_score = sum(
            factor.score * factor.weight 
            for factor in risk_factors
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Determine actions
        should_proceed = overall_score < self.block_deployment_threshold
        requires_approval = overall_score >= self.require_approval_threshold
        auto_rollback = overall_score >= 50  # Enable auto-rollback for medium+ risk
        
        # Calculate rollback confidence
        rollback_confidence = min(
            90,
            50 + (historical_factor.score * 0.3) + (criticality_factor.score * 0.2)
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_factors, overall_score, risk_level
        )
        
        # Get historical context
        past_failures = self._get_past_failure_count(service)
        avg_recovery = self._get_avg_recovery_time(service)
        current_health = 100 - health_factor.score  # Invert (lower risk = higher health)
        
        # Build assessment
        assessment = DeploymentRiskAssessment(
            deployment_id=deployment_id,
            service=service,
            version=new_version,
            previous_version=previous_version,
            overall_risk_score=round(overall_score, 1),
            risk_level=risk_level.value,
            risk_factors=[asdict(f) for f in risk_factors],
            should_proceed=should_proceed,
            requires_approval=requires_approval,
            auto_rollback_enabled=auto_rollback,
            rollback_threshold_minutes=self.default_rollback_window_minutes,
            rollback_confidence=round(rollback_confidence, 1),
            recommendations=recommendations,
            assessed_at=datetime.now(timezone.utc).isoformat(),
            past_failures_count=past_failures,
            avg_recovery_time_minutes=avg_recovery,
            service_criticality=self.get_service_criticality(service).value,
            current_health_score=round(current_health, 1)
        )
        
        # Store assessment
        self._store_assessment(assessment)
        
        logger.info(
            f"[RISK] Assessment complete: {service} = {overall_score:.1f} ({risk_level.value})"
        )
        
        return assessment
    
    def _assess_historical_failures(self, service: str) -> RiskFactor:
        """Assess risk based on historical deployment failures"""
        
        try:
            # Get deployment history
            history_key = f"deployment_history:{service}"
            history_data = self.redis.lrange(history_key, 0, 19)  # Last 20
            
            if not history_data:
                return RiskFactor(
                    name="historical_failures",
                    score=30,  # Unknown history = moderate risk
                    weight=self.weights["historical_failures"],
                    details="No deployment history available",
                    mitigations=["Build deployment history for better risk assessment"]
                )
            
            # Calculate failure rate
            total = len(history_data)
            failures = 0
            for entry in history_data:
                try:
                    data = json.loads(entry)
                    if data.get("failed") or data.get("rolled_back"):
                        failures += 1
                except:
                    continue
            
            failure_rate = (failures / total * 100) if total > 0 else 0
            
            # Score based on failure rate
            if failure_rate == 0:
                score = 10
            elif failure_rate < 10:
                score = 25
            elif failure_rate < 20:
                score = 45
            elif failure_rate < 30:
                score = 65
            else:
                score = 85
            
            return RiskFactor(
                name="historical_failures",
                score=score,
                weight=self.weights["historical_failures"],
                details=f"Failure rate: {failure_rate:.1f}% ({failures}/{total} deployments)",
                mitigations=[
                    "Review past failure root causes",
                    "Add more comprehensive testing",
                    "Consider canary deployment"
                ] if score > 40 else []
            )
            
        except Exception as e:
            logger.error(f"[RISK] Historical assessment error: {e}")
            return RiskFactor(
                name="historical_failures",
                score=50,
                weight=self.weights["historical_failures"],
                details=f"Error assessing history: {e}",
                mitigations=[]
            )
    
    def _assess_service_criticality(self, service: str) -> RiskFactor:
        """Assess risk based on service criticality tier"""
        
        criticality = self.get_service_criticality(service)
        
        criticality_scores = {
            ServiceCriticality.TIER_1: 80,
            ServiceCriticality.TIER_2: 55,
            ServiceCriticality.TIER_3: 30,
            ServiceCriticality.TIER_4: 10,
        }
        
        score = criticality_scores.get(criticality, 55)
        
        mitigations = []
        if criticality == ServiceCriticality.TIER_1:
            mitigations = [
                "Consider deploying during low-traffic window",
                "Ensure rollback procedure is tested",
                "Have incident response team on standby"
            ]
        elif criticality == ServiceCriticality.TIER_2:
            mitigations = [
                "Monitor closely after deployment",
                "Prepare rollback if needed"
            ]
        
        return RiskFactor(
            name="service_criticality",
            score=score,
            weight=self.weights["service_criticality"],
            details=f"Service tier: {criticality.value}",
            mitigations=mitigations
        )
    
    async def _assess_current_health(self, service: str) -> RiskFactor:
        """Assess risk based on current system health"""
        
        try:
            # Get recent anomalies
            anomalies = self.redis.lrange(f"recent_anomalies:{service}", 0, 9)
            anomaly_count = len(anomalies)
            
            # Get current metrics health
            metrics_key = f"metrics:{service}:health"
            health_data = self.redis.get(metrics_key)
            
            # Calculate health score
            if anomaly_count == 0:
                score = 15
                details = "Service is healthy - no recent anomalies"
            elif anomaly_count <= 2:
                score = 35
                details = f"Minor issues: {anomaly_count} recent anomalies"
            elif anomaly_count <= 5:
                score = 60
                details = f"Degraded health: {anomaly_count} recent anomalies"
            else:
                score = 85
                details = f"Poor health: {anomaly_count} recent anomalies"
            
            mitigations = []
            if score > 50:
                mitigations = [
                    "Wait for current issues to stabilize",
                    "Address existing anomalies first",
                    "Consider postponing deployment"
                ]
            
            return RiskFactor(
                name="current_health",
                score=score,
                weight=self.weights["current_health"],
                details=details,
                mitigations=mitigations
            )
            
        except Exception as e:
            return RiskFactor(
                name="current_health",
                score=50,
                weight=self.weights["current_health"],
                details=f"Unable to assess health: {e}",
                mitigations=[]
            )
    
    def _assess_change_magnitude(
        self,
        previous_version: Optional[str],
        new_version: str,
        change_details: Optional[Dict]
    ) -> RiskFactor:
        """Assess risk based on change magnitude"""
        
        # Analyze version difference
        is_major = False
        is_minor = False
        is_patch = False
        
        if previous_version and new_version:
            try:
                prev_parts = previous_version.split(".")
                new_parts = new_version.split(".")
                
                if prev_parts[0] != new_parts[0]:
                    is_major = True
                elif len(prev_parts) > 1 and len(new_parts) > 1:
                    if prev_parts[1] != new_parts[1]:
                        is_minor = True
                    else:
                        is_patch = True
            except:
                pass
        
        # Base score on change type
        if is_major:
            score = 75
            details = f"Major version change: {previous_version} -> {new_version}"
        elif is_minor:
            score = 45
            details = f"Minor version change: {previous_version} -> {new_version}"
        elif is_patch:
            score = 20
            details = f"Patch version change: {previous_version} -> {new_version}"
        else:
            score = 50
            details = f"Version change: {previous_version or 'unknown'} -> {new_version}"
        
        # Adjust based on change details if provided
        if change_details:
            if change_details.get("database_migration"):
                score += 20
                details += " (includes database migration)"
            if change_details.get("config_change"):
                score += 10
                details += " (includes config changes)"
            if change_details.get("files_changed", 0) > 100:
                score += 15
                details += f" (large changeset: {change_details['files_changed']} files)"
        
        score = min(100, score)
        
        mitigations = []
        if score > 50:
            mitigations = [
                "Consider breaking into smaller deployments",
                "Test thoroughly in staging first",
                "Plan for extended monitoring period"
            ]
        
        return RiskFactor(
            name="change_magnitude",
            score=score,
            weight=self.weights["change_magnitude"],
            details=details,
            mitigations=mitigations
        )
    
    def _assess_deployment_timing(self) -> RiskFactor:
        """Assess risk based on deployment timing"""
        
        now = datetime.now(timezone.utc)
        hour = now.hour
        day = now.weekday()  # 0=Monday, 6=Sunday
        
        # High risk times
        is_friday = day == 4
        is_weekend = day >= 5
        is_late_night = hour >= 22 or hour < 6
        is_peak_hours = 9 <= hour <= 18 and day < 5
        
        if is_friday and hour >= 14:
            score = 85
            details = "Friday afternoon - high risk deployment window"
        elif is_weekend:
            score = 70
            details = "Weekend deployment - reduced support availability"
        elif is_late_night:
            score = 60
            details = "Late night deployment - reduced monitoring"
        elif is_peak_hours:
            score = 45
            details = "Peak hours - higher user impact potential"
        else:
            score = 20
            details = "Good deployment window"
        
        mitigations = []
        if score > 50:
            mitigations = [
                "Consider deploying during business hours",
                "Avoid Friday deployments when possible",
                "Ensure on-call coverage is available"
            ]
        
        return RiskFactor(
            name="deployment_timing",
            score=score,
            weight=self.weights["deployment_timing"],
            details=details,
            mitigations=mitigations
        )
    
    async def _assess_dependencies_health(self, service: str) -> RiskFactor:
        """Assess risk based on dependencies health"""
        
        # Common dependencies to check
        critical_dependencies = [
            "database-primary", "redis-cluster", "kafka-brokers",
            "api-gateway", "auth-service"
        ]
        
        unhealthy_deps = []
        
        for dep in critical_dependencies:
            if dep == service:
                continue
            
            try:
                anomalies = self.redis.lrange(f"recent_anomalies:{dep}", 0, 4)
                if len(anomalies) >= 3:
                    unhealthy_deps.append(dep)
            except:
                pass
        
        if len(unhealthy_deps) == 0:
            score = 15
            details = "All dependencies healthy"
        elif len(unhealthy_deps) == 1:
            score = 45
            details = f"1 dependency has issues: {unhealthy_deps[0]}"
        elif len(unhealthy_deps) <= 2:
            score = 65
            details = f"Multiple dependencies have issues: {', '.join(unhealthy_deps)}"
        else:
            score = 85
            details = f"Critical: {len(unhealthy_deps)} dependencies unhealthy"
        
        mitigations = []
        if unhealthy_deps:
            mitigations = [
                f"Wait for {dep} to stabilize" for dep in unhealthy_deps
            ]
        
        return RiskFactor(
            name="dependencies_health",
            score=score,
            weight=self.weights["dependencies_health"],
            details=details,
            mitigations=mitigations
        )
    
    def _assess_recent_incidents(self, service: str) -> RiskFactor:
        """Assess risk based on recent incidents"""
        
        try:
            # Get recent incidents
            incident_ids = self.redis.lrange(f"incident_history:{service}", 0, 9)
            
            # Count incidents in last 24 hours
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            recent_count = 0
            
            for inc_id in incident_ids:
                try:
                    inc_data = self.redis.get(f"incident_memory:{inc_id.decode()}")
                    if inc_data:
                        inc = json.loads(inc_data)
                        if inc.get("recorded_at", "") > cutoff:
                            recent_count += 1
                except:
                    continue
            
            if recent_count == 0:
                score = 10
                details = "No incidents in last 24 hours"
            elif recent_count == 1:
                score = 35
                details = "1 incident in last 24 hours"
            elif recent_count <= 3:
                score = 60
                details = f"{recent_count} incidents in last 24 hours"
            else:
                score = 85
                details = f"High incident rate: {recent_count} in last 24 hours"
            
            mitigations = []
            if score > 40:
                mitigations = [
                    "Review recent incidents before deploying",
                    "Ensure recent fixes are validated"
                ]
            
            return RiskFactor(
                name="recent_incidents",
                score=score,
                weight=self.weights["recent_incidents"],
                details=details,
                mitigations=mitigations
            )
            
        except Exception as e:
            return RiskFactor(
                name="recent_incidents",
                score=30,
                weight=self.weights["recent_incidents"],
                details=f"Unable to assess incidents: {e}",
                mitigations=[]
            )
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score"""
        
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    def _generate_recommendations(
        self,
        risk_factors: List[RiskFactor],
        overall_score: float,
        risk_level: RiskLevel
    ) -> List[str]:
        """Generate recommendations based on risk assessment"""
        
        recommendations = []
        
        # Overall recommendations
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("⛔ BLOCK: Risk score too high - deployment not recommended")
            recommendations.append("Address high-risk factors before proceeding")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("⚠️ Requires manual approval from senior engineer")
            recommendations.append("Enable intensive monitoring for 30 minutes post-deploy")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("✓ Deploy with enhanced monitoring")
            recommendations.append("Keep rollback ready for 15 minutes")
        else:
            recommendations.append("✓ Low risk - safe to deploy")
        
        # Add specific mitigations from high-risk factors
        for factor in sorted(risk_factors, key=lambda f: f.score, reverse=True):
            if factor.score >= 50 and factor.mitigations:
                recommendations.extend(factor.mitigations[:2])
        
        # Deduplicate while preserving order
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
        
        return unique_recs[:8]  # Limit to 8 recommendations
    
    def _get_past_failure_count(self, service: str) -> int:
        """Get count of past deployment failures"""
        try:
            history = self.redis.lrange(f"deployment_history:{service}", 0, -1)
            failures = 0
            for entry in history:
                try:
                    data = json.loads(entry)
                    if data.get("failed") or data.get("rolled_back"):
                        failures += 1
                except:
                    continue
            return failures
        except:
            return 0
    
    def _get_avg_recovery_time(self, service: str) -> float:
        """Get average recovery time for service"""
        try:
            incidents = self.redis.lrange(f"incident_history:{service}", 0, 19)
            recovery_times = []
            
            for inc_id in incidents:
                try:
                    inc_data = self.redis.get(f"incident_memory:{inc_id.decode()}")
                    if inc_data:
                        inc = json.loads(inc_data)
                        if inc.get("resolution_time_seconds"):
                            recovery_times.append(inc["resolution_time_seconds"] / 60)
                except:
                    continue
            
            return sum(recovery_times) / len(recovery_times) if recovery_times else 0
        except:
            return 0
    
    def _store_assessment(self, assessment: DeploymentRiskAssessment):
        """Store risk assessment for tracking"""
        try:
            key = f"risk_assessment:{assessment.deployment_id}"
            self.redis.setex(
                key,
                86400 * 7,  # Keep for 7 days
                json.dumps(asdict(assessment))
            )
            
            # Add to history
            self.redis.lpush(
                f"risk_assessments:{assessment.service}",
                json.dumps(asdict(assessment))
            )
            self.redis.ltrim(f"risk_assessments:{assessment.service}", 0, 99)
            
        except Exception as e:
            logger.error(f"[RISK] Failed to store assessment: {e}")
    
    async def should_auto_rollback(
        self,
        service: str,
        deployment_id: str,
        current_error_rate: float
    ) -> Tuple[bool, str]:
        """
        Check if automatic rollback should be triggered.
        
        Args:
            service: Service that was deployed
            deployment_id: Deployment identifier
            current_error_rate: Current error rate percentage
        
        Returns:
            Tuple of (should_rollback, reason)
        """
        
        # Get deployment assessment
        assessment_data = self.redis.get(f"risk_assessment:{deployment_id}")
        
        if not assessment_data:
            # No assessment found - use default threshold
            if current_error_rate >= self.auto_rollback_threshold:
                return True, f"Error rate {current_error_rate}% exceeds threshold"
            return False, "Within acceptable limits"
        
        assessment = json.loads(assessment_data)
        
        # Check if auto-rollback is enabled
        if not assessment.get("auto_rollback_enabled"):
            return False, "Auto-rollback not enabled for this deployment"
        
        # Dynamic threshold based on risk level
        risk_level = assessment.get("risk_level", "medium")
        
        thresholds = {
            "critical": 20,   # Very sensitive
            "high": 30,
            "medium": 50,
            "low": 70,
            "minimal": 90
        }
        
        threshold = thresholds.get(risk_level, 50)
        
        if current_error_rate >= threshold:
            return True, (
                f"Error rate {current_error_rate}% exceeds threshold {threshold}% "
                f"for {risk_level} risk deployment"
            )
        
        return False, f"Error rate {current_error_rate}% within acceptable range"
    
    def get_risk_stats(self) -> Dict:
        """Get deployment risk statistics"""
        
        try:
            # Get all assessments
            all_assessments = []
            for key in self.redis.scan_iter("risk_assessments:*"):
                assessments = self.redis.lrange(key, 0, 19)
                for a in assessments:
                    try:
                        all_assessments.append(json.loads(a))
                    except:
                        continue
            
            if not all_assessments:
                return {"message": "No risk assessments available"}
            
            # Calculate stats
            total = len(all_assessments)
            avg_score = sum(a.get("overall_risk_score", 0) for a in all_assessments) / total
            
            by_level = {}
            for a in all_assessments:
                level = a.get("risk_level", "unknown")
                by_level[level] = by_level.get(level, 0) + 1
            
            blocked = sum(1 for a in all_assessments if not a.get("should_proceed"))
            approved = total - blocked
            
            return {
                "total_assessments": total,
                "average_risk_score": round(avg_score, 1),
                "by_risk_level": by_level,
                "deployments_blocked": blocked,
                "deployments_approved": approved,
                "block_rate": round(blocked / total * 100, 1) if total > 0 else 0
            }
            
        except Exception as e:
            return {"error": str(e)}


# Convenience function
async def assess_deployment(
    redis_client,
    service: str,
    new_version: str,
    previous_version: Optional[str] = None
) -> DeploymentRiskAssessment:
    """Quick function to assess deployment risk"""
    analyzer = DeploymentRiskAnalyzer(redis_client)
    return await analyzer.assess_deployment_risk(
        service, new_version, previous_version
    )
