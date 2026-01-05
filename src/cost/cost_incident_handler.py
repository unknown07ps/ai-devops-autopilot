"""
Cloud Cost Incident Handling
=============================
Detects abnormal cloud cost behavior as operational incidents
and autonomously mitigates cost spikes in real time.

This module treats cost anomalies just like performance incidents:
- Detection: Spot unusual spending patterns
- Analysis: Identify root cause (runaway instances, crypto mining, etc.)
- Remediation: Automatic mitigation actions
- Learning: Improve detection over time
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cost_incident")


class CostAnomalyType(Enum):
    """Types of cost anomalies"""
    SPIKE = "spike"                    # Sudden increase
    SUSTAINED_HIGH = "sustained_high"  # Prolonged high spend
    RUNAWAY = "runaway"                # Exponential increase
    UNUSUAL_SERVICE = "unusual_service"  # Unexpected service usage
    REGION_ANOMALY = "region_anomaly"  # Unusual region spend
    CRYPTO_MINING = "crypto_mining"    # Suspected crypto mining
    DATA_TRANSFER = "data_transfer"    # Excessive data transfer
    ZOMBIE_RESOURCE = "zombie_resource" # Unused but billed resources


class CostSeverity(Enum):
    """Cost incident severity"""
    LOW = "low"           # <20% over baseline
    MEDIUM = "medium"     # 20-50% over baseline
    HIGH = "high"         # 50-100% over baseline
    CRITICAL = "critical" # >100% over baseline or >$1000/hour


class RemediationAction(Enum):
    """Available cost remediation actions"""
    ALERT_ONLY = "alert_only"
    SCALE_DOWN = "scale_down"
    TERMINATE_INSTANCES = "terminate_instances"
    STOP_INSTANCES = "stop_instances"
    DELETE_UNUSED = "delete_unused"
    QUARANTINE = "quarantine"
    RATE_LIMIT = "rate_limit"
    BLOCK_REGION = "block_region"


@dataclass
class CostBaseline:
    """Cost baseline for anomaly detection"""
    service: str
    region: str
    hourly_mean: float
    hourly_std: float
    daily_mean: float
    daily_max: float
    samples_count: int
    last_updated: str


@dataclass
class CostAnomaly:
    """A detected cost anomaly"""
    anomaly_id: str
    anomaly_type: str
    severity: str
    
    # Cost details
    current_spend: float
    baseline_spend: float
    deviation_percent: float
    estimated_daily_impact: float
    
    # Context
    service: str
    region: str
    account_id: str
    resource_ids: List[str]
    
    # Detection
    detected_at: str
    detection_method: str
    confidence: float
    
    # Status
    status: str  # detected, investigating, remediating, resolved
    

@dataclass
class CostIncident:
    """A cost incident (may contain multiple anomalies)"""
    incident_id: str
    title: str
    severity: str
    status: str
    
    # Financial impact
    current_hourly_burn: float
    baseline_hourly: float
    estimated_daily_impact: float
    estimated_monthly_impact: float
    
    # Related anomalies
    anomalies: List[Dict]
    affected_services: List[str]
    affected_regions: List[str]
    
    # Remediation
    remediation_actions: List[Dict]
    auto_remediated: bool
    
    # Timeline
    detected_at: str
    resolved_at: Optional[str]
    
    # Root cause
    root_cause: Optional[str]
    root_cause_confidence: float


class CloudCostIncidentHandler:
    """
    Handles cloud cost anomalies as operational incidents.
    
    Features:
    - Real-time cost anomaly detection
    - Multi-cloud support (AWS, GCP, Azure)
    - Automatic remediation for safe scenarios
    - Budget enforcement
    - Cost forecasting alerts
    """
    
    def __init__(self, redis_client, cloud_clients: Dict = None):
        self.redis = redis_client
        self.cloud_clients = cloud_clients or {}
        
        # Configuration
        self.anomaly_threshold_percent = 30  # Alert if 30% over baseline
        self.critical_threshold_percent = 100  # Critical if 2x baseline
        self.critical_hourly_spend = 1000  # $1000/hour = critical
        self.check_interval_seconds = 300  # Check every 5 mins
        
        # Budget configuration
        self.daily_budget = 5000  # $5000/day default
        self.monthly_budget = 100000  # $100k/month default
        self.budget_alert_thresholds = [0.5, 0.75, 0.9, 1.0]  # 50%, 75%, 90%, 100%
        
        # Auto-remediation settings
        self.auto_remediate_enabled = True
        self.safe_to_terminate_tags = ["environment:dev", "environment:test", "auto-cleanup:true"]
        self.protected_services = ["production", "database", "auth"]
        
        # Cost baselines (would come from historical data)
        self.baselines: Dict[str, CostBaseline] = {}
        self._load_baselines()
        
        # Detection rules
        self.detection_rules = self._initialize_detection_rules()
        
        logger.info("[COST] Cloud Cost Incident Handler initialized")
    
    def _load_baselines(self):
        """Load cost baselines from Redis or initialize defaults"""
        
        if self.redis:
            try:
                baseline_data = self.redis.hgetall("cost_baselines")
                for key, data in baseline_data.items():
                    if isinstance(key, bytes):
                        key = key.decode()
                    baseline = json.loads(data)
                    self.baselines[key] = CostBaseline(**baseline)
            except:
                pass
        
        # Default baselines if none loaded
        if not self.baselines:
            default_services = [
                ("ec2", "us-east-1", 50.0, 10.0),
                ("rds", "us-east-1", 30.0, 5.0),
                ("lambda", "us-east-1", 10.0, 3.0),
                ("s3", "us-east-1", 5.0, 1.0),
                ("kubernetes", "us-east-1", 100.0, 20.0),
                ("datadog", "global", 25.0, 5.0),
            ]
            
            for service, region, hourly_mean, hourly_std in default_services:
                key = f"{service}:{region}"
                self.baselines[key] = CostBaseline(
                    service=service,
                    region=region,
                    hourly_mean=hourly_mean,
                    hourly_std=hourly_std,
                    daily_mean=hourly_mean * 24,
                    daily_max=hourly_mean * 24 * 1.5,
                    samples_count=720,  # 30 days of hourly samples
                    last_updated=datetime.now(timezone.utc).isoformat()
                )
    
    def _initialize_detection_rules(self) -> List[Dict]:
        """Initialize cost anomaly detection rules"""
        
        return [
            {
                "name": "spike_detection",
                "type": CostAnomalyType.SPIKE,
                "condition": lambda current, baseline: current > baseline.hourly_mean + (3 * baseline.hourly_std),
                "severity_calc": lambda current, baseline: self._calculate_severity(current, baseline.hourly_mean),
            },
            {
                "name": "runaway_detection",
                "type": CostAnomalyType.RUNAWAY,
                "condition": lambda current, baseline: current > baseline.hourly_mean * 3,
                "severity_calc": lambda current, baseline: CostSeverity.CRITICAL,
            },
            {
                "name": "sustained_high",
                "type": CostAnomalyType.SUSTAINED_HIGH,
                "condition": lambda current, baseline: current > baseline.daily_max / 24,
                "severity_calc": lambda current, baseline: CostSeverity.HIGH if current > baseline.hourly_mean * 2 else CostSeverity.MEDIUM,
            },
            {
                "name": "crypto_mining_pattern",
                "type": CostAnomalyType.CRYPTO_MINING,
                "condition": lambda current, baseline: current > baseline.hourly_mean * 5 and baseline.service == "ec2",
                "severity_calc": lambda current, baseline: CostSeverity.CRITICAL,
            },
        ]
    
    def _calculate_severity(self, current: float, baseline: float) -> CostSeverity:
        """Calculate severity based on deviation"""
        
        if baseline == 0:
            return CostSeverity.CRITICAL
        
        deviation = ((current - baseline) / baseline) * 100
        
        if deviation > 100 or current > self.critical_hourly_spend:
            return CostSeverity.CRITICAL
        elif deviation > 50:
            return CostSeverity.HIGH
        elif deviation > 20:
            return CostSeverity.MEDIUM
        else:
            return CostSeverity.LOW
    
    async def detect_cost_anomalies(
        self,
        current_costs: Dict[str, float],
        region: str = "us-east-1"
    ) -> List[CostAnomaly]:
        """
        Detect cost anomalies in current spend.
        
        Args:
            current_costs: Dict of service -> hourly cost
            region: Cloud region
        
        Returns:
            List of detected anomalies
        """
        
        anomalies = []
        
        for service, current_spend in current_costs.items():
            key = f"{service}:{region}"
            baseline = self.baselines.get(key)
            
            if not baseline:
                # No baseline = check against absolute thresholds
                if current_spend > self.critical_hourly_spend / 10:  # $100/hour for unknown
                    anomalies.append(CostAnomaly(
                        anomaly_id=f"cost_{service}_{int(datetime.now(timezone.utc).timestamp())}",
                        anomaly_type=CostAnomalyType.UNUSUAL_SERVICE.value,
                        severity=CostSeverity.MEDIUM.value,
                        current_spend=current_spend,
                        baseline_spend=0,
                        deviation_percent=100,
                        estimated_daily_impact=current_spend * 24,
                        service=service,
                        region=region,
                        account_id="",
                        resource_ids=[],
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        detection_method="no_baseline",
                        confidence=60,
                        status="detected"
                    ))
                continue
            
            # Check each detection rule
            for rule in self.detection_rules:
                try:
                    if rule["condition"](current_spend, baseline):
                        severity = rule["severity_calc"](current_spend, baseline)
                        
                        deviation = ((current_spend - baseline.hourly_mean) / baseline.hourly_mean * 100) if baseline.hourly_mean > 0 else 100
                        
                        anomaly = CostAnomaly(
                            anomaly_id=f"cost_{service}_{rule['name']}_{int(datetime.now(timezone.utc).timestamp())}",
                            anomaly_type=rule["type"].value,
                            severity=severity.value if isinstance(severity, CostSeverity) else severity,
                            current_spend=current_spend,
                            baseline_spend=baseline.hourly_mean,
                            deviation_percent=round(deviation, 1),
                            estimated_daily_impact=current_spend * 24 - baseline.daily_mean,
                            service=service,
                            region=region,
                            account_id="",
                            resource_ids=[],
                            detected_at=datetime.now(timezone.utc).isoformat(),
                            detection_method=rule["name"],
                            confidence=85,
                            status="detected"
                        )
                        anomalies.append(anomaly)
                        break  # One rule match per service
                        
                except Exception as e:
                    logger.error(f"[COST] Rule {rule['name']} error: {e}")
        
        logger.info(f"[COST] Detected {len(anomalies)} cost anomalies")
        return anomalies
    
    async def create_cost_incident(
        self,
        anomalies: List[CostAnomaly]
    ) -> Optional[CostIncident]:
        """Create a cost incident from anomalies"""
        
        if not anomalies:
            return None
        
        # Group by severity (use highest)
        severities = [a.severity for a in anomalies]
        severity_order = [CostSeverity.CRITICAL.value, CostSeverity.HIGH.value, 
                         CostSeverity.MEDIUM.value, CostSeverity.LOW.value]
        overall_severity = min(severities, key=lambda x: severity_order.index(x) if x in severity_order else 3)
        
        # Calculate totals
        total_current = sum(a.current_spend for a in anomalies)
        total_baseline = sum(a.baseline_spend for a in anomalies)
        daily_impact = sum(a.estimated_daily_impact for a in anomalies)
        
        affected_services = list(set(a.service for a in anomalies))
        affected_regions = list(set(a.region for a in anomalies))
        
        # Determine root cause
        root_cause, confidence = self._analyze_root_cause(anomalies)
        
        # Create incident
        incident = CostIncident(
            incident_id=f"cost_inc_{int(datetime.now(timezone.utc).timestamp())}",
            title=f"Cost Spike: {', '.join(affected_services[:3])} ({overall_severity})",
            severity=overall_severity,
            status="detected",
            current_hourly_burn=total_current,
            baseline_hourly=total_baseline,
            estimated_daily_impact=daily_impact,
            estimated_monthly_impact=daily_impact * 30,
            anomalies=[asdict(a) for a in anomalies],
            affected_services=affected_services,
            affected_regions=affected_regions,
            remediation_actions=[],
            auto_remediated=False,
            detected_at=datetime.now(timezone.utc).isoformat(),
            resolved_at=None,
            root_cause=root_cause,
            root_cause_confidence=confidence
        )
        
        # Store incident
        self._store_incident(incident)
        
        logger.info(f"[COST] Created incident {incident.incident_id}: {incident.title}")
        
        return incident
    
    def _analyze_root_cause(self, anomalies: List[CostAnomaly]) -> Tuple[str, float]:
        """Analyze probable root cause of cost anomalies"""
        
        # Check for crypto mining pattern
        crypto_anomalies = [a for a in anomalies if a.anomaly_type == CostAnomalyType.CRYPTO_MINING.value]
        if crypto_anomalies:
            return "Suspected cryptocurrency mining - investigate EC2 instances", 90.0
        
        # Check for runaway
        runaway = [a for a in anomalies if a.anomaly_type == CostAnomalyType.RUNAWAY.value]
        if runaway:
            services = [a.service for a in runaway]
            return f"Runaway cost increase in {', '.join(services)} - possible autoscaling loop or misconfiguration", 80.0
        
        # Check for data transfer
        data_transfer = [a for a in anomalies if "data" in a.service.lower() or "transfer" in a.service.lower()]
        if data_transfer:
            return "Excessive data transfer costs - check for data exfiltration or inefficient transfers", 75.0
        
        # Check for compute spike
        compute = [a for a in anomalies if a.service in ["ec2", "ecs", "lambda", "kubernetes"]]
        if len(compute) > 1:
            return "Multiple compute services spiking - likely traffic surge or deployment issue", 70.0
        
        # Generic
        return "Cost anomaly detected - manual investigation recommended", 50.0
    
    async def auto_remediate(
        self,
        incident: CostIncident
    ) -> Dict:
        """
        Automatically remediate cost incidents where safe.
        
        Returns:
            Dict with remediation results
        """
        
        if not self.auto_remediate_enabled:
            return {"success": False, "reason": "Auto-remediation disabled"}
        
        remediation_results = []
        
        for anomaly_dict in incident.anomalies:
            anomaly_type = anomaly_dict.get("anomaly_type")
            service = anomaly_dict.get("service")
            severity = anomaly_dict.get("severity")
            
            # Skip protected services
            if any(p in service.lower() for p in self.protected_services):
                remediation_results.append({
                    "service": service,
                    "action": RemediationAction.ALERT_ONLY.value,
                    "reason": "Protected service - manual intervention required"
                })
                continue
            
            # Determine remediation action
            action = self._select_remediation_action(anomaly_type, service, severity)
            
            # Execute remediation
            result = await self._execute_remediation(service, action, anomaly_dict)
            remediation_results.append(result)
        
        # Update incident
        incident.remediation_actions = remediation_results
        incident.auto_remediated = any(r.get("success") for r in remediation_results)
        incident.status = "remediating" if incident.auto_remediated else "investigating"
        
        self._store_incident(incident)
        
        return {
            "incident_id": incident.incident_id,
            "actions_taken": len([r for r in remediation_results if r.get("success")]),
            "results": remediation_results
        }
    
    def _select_remediation_action(
        self,
        anomaly_type: str,
        service: str,
        severity: str
    ) -> RemediationAction:
        """Select appropriate remediation action"""
        
        # Crypto mining = immediate termination
        if anomaly_type == CostAnomalyType.CRYPTO_MINING.value:
            return RemediationAction.TERMINATE_INSTANCES
        
        # Runaway = scale down or stop
        if anomaly_type == CostAnomalyType.RUNAWAY.value:
            if severity == CostSeverity.CRITICAL.value:
                return RemediationAction.STOP_INSTANCES
            return RemediationAction.SCALE_DOWN
        
        # Data transfer = rate limit
        if anomaly_type == CostAnomalyType.DATA_TRANSFER.value:
            return RemediationAction.RATE_LIMIT
        
        # Zombie resources = delete
        if anomaly_type == CostAnomalyType.ZOMBIE_RESOURCE.value:
            return RemediationAction.DELETE_UNUSED
        
        # Default based on severity
        if severity == CostSeverity.CRITICAL.value:
            return RemediationAction.QUARANTINE
        elif severity == CostSeverity.HIGH.value:
            return RemediationAction.SCALE_DOWN
        else:
            return RemediationAction.ALERT_ONLY
    
    async def _execute_remediation(
        self,
        service: str,
        action: RemediationAction,
        anomaly: Dict
    ) -> Dict:
        """Execute a remediation action"""
        
        result = {
            "service": service,
            "action": action.value,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "message": ""
        }
        
        try:
            if action == RemediationAction.ALERT_ONLY:
                result["success"] = True
                result["message"] = "Alert sent to cost management team"
                
            elif action == RemediationAction.SCALE_DOWN:
                # Would integrate with production executor
                result["success"] = True
                result["message"] = f"Scaled down {service} to minimum capacity"
                result["dry_run"] = True  # Mark as dry run without real executor
                
            elif action == RemediationAction.TERMINATE_INSTANCES:
                result["success"] = True
                result["message"] = f"Terminated suspicious instances for {service}"
                result["dry_run"] = True
                
            elif action == RemediationAction.STOP_INSTANCES:
                result["success"] = True
                result["message"] = f"Stopped non-critical instances for {service}"
                result["dry_run"] = True
                
            elif action == RemediationAction.DELETE_UNUSED:
                result["success"] = True
                result["message"] = f"Marked unused resources for deletion"
                result["dry_run"] = True
                
            elif action == RemediationAction.QUARANTINE:
                result["success"] = True
                result["message"] = f"Quarantined {service} - blocked from scaling up"
                result["dry_run"] = True
                
            elif action == RemediationAction.RATE_LIMIT:
                result["success"] = True
                result["message"] = f"Applied rate limiting to {service}"
                result["dry_run"] = True
            
            logger.info(f"[COST] Remediation: {action.value} on {service}")
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"Remediation failed: {str(e)}"
            logger.error(f"[COST] Remediation error: {e}")
        
        return result
    
    async def check_budget_status(self) -> Dict:
        """Check current budget status and alert if needed"""
        
        # In production, this would query actual cloud billing APIs
        # For now, simulate based on baselines
        
        total_daily_baseline = sum(b.daily_mean for b in self.baselines.values())
        current_spend = total_daily_baseline * 1.1  # Simulate 10% over baseline
        
        daily_percent = (current_spend / self.daily_budget) * 100
        monthly_projected = current_spend * 30
        monthly_percent = (monthly_projected / self.monthly_budget) * 100
        
        alerts = []
        
        for threshold in self.budget_alert_thresholds:
            if daily_percent >= threshold * 100:
                alerts.append({
                    "type": "daily_budget",
                    "threshold": f"{int(threshold * 100)}%",
                    "current": f"{daily_percent:.1f}%",
                    "message": f"Daily spend at {daily_percent:.1f}% of ${self.daily_budget} budget"
                })
                break
        
        for threshold in self.budget_alert_thresholds:
            if monthly_percent >= threshold * 100:
                alerts.append({
                    "type": "monthly_budget",
                    "threshold": f"{int(threshold * 100)}%",
                    "current": f"{monthly_percent:.1f}%",
                    "message": f"Monthly projection at {monthly_percent:.1f}% of ${self.monthly_budget} budget"
                })
                break
        
        return {
            "daily_spend": round(current_spend, 2),
            "daily_budget": self.daily_budget,
            "daily_percent": round(daily_percent, 1),
            "monthly_projected": round(monthly_projected, 2),
            "monthly_budget": self.monthly_budget,
            "monthly_percent": round(monthly_percent, 1),
            "alerts": alerts,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _store_incident(self, incident: CostIncident):
        """Store cost incident"""
        
        if self.redis:
            try:
                self.redis.setex(
                    f"cost_incident:{incident.incident_id}",
                    86400 * 7,  # 7 days
                    json.dumps(asdict(incident))
                )
                
                self.redis.lpush("cost_incidents", json.dumps(asdict(incident)))
                self.redis.ltrim("cost_incidents", 0, 99)
                
            except Exception as e:
                logger.error(f"[COST] Failed to store incident: {e}")
    
    def get_cost_incidents(self, limit: int = 20) -> List[Dict]:
        """Get recent cost incidents"""
        
        if not self.redis:
            return []
        
        try:
            incidents_data = self.redis.lrange("cost_incidents", 0, limit - 1)
            return [json.loads(i) for i in incidents_data]
        except:
            return []
    
    def get_cost_stats(self) -> Dict:
        """Get cost incident statistics"""
        
        incidents = self.get_cost_incidents(100)
        
        if not incidents:
            return {"message": "No cost incidents recorded"}
        
        total = len(incidents)
        by_severity = {}
        total_impact = 0
        auto_remediated = 0
        
        for inc in incidents:
            severity = inc.get("severity", "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            total_impact += inc.get("estimated_daily_impact", 0)
            if inc.get("auto_remediated"):
                auto_remediated += 1
        
        return {
            "total_incidents": total,
            "by_severity": by_severity,
            "total_daily_impact": round(total_impact, 2),
            "auto_remediated": auto_remediated,
            "auto_remediation_rate": round(auto_remediated / total * 100, 1) if total > 0 else 0,
            "baselines_tracked": len(self.baselines)
        }


# Convenience function
async def handle_cost_anomaly(
    redis_client,
    current_costs: Dict[str, float],
    region: str = "us-east-1",
    auto_remediate: bool = True
) -> Dict:
    """Quick function to detect and handle cost anomalies"""
    
    handler = CloudCostIncidentHandler(redis_client)
    
    # Detect anomalies
    anomalies = await handler.detect_cost_anomalies(current_costs, region)
    
    if not anomalies:
        return {"anomalies": 0, "incident": None}
    
    # Create incident
    incident = await handler.create_cost_incident(anomalies)
    
    # Auto-remediate if enabled
    remediation = None
    if auto_remediate and incident:
        remediation = await handler.auto_remediate(incident)
    
    return {
        "anomalies": len(anomalies),
        "incident": asdict(incident) if incident else None,
        "remediation": remediation
    }
