"""
MTTR Acceleration Engine
=========================
Performs parallel analysis to reduce Mean Time To Resolution during incidents.
Executes concurrent root-cause analysis and remediation planning.

This module accelerates incident resolution by:
- Running multiple analysis strategies in parallel
- Gathering data from multiple sources concurrently
- Preparing remediation options before analysis completes
- Pre-warming likely fixes
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mttr_engine")


class AnalysisStrategy(Enum):
    """Root cause analysis strategies"""
    LOG_ANALYSIS = "log_analysis"
    METRIC_CORRELATION = "metric_correlation"
    DEPLOYMENT_CORRELATION = "deployment_correlation"
    DEPENDENCY_CHECK = "dependency_check"
    PATTERN_MATCHING = "pattern_matching"
    AI_INFERENCE = "ai_inference"
    HISTORICAL_LOOKUP = "historical_lookup"


class RemediationPhase(Enum):
    """Phases of remediation"""
    DIAGNOSIS = "diagnosis"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    VERIFICATION = "verification"


@dataclass
class AnalysisResult:
    """Result from one analysis strategy"""
    strategy: str
    success: bool
    confidence: float
    
    root_cause: Optional[str]
    contributing_factors: List[str]
    evidence: List[Dict]
    
    execution_time_ms: float
    error: Optional[str] = None


@dataclass
class RemediationPlan:
    """Pre-computed remediation plan"""
    plan_id: str
    action_type: str
    priority: int
    
    prerequisites: List[str]
    steps: List[Dict]
    rollback_steps: List[Dict]
    
    estimated_impact: str
    estimated_time_minutes: float
    risk_level: str
    
    ready_to_execute: bool


@dataclass
class AcceleratedResolution:
    """Complete accelerated resolution package"""
    resolution_id: str
    incident_id: str
    
    # Timing
    started_at: str
    completed_at: str
    total_time_ms: float
    parallel_speedup: float  # vs sequential
    
    # Analysis results
    analysis_results: List[Dict]
    consensus_root_cause: str
    consensus_confidence: float
    
    # Remediation
    remediation_plans: List[Dict]
    recommended_plan_id: str
    
    # Status
    ready_for_execution: bool


class MTTRAccelerator:
    """
    Accelerates Mean Time To Resolution through parallel processing.
    
    Features:
    - Parallel multi-strategy root cause analysis
    - Concurrent data gathering
    - Speculative remediation planning
    - Pre-warmed action preparation
    """
    
    def __init__(self, redis_client, analyzers: Dict = None):
        self.redis = redis_client
        self.analyzers = analyzers or {}
        
        # Configuration
        self.analysis_timeout_seconds = 30
        self.max_parallel_strategies = 7
        self.min_confidence_for_consensus = 60
        
        # Pre-registered analysis strategies
        self.strategies = {
            AnalysisStrategy.LOG_ANALYSIS: self._analyze_logs,
            AnalysisStrategy.METRIC_CORRELATION: self._analyze_metrics,
            AnalysisStrategy.DEPLOYMENT_CORRELATION: self._analyze_deployments,
            AnalysisStrategy.DEPENDENCY_CHECK: self._check_dependencies,
            AnalysisStrategy.PATTERN_MATCHING: self._match_patterns,
            AnalysisStrategy.HISTORICAL_LOOKUP: self._lookup_history,
        }
        
        # Pre-registered remediation generators
        self.remediation_generators = {
            "deployment_issue": self._plan_rollback,
            "resource_exhaustion": self._plan_scale_up,
            "memory_issue": self._plan_restart,
            "dependency_failure": self._plan_circuit_breaker,
            "configuration_error": self._plan_config_rollback,
        }
        
        logger.info("[MTTR] Acceleration Engine initialized")
    
    async def accelerate_resolution(
        self,
        incident_id: str,
        service: str,
        symptoms: Dict,
        context: Dict = None
    ) -> AcceleratedResolution:
        """
        Run accelerated parallel analysis and remediation planning.
        
        This is the main entry point that runs everything in parallel
        to minimize MTTR.
        """
        
        start_time = time.time()
        context = context or {}
        
        logger.info(f"[MTTR] Starting accelerated resolution for {incident_id}")
        
        # Phase 1: Parallel data gathering
        data_task = asyncio.create_task(
            self._gather_all_data(service, context)
        )
        
        # Phase 2: Run all analysis strategies in parallel
        analysis_tasks = [
            self._run_analysis_strategy(strategy, service, symptoms, context)
            for strategy in self.strategies.keys()
        ]
        
        # Phase 3: Speculatively prepare remediations for common causes
        remediation_tasks = [
            self._prepare_remediation(cause_type, service)
            for cause_type in self.remediation_generators.keys()
        ]
        
        # Execute all in parallel with timeout
        try:
            all_results = await asyncio.wait_for(
                asyncio.gather(
                    data_task,
                    *analysis_tasks,
                    *remediation_tasks,
                    return_exceptions=True
                ),
                timeout=self.analysis_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning("[MTTR] Analysis timeout - using partial results")
            all_results = []
        
        # Separate results
        gathered_data = all_results[0] if all_results else {}
        analysis_results = [
            r for r in all_results[1:len(self.strategies)+1]
            if isinstance(r, AnalysisResult)
        ]
        remediation_plans = [
            r for r in all_results[len(self.strategies)+1:]
            if isinstance(r, RemediationPlan)
        ]
        
        # Build consensus from parallel analysis
        consensus_cause, consensus_confidence = self._build_consensus(analysis_results)
        
        # Rank remediation plans based on consensus
        ranked_plans = self._rank_remediations(remediation_plans, consensus_cause)
        
        # Calculate timing
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        
        # Estimate sequential time (sum of all individual times)
        sequential_time = sum(
            r.execution_time_ms for r in analysis_results
        )
        parallel_speedup = sequential_time / total_time_ms if total_time_ms > 0 else 1
        
        # Build resolution package
        resolution = AcceleratedResolution(
            resolution_id=f"res_{incident_id}_{int(start_time)}",
            incident_id=incident_id,
            started_at=datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            total_time_ms=round(total_time_ms, 1),
            parallel_speedup=round(parallel_speedup, 2),
            analysis_results=[asdict(r) for r in analysis_results],
            consensus_root_cause=consensus_cause,
            consensus_confidence=consensus_confidence,
            remediation_plans=[asdict(p) for p in ranked_plans],
            recommended_plan_id=ranked_plans[0].plan_id if ranked_plans else None,
            ready_for_execution=consensus_confidence >= self.min_confidence_for_consensus
        )
        
        # Store resolution
        self._store_resolution(resolution)
        
        logger.info(
            f"[MTTR] Resolution complete: {total_time_ms:.0f}ms "
            f"({parallel_speedup:.1f}x speedup), "
            f"confidence: {consensus_confidence:.0f}%"
        )
        
        return resolution
    
    async def _gather_all_data(
        self,
        service: str,
        context: Dict
    ) -> Dict:
        """Gather all relevant data in parallel"""
        
        async def get_logs():
            try:
                logs = self.redis.lrange(f"logs:{service}", 0, 99)
                return [json.loads(l) for l in logs]
            except:
                return []
        
        async def get_metrics():
            try:
                metrics = self.redis.get(f"metrics:{service}")
                return json.loads(metrics) if metrics else {}
            except:
                return {}
        
        async def get_deployments():
            try:
                deploys = self.redis.zrangebyscore(
                    f"deployments:{service}",
                    time.time() - 3600,  # Last hour
                    "+inf"
                )
                return [d.decode() if isinstance(d, bytes) else d for d in deploys]
            except:
                return []
        
        async def get_alerts():
            try:
                alerts = self.redis.lrange(f"alerts:{service}", 0, 49)
                return [json.loads(a) for a in alerts]
            except:
                return []
        
        # Run all data gathering in parallel
        logs, metrics, deployments, alerts = await asyncio.gather(
            get_logs(),
            get_metrics(),
            get_deployments(),
            get_alerts(),
            return_exceptions=True
        )
        
        return {
            "logs": logs if not isinstance(logs, Exception) else [],
            "metrics": metrics if not isinstance(metrics, Exception) else {},
            "deployments": deployments if not isinstance(deployments, Exception) else [],
            "alerts": alerts if not isinstance(alerts, Exception) else []
        }
    
    async def _run_analysis_strategy(
        self,
        strategy: AnalysisStrategy,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Run a single analysis strategy"""
        
        start = time.time()
        
        try:
            analyzer = self.strategies.get(strategy)
            if analyzer:
                result = await analyzer(service, symptoms, context)
                result.execution_time_ms = (time.time() - start) * 1000
                return result
            else:
                return AnalysisResult(
                    strategy=strategy.value,
                    success=False,
                    confidence=0,
                    root_cause=None,
                    contributing_factors=[],
                    evidence=[],
                    execution_time_ms=(time.time() - start) * 1000,
                    error="Strategy not implemented"
                )
        except Exception as e:
            return AnalysisResult(
                strategy=strategy.value,
                success=False,
                confidence=0,
                root_cause=None,
                contributing_factors=[],
                evidence=[],
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def _analyze_logs(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Analyze logs for root cause"""
        
        # Simulate log analysis
        await asyncio.sleep(0.1)  # Simulated processing
        
        error_patterns = symptoms.get("error_patterns", [])
        
        if "OutOfMemoryError" in str(error_patterns):
            return AnalysisResult(
                strategy=AnalysisStrategy.LOG_ANALYSIS.value,
                success=True,
                confidence=85,
                root_cause="Memory exhaustion - OOM errors detected",
                contributing_factors=["High memory usage", "Possible memory leak"],
                evidence=[{"type": "log", "pattern": "OutOfMemoryError"}],
                execution_time_ms=0
            )
        
        if "Connection refused" in str(error_patterns):
            return AnalysisResult(
                strategy=AnalysisStrategy.LOG_ANALYSIS.value,
                success=True,
                confidence=75,
                root_cause="Dependency unavailable",
                contributing_factors=["Connection failures to downstream service"],
                evidence=[{"type": "log", "pattern": "Connection refused"}],
                execution_time_ms=0
            )
        
        return AnalysisResult(
            strategy=AnalysisStrategy.LOG_ANALYSIS.value,
            success=True,
            confidence=40,
            root_cause=None,
            contributing_factors=["No clear error pattern found"],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _analyze_metrics(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Correlate metrics for root cause"""
        
        await asyncio.sleep(0.05)
        
        cpu = symptoms.get("cpu_usage", 0)
        memory = symptoms.get("memory_usage", 0)
        latency = symptoms.get("latency_p99_ms", 0)
        
        if memory > 90:
            return AnalysisResult(
                strategy=AnalysisStrategy.METRIC_CORRELATION.value,
                success=True,
                confidence=80,
                root_cause="Memory exhaustion",
                contributing_factors=[f"Memory at {memory}%"],
                evidence=[{"type": "metric", "name": "memory", "value": memory}],
                execution_time_ms=0
            )
        
        if cpu > 90:
            return AnalysisResult(
                strategy=AnalysisStrategy.METRIC_CORRELATION.value,
                success=True,
                confidence=75,
                root_cause="CPU exhaustion",
                contributing_factors=[f"CPU at {cpu}%"],
                evidence=[{"type": "metric", "name": "cpu", "value": cpu}],
                execution_time_ms=0
            )
        
        if latency > 5000:
            return AnalysisResult(
                strategy=AnalysisStrategy.METRIC_CORRELATION.value,
                success=True,
                confidence=70,
                root_cause="High latency - possible bottleneck",
                contributing_factors=[f"P99 latency at {latency}ms"],
                evidence=[{"type": "metric", "name": "latency", "value": latency}],
                execution_time_ms=0
            )
        
        return AnalysisResult(
            strategy=AnalysisStrategy.METRIC_CORRELATION.value,
            success=True,
            confidence=30,
            root_cause=None,
            contributing_factors=[],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _analyze_deployments(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Check for deployment correlation"""
        
        await asyncio.sleep(0.05)
        
        recent_deploy = context.get("recent_deployment", False)
        deploy_age_min = context.get("deployment_age_minutes", 999)
        
        if recent_deploy and deploy_age_min < 30:
            return AnalysisResult(
                strategy=AnalysisStrategy.DEPLOYMENT_CORRELATION.value,
                success=True,
                confidence=85,
                root_cause=f"Recent deployment ({deploy_age_min}min ago) correlates with issue",
                contributing_factors=["Issues started after deployment"],
                evidence=[{"type": "deployment", "age_minutes": deploy_age_min}],
                execution_time_ms=0
            )
        
        return AnalysisResult(
            strategy=AnalysisStrategy.DEPLOYMENT_CORRELATION.value,
            success=True,
            confidence=20,
            root_cause=None,
            contributing_factors=["No recent deployments"],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _check_dependencies(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Check dependency health"""
        
        await asyncio.sleep(0.05)
        
        unhealthy_deps = context.get("unhealthy_dependencies", [])
        
        if unhealthy_deps:
            return AnalysisResult(
                strategy=AnalysisStrategy.DEPENDENCY_CHECK.value,
                success=True,
                confidence=80,
                root_cause=f"Dependency failure: {unhealthy_deps[0]}",
                contributing_factors=[f"{len(unhealthy_deps)} dependencies unhealthy"],
                evidence=[{"type": "dependency", "unhealthy": unhealthy_deps}],
                execution_time_ms=0
            )
        
        return AnalysisResult(
            strategy=AnalysisStrategy.DEPENDENCY_CHECK.value,
            success=True,
            confidence=25,
            root_cause=None,
            contributing_factors=["All dependencies healthy"],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _match_patterns(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Match against known incident patterns"""
        
        await asyncio.sleep(0.05)
        
        # Simplified pattern matching
        error_rate = symptoms.get("error_rate", 0)
        
        if error_rate > 20:
            return AnalysisResult(
                strategy=AnalysisStrategy.PATTERN_MATCHING.value,
                success=True,
                confidence=70,
                root_cause="High error rate pattern - likely code or data issue",
                contributing_factors=[f"Error rate: {error_rate}%"],
                evidence=[{"type": "pattern", "name": "high_error_rate"}],
                execution_time_ms=0
            )
        
        return AnalysisResult(
            strategy=AnalysisStrategy.PATTERN_MATCHING.value,
            success=True,
            confidence=30,
            root_cause=None,
            contributing_factors=[],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _lookup_history(
        self,
        service: str,
        symptoms: Dict,
        context: Dict
    ) -> AnalysisResult:
        """Look up similar historical incidents"""
        
        await asyncio.sleep(0.05)
        
        # Would integrate with incident memory
        return AnalysisResult(
            strategy=AnalysisStrategy.HISTORICAL_LOOKUP.value,
            success=True,
            confidence=40,
            root_cause=None,
            contributing_factors=["Similar incidents found"],
            evidence=[],
            execution_time_ms=0
        )
    
    async def _prepare_remediation(
        self,
        cause_type: str,
        service: str
    ) -> RemediationPlan:
        """Pre-prepare remediation plan for a cause type"""
        
        generator = self.remediation_generators.get(cause_type)
        if generator:
            return await generator(service)
        
        return RemediationPlan(
            plan_id=f"plan_{cause_type}_{int(time.time())}",
            action_type="investigate",
            priority=5,
            prerequisites=[],
            steps=[{"action": "manual_investigation"}],
            rollback_steps=[],
            estimated_impact="Unknown",
            estimated_time_minutes=30,
            risk_level="low",
            ready_to_execute=False
        )
    
    async def _plan_rollback(self, service: str) -> RemediationPlan:
        """Prepare rollback plan"""
        return RemediationPlan(
            plan_id=f"rollback_{service}_{int(time.time())}",
            action_type="rollback",
            priority=1,
            prerequisites=["Previous version available", "No DB migration"],
            steps=[
                {"action": "rollback_deployment", "target": "previous_version"},
                {"action": "verify_health", "timeout": 300}
            ],
            rollback_steps=[{"action": "redeploy_current"}],
            estimated_impact="Brief service interruption",
            estimated_time_minutes=5,
            risk_level="low",
            ready_to_execute=True
        )
    
    async def _plan_scale_up(self, service: str) -> RemediationPlan:
        """Prepare scale-up plan"""
        return RemediationPlan(
            plan_id=f"scale_{service}_{int(time.time())}",
            action_type="scale_up",
            priority=2,
            prerequisites=["Cluster has capacity"],
            steps=[
                {"action": "scale_replicas", "factor": 2},
                {"action": "verify_health", "timeout": 180}
            ],
            rollback_steps=[{"action": "scale_down"}],
            estimated_impact="Increased cost",
            estimated_time_minutes=3,
            risk_level="low",
            ready_to_execute=True
        )
    
    async def _plan_restart(self, service: str) -> RemediationPlan:
        """Prepare restart plan"""
        return RemediationPlan(
            plan_id=f"restart_{service}_{int(time.time())}",
            action_type="restart",
            priority=2,
            prerequisites=["Service is restartable"],
            steps=[
                {"action": "rolling_restart", "max_unavailable": 1},
                {"action": "verify_health", "timeout": 300}
            ],
            rollback_steps=[],
            estimated_impact="Brief capacity reduction",
            estimated_time_minutes=5,
            risk_level="medium",
            ready_to_execute=True
        )
    
    async def _plan_circuit_breaker(self, service: str) -> RemediationPlan:
        """Prepare circuit breaker plan"""
        return RemediationPlan(
            plan_id=f"circuit_{service}_{int(time.time())}",
            action_type="circuit_breaker",
            priority=1,
            prerequisites=["Circuit breaker configured"],
            steps=[
                {"action": "enable_circuit_breaker", "target": "failing_dependency"},
                {"action": "monitor_fallback", "duration": 300}
            ],
            rollback_steps=[{"action": "disable_circuit_breaker"}],
            estimated_impact="Degraded but available service",
            estimated_time_minutes=1,
            risk_level="low",
            ready_to_execute=True
        )
    
    async def _plan_config_rollback(self, service: str) -> RemediationPlan:
        """Prepare config rollback plan"""
        return RemediationPlan(
            plan_id=f"config_{service}_{int(time.time())}",
            action_type="config_rollback",
            priority=2,
            prerequisites=["Previous config version available"],
            steps=[
                {"action": "rollback_configmap", "target": "previous"},
                {"action": "restart_pods", "strategy": "rolling"}
            ],
            rollback_steps=[{"action": "reapply_current_config"}],
            estimated_impact="Config values reverted",
            estimated_time_minutes=3,
            risk_level="low",
            ready_to_execute=True
        )
    
    def _build_consensus(
        self,
        results: List[AnalysisResult]
    ) -> Tuple[str, float]:
        """Build consensus from multiple analysis strategies"""
        
        if not results:
            return "Unknown - no analysis completed", 0
        
        # Group by root cause
        causes = {}
        for r in results:
            if r.success and r.root_cause and r.confidence > 50:
                cause = r.root_cause
                if cause not in causes:
                    causes[cause] = []
                causes[cause].append(r.confidence)
        
        if not causes:
            # No clear consensus
            best = max(results, key=lambda r: r.confidence)
            return best.root_cause or "Unknown", best.confidence
        
        # Find highest combined confidence
        best_cause = None
        best_score = 0
        
        for cause, confidences in causes.items():
            # Average confidence weighted by number of strategies
            avg_conf = sum(confidences) / len(confidences)
            multi_strategy_bonus = min(len(confidences) * 10, 30)
            score = avg_conf + multi_strategy_bonus
            
            if score > best_score:
                best_score = score
                best_cause = cause
        
        return best_cause, min(best_score, 100)
    
    def _rank_remediations(
        self,
        plans: List[RemediationPlan],
        root_cause: str
    ) -> List[RemediationPlan]:
        """Rank remediation plans based on root cause"""
        
        if not plans:
            return []
        
        # Keyword matching for ranking
        cause_lower = (root_cause or "").lower()
        
        def score_plan(plan: RemediationPlan) -> float:
            score = 100 - plan.priority * 10  # Lower priority number = higher score
            
            # Boost plans that match root cause keywords
            if "deployment" in cause_lower and plan.action_type == "rollback":
                score += 50
            elif "memory" in cause_lower and plan.action_type in ["restart", "scale_up"]:
                score += 40
            elif "cpu" in cause_lower and plan.action_type == "scale_up":
                score += 40
            elif "dependency" in cause_lower and plan.action_type == "circuit_breaker":
                score += 50
            elif "config" in cause_lower and plan.action_type == "config_rollback":
                score += 50
            
            # Ready to execute bonus
            if plan.ready_to_execute:
                score += 10
            
            return score
        
        return sorted(plans, key=score_plan, reverse=True)
    
    def _store_resolution(self, resolution: AcceleratedResolution):
        """Store resolution for tracking"""
        try:
            self.redis.setex(
                f"resolution:{resolution.resolution_id}",
                86400 * 7,
                json.dumps(asdict(resolution))
            )
            self.redis.lpush("resolutions:all", resolution.resolution_id)
            self.redis.ltrim("resolutions:all", 0, 199)
        except Exception as e:
            logger.error(f"[MTTR] Error storing resolution: {e}")
    
    def get_mttr_stats(self) -> Dict:
        """Get MTTR acceleration statistics"""
        
        try:
            resolution_ids = self.redis.lrange("resolutions:all", 0, 99)
            
            if not resolution_ids:
                return {"total_resolutions": 0}
            
            total_time = 0
            total_speedup = 0
            successful = 0
            
            for rid in resolution_ids:
                rid_str = rid.decode() if isinstance(rid, bytes) else rid
                data = self.redis.get(f"resolution:{rid_str}")
                if data:
                    res = json.loads(data)
                    total_time += res.get("total_time_ms", 0)
                    total_speedup += res.get("parallel_speedup", 1)
                    if res.get("ready_for_execution"):
                        successful += 1
            
            count = len(resolution_ids)
            
            return {
                "total_resolutions": count,
                "avg_resolution_time_ms": round(total_time / count, 1) if count else 0,
                "avg_parallel_speedup": round(total_speedup / count, 2) if count else 1,
                "success_rate": round(successful / count * 100, 1) if count else 0,
                "analysis_strategies": len(self.strategies),
                "remediation_types": len(self.remediation_generators)
            }
        except Exception as e:
            return {"error": str(e)}


# Convenience function
async def accelerate_incident(
    redis_client,
    incident_id: str,
    service: str,
    symptoms: Dict
) -> AcceleratedResolution:
    """Quick function for accelerated incident resolution"""
    engine = MTTRAccelerator(redis_client)
    return await engine.accelerate_resolution(incident_id, service, symptoms)
