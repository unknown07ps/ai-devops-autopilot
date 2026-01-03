"""
DevOps Knowledge Base - Comprehensive Production Error Patterns
Contains 100+ patterns for Kubernetes, Database, Cloud, Application, CI/CD, and Network issues
Each pattern includes symptoms, root causes, and recommended actions with confidence scores
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum


class PatternCategory(str, Enum):
    KUBERNETES = "kubernetes"
    DATABASE = "database"
    CLOUD = "cloud"
    APPLICATION = "application"
    CICD = "cicd"
    NETWORK = "network"
    MONITORING = "monitoring"
    SECURITY = "security"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BlastRadius(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Symptom:
    """A single symptom that indicates a potential issue"""
    type: str  # metric, event, log, status
    name: str
    condition: str  # above, below, equals, contains, matches
    value: any
    weight: float = 1.0  # Importance weight for matching


@dataclass
class RecommendedAction:
    """An action to resolve the issue"""
    action_type: str
    action_category: str
    confidence: float
    params: Dict = field(default_factory=dict)
    requires_approval: bool = False
    estimated_resolution_seconds: int = 60
    rollback_action: str = None


@dataclass
class IncidentPattern:
    """Complete pattern for a known DevOps issue"""
    pattern_id: str
    name: str
    description: str
    category: PatternCategory
    subcategory: str
    severity: Severity
    symptoms: List[Symptom]
    signals: List[str]  # Keywords to match
    root_causes: List[str]
    recommended_actions: List[RecommendedAction]
    autonomous_safe: bool
    blast_radius: BlastRadius
    resolution_time_avg_seconds: int
    tags: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def match_score(self, anomalies: List[Dict], logs: List[Dict] = None) -> float:
        """Calculate how well this pattern matches given anomalies"""
        score = 0.0
        max_score = sum(s.weight for s in self.symptoms)
        
        for symptom in self.symptoms:
            if self._symptom_matches(symptom, anomalies, logs):
                score += symptom.weight
        
        # Bonus for signal keyword matches
        if logs:
            log_text = " ".join(str(l) for l in logs).lower()
            for signal in self.signals:
                if signal.lower() in log_text:
                    score += 0.5
        
        return min(100.0, (score / max_score) * 100) if max_score > 0 else 0.0
    
    def _symptom_matches(self, symptom: Symptom, anomalies: List[Dict], logs: List[Dict]) -> bool:
        """Check if a single symptom matches"""
        for anomaly in anomalies:
            if symptom.type == "metric":
                if anomaly.get("metric_name") == symptom.name:
                    value = anomaly.get("value", 0)
                    if symptom.condition == "above" and value > symptom.value:
                        return True
                    elif symptom.condition == "below" and value < symptom.value:
                        return True
                    elif symptom.condition == "equals" and value == symptom.value:
                        return True
            elif symptom.type == "event":
                if symptom.name.lower() in str(anomaly).lower():
                    return True
            elif symptom.type == "log" and logs:
                for log in logs:
                    if symptom.name.lower() in str(log).lower():
                        return True
        return False


class DevOpsKnowledgeBase:
    """
    Comprehensive knowledge base of DevOps incident patterns
    Contains 100+ patterns covering all major incident types
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.patterns: Dict[str, IncidentPattern] = {}
        self._load_builtin_patterns()
        if redis_client:
            self._load_custom_patterns()
    
    def _load_builtin_patterns(self):
        """Load all built-in patterns (500+ total)"""
        # Core patterns (30+)
        self._add_kubernetes_patterns()
        self._add_database_patterns()
        self._add_cloud_patterns()
        self._add_application_patterns()
        self._add_cicd_patterns()
        self._add_network_patterns()
        
        # Extended patterns (470+)
        self._load_extended_patterns()
    
    def _load_extended_patterns(self):
        """Load extended patterns from separate modules (500+ total)"""
        pattern_modules = [
            ("src.training.patterns_kubernetes_extended", "get_extended_kubernetes_patterns"),
            ("src.training.patterns_kubernetes_batch2", "get_kubernetes_patterns_batch2"),
            ("src.training.patterns_database_extended", "get_extended_database_patterns"),
            ("src.training.patterns_database_batch2", "get_database_patterns_batch2"),
            ("src.training.patterns_cloud_batch2", "get_cloud_patterns_batch2"),
            ("src.training.patterns_extended", "get_all_extended_patterns"),
            ("src.training.patterns_batch3", "get_all_batch3_patterns"),
        ]
        
        for module_name, func_name in pattern_modules:
            try:
                module = __import__(module_name, fromlist=[func_name])
                get_patterns_func = getattr(module, func_name)
                for pattern in get_patterns_func():
                    self.add_pattern(pattern)
            except (ImportError, AttributeError) as e:
                print(f"Could not load {module_name}: {e}")
                pass
    
    def _add_kubernetes_patterns(self):
        """Add Kubernetes-related incident patterns"""
        
        # K8s-001: OOMKilled
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_oom_killed_001",
            name="Pod OOMKilled",
            description="Container killed due to exceeding memory limits",
            category=PatternCategory.KUBERNETES,
            subcategory="pod_crash",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "memory_usage_percent", "above", 95, 2.0),
                Symptom("event", "OOMKilled", "contains", True, 3.0),
                Symptom("metric", "container_restarts", "above", 2, 1.5),
            ],
            signals=["OOMKilled", "memory limit", "killed", "out of memory", "oom"],
            root_causes=["memory_leak", "insufficient_memory_limits", "traffic_spike", "memory_intensive_query"],
            recommended_actions=[
                RecommendedAction("increase_memory_limit", "kubernetes", 90, {"increase_percent": 50}, False, 30),
                RecommendedAction("restart_pod", "kubernetes", 75, {}, False, 15),
                RecommendedAction("scale_horizontal", "kubernetes", 65, {"replicas": 1}, False, 60),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=120,
            tags=["memory", "oom", "pod", "container"],
            related_patterns=["k8s_memory_pressure_002"]
        ))
        
        # K8s-002: CrashLoopBackOff
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_crashloop_002",
            name="Pod CrashLoopBackOff",
            description="Container repeatedly crashing and restarting",
            category=PatternCategory.KUBERNETES,
            subcategory="pod_crash",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "CrashLoopBackOff", "contains", True, 3.0),
                Symptom("metric", "container_restarts", "above", 5, 2.0),
                Symptom("event", "Back-off restarting", "contains", True, 1.5),
            ],
            signals=["CrashLoopBackOff", "Back-off", "restarting failed container", "exit code"],
            root_causes=["application_error", "missing_config", "dependency_failure", "startup_failure"],
            recommended_actions=[
                RecommendedAction("get_pod_logs", "kubernetes", 95, {"tail_lines": 100}, False, 10),
                RecommendedAction("describe_pod", "kubernetes", 90, {}, False, 5),
                RecommendedAction("rollback_deployment", "kubernetes", 70, {}, True, 60),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["crash", "loop", "restart", "container"]
        ))
        
        # K8s-003: ImagePullBackOff
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_imagepull_003",
            name="ImagePullBackOff",
            description="Failed to pull container image",
            category=PatternCategory.KUBERNETES,
            subcategory="image_pull",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "ImagePullBackOff", "contains", True, 3.0),
                Symptom("event", "ErrImagePull", "contains", True, 2.5),
                Symptom("event", "Failed to pull image", "contains", True, 2.0),
            ],
            signals=["ImagePullBackOff", "ErrImagePull", "unauthorized", "not found", "manifest unknown"],
            root_causes=["invalid_image_tag", "registry_auth_failure", "network_issue", "image_not_exist"],
            recommended_actions=[
                RecommendedAction("verify_image_exists", "kubernetes", 90, {}, False, 30),
                RecommendedAction("check_registry_credentials", "kubernetes", 85, {}, False, 30),
                RecommendedAction("rollback_to_previous_image", "kubernetes", 75, {}, True, 60),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=180,
            tags=["image", "pull", "registry", "container"]
        ))
        
        # K8s-004: Node NotReady
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_node_notready_004",
            name="Node NotReady",
            description="Kubernetes node became unavailable",
            category=PatternCategory.KUBERNETES,
            subcategory="node_health",
            severity=Severity.CRITICAL,
            symptoms=[
                Symptom("event", "NodeNotReady", "contains", True, 3.0),
                Symptom("event", "node condition Ready is now: Unknown", "contains", True, 2.5),
                Symptom("metric", "node_status_ready", "equals", 0, 3.0),
            ],
            signals=["NotReady", "node condition", "kubelet stopped", "NodeHasSufficientMemory"],
            root_causes=["kubelet_crash", "network_partition", "disk_pressure", "memory_pressure", "hardware_failure"],
            recommended_actions=[
                RecommendedAction("cordon_node", "kubernetes", 95, {}, False, 10),
                RecommendedAction("drain_node", "kubernetes", 85, {"force": True}, True, 120),
                RecommendedAction("restart_kubelet", "kubernetes", 75, {}, True, 60),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=600,
            tags=["node", "notready", "kubelet", "cluster"]
        ))
        
        # K8s-005: High CPU Throttling
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_cpu_throttle_005",
            name="High CPU Throttling",
            description="Container experiencing significant CPU throttling",
            category=PatternCategory.KUBERNETES,
            subcategory="resource_limits",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("metric", "cpu_throttle_percent", "above", 50, 2.0),
                Symptom("metric", "cpu_usage_percent", "above", 90, 1.5),
                Symptom("metric", "request_latency_p99", "above", 1000, 1.0),
            ],
            signals=["throttling", "cpu limit", "slow response", "timeout"],
            root_causes=["insufficient_cpu_limits", "traffic_spike", "inefficient_code", "blocking_operations"],
            recommended_actions=[
                RecommendedAction("increase_cpu_limit", "kubernetes", 85, {"increase_percent": 50}, False, 30),
                RecommendedAction("scale_horizontal", "kubernetes", 80, {"replicas": 1}, False, 60),
                RecommendedAction("optimize_resource_requests", "kubernetes", 70, {}, False, 120),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=120,
            tags=["cpu", "throttle", "limits", "performance"]
        ))
        
        # K8s-006: PVC Pending
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_pvc_pending_006",
            name="PVC Pending",
            description="PersistentVolumeClaim stuck in pending state",
            category=PatternCategory.KUBERNETES,
            subcategory="storage",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "PVC Pending", "contains", True, 3.0),
                Symptom("event", "waiting for a volume to be created", "contains", True, 2.0),
                Symptom("event", "no persistent volumes available", "contains", True, 2.5),
            ],
            signals=["Pending", "PersistentVolumeClaim", "no volume", "storage class", "provisioner"],
            root_causes=["no_matching_pv", "storage_class_missing", "quota_exceeded", "provisioner_error"],
            recommended_actions=[
                RecommendedAction("check_storage_class", "kubernetes", 90, {}, False, 15),
                RecommendedAction("create_pv", "kubernetes", 75, {}, True, 60),
                RecommendedAction("expand_storage_quota", "cloud", 70, {}, True, 120),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["pvc", "storage", "volume", "pending"]
        ))
        
        # K8s-007: HPA Unable to Scale
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_hpa_unable_007",
            name="HPA Unable to Scale",
            description="Horizontal Pod Autoscaler unable to scale pods",
            category=PatternCategory.KUBERNETES,
            subcategory="autoscaling",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("event", "unable to fetch metrics", "contains", True, 2.5),
                Symptom("event", "FailedGetResourceMetric", "contains", True, 2.0),
                Symptom("metric", "hpa_current_replicas", "equals", "hpa_desired_replicas", 1.5),
            ],
            signals=["HPA", "unable to scale", "metrics unavailable", "FailedGetResourceMetric"],
            root_causes=["metrics_server_down", "invalid_metric_name", "insufficient_resources", "quota_limit"],
            recommended_actions=[
                RecommendedAction("check_metrics_server", "kubernetes", 90, {}, False, 30),
                RecommendedAction("manual_scale", "kubernetes", 80, {"replicas": 2}, False, 30),
                RecommendedAction("check_resource_quota", "kubernetes", 70, {}, False, 60),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=180,
            tags=["hpa", "autoscaling", "metrics", "scale"]
        ))
        
        # K8s-008: DNS Resolution Failure
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_dns_failure_008",
            name="DNS Resolution Failure",
            description="Pods unable to resolve DNS names",
            category=PatternCategory.KUBERNETES,
            subcategory="networking",
            severity=Severity.CRITICAL,
            symptoms=[
                Symptom("log", "could not resolve", "contains", True, 3.0),
                Symptom("log", "no such host", "contains", True, 2.5),
                Symptom("event", "dns lookup failed", "contains", True, 2.0),
            ],
            signals=["DNS", "resolve", "no such host", "SERVFAIL", "coredns", "kube-dns"],
            root_causes=["coredns_crash", "dns_config_error", "network_policy_blocking", "ndots_misconfiguration"],
            recommended_actions=[
                RecommendedAction("restart_coredns", "kubernetes", 85, {}, False, 60),
                RecommendedAction("check_dns_config", "kubernetes", 90, {}, False, 30),
                RecommendedAction("validate_network_policies", "kubernetes", 75, {}, False, 120),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=300,
            tags=["dns", "coredns", "networking", "resolution"]
        ))
        
        # K8s-009: Ingress 502/504 Errors
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_ingress_errors_009",
            name="Ingress Bad Gateway Errors",
            description="Ingress controller returning 502/504 errors",
            category=PatternCategory.KUBERNETES,
            subcategory="ingress",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "http_502_rate", "above", 5, 2.5),
                Symptom("metric", "http_504_rate", "above", 5, 2.5),
                Symptom("metric", "upstream_response_time", "above", 30000, 2.0),
            ],
            signals=["502", "504", "bad gateway", "gateway timeout", "upstream", "backend"],
            root_causes=["backend_unhealthy", "timeout_misconfiguration", "resource_exhaustion", "connection_limit"],
            recommended_actions=[
                RecommendedAction("check_backend_health", "kubernetes", 90, {}, False, 30),
                RecommendedAction("increase_timeout", "kubernetes", 75, {"timeout_seconds": 60}, False, 30),
                RecommendedAction("scale_backend", "kubernetes", 80, {"replicas": 1}, False, 60),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180,
            tags=["ingress", "502", "504", "gateway", "traffic"]
        ))
        
        # K8s-010: Pod Eviction
        self.add_pattern(IncidentPattern(
            pattern_id="k8s_pod_eviction_010",
            name="Pod Eviction",
            description="Pods being evicted from nodes",
            category=PatternCategory.KUBERNETES,
            subcategory="pod_scheduling",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "Evicted", "contains", True, 3.0),
                Symptom("event", "The node was low on resource", "contains", True, 2.5),
                Symptom("event", "ephemeral-storage", "contains", True, 1.5),
            ],
            signals=["Evicted", "eviction", "low on resource", "disk pressure", "ephemeral-storage"],
            root_causes=["disk_pressure", "memory_pressure", "ephemeral_storage_limit", "node_overcommit"],
            recommended_actions=[
                RecommendedAction("cleanup_disk_space", "kubernetes", 85, {}, False, 120),
                RecommendedAction("set_resource_limits", "kubernetes", 80, {}, False, 60),
                RecommendedAction("add_node", "cloud", 70, {}, True, 300),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["eviction", "disk", "memory", "resources"]
        ))
    
    def _add_database_patterns(self):
        """Add database-related incident patterns"""
        
        # DB-001: Connection Pool Exhausted
        self.add_pattern(IncidentPattern(
            pattern_id="db_connection_pool_001",
            name="Database Connection Pool Exhausted",
            description="Application unable to acquire database connections",
            category=PatternCategory.DATABASE,
            subcategory="connection",
            severity=Severity.CRITICAL,
            symptoms=[
                Symptom("log", "connection pool exhausted", "contains", True, 3.0),
                Symptom("log", "unable to acquire connection", "contains", True, 2.5),
                Symptom("metric", "active_connections", "above", 95, 2.0),
                Symptom("metric", "connection_wait_time_ms", "above", 5000, 2.0),
            ],
            signals=["pool exhausted", "no connections available", "max pool size", "connection timeout"],
            root_causes=["connection_leak", "slow_queries", "insufficient_pool_size", "traffic_spike"],
            recommended_actions=[
                RecommendedAction("increase_pool_size", "database", 85, {"increase_by": 20}, False, 30),
                RecommendedAction("kill_idle_connections", "database", 80, {"idle_threshold_seconds": 300}, False, 15),
                RecommendedAction("restart_application", "application", 70, {}, True, 120),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=120,
            tags=["connection", "pool", "database", "exhausted"]
        ))
        
        # DB-002: Slow Query Performance
        self.add_pattern(IncidentPattern(
            pattern_id="db_slow_query_002",
            name="Slow Query Performance",
            description="Database queries taking abnormally long",
            category=PatternCategory.DATABASE,
            subcategory="performance",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("metric", "query_time_p99_ms", "above", 5000, 2.5),
                Symptom("metric", "slow_queries_per_minute", "above", 10, 2.0),
                Symptom("log", "slow query", "contains", True, 1.5),
            ],
            signals=["slow query", "query timeout", "table scan", "missing index", "lock wait"],
            root_causes=["missing_index", "table_lock", "full_table_scan", "complex_join", "large_result_set"],
            recommended_actions=[
                RecommendedAction("analyze_slow_queries", "database", 95, {}, False, 60),
                RecommendedAction("add_missing_index", "database", 80, {}, True, 300),
                RecommendedAction("optimize_query", "database", 75, {}, True, 600),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=600,
            tags=["slow", "query", "performance", "index"]
        ))
        
        # DB-003: Replication Lag
        self.add_pattern(IncidentPattern(
            pattern_id="db_replication_lag_003",
            name="Database Replication Lag",
            description="Replica database falling behind primary",
            category=PatternCategory.DATABASE,
            subcategory="replication",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "replication_lag_seconds", "above", 30, 3.0),
                Symptom("metric", "slave_io_running", "equals", False, 2.5),
                Symptom("log", "replication lag", "contains", True, 2.0),
            ],
            signals=["replication lag", "seconds behind", "slave stopped", "relay log"],
            root_causes=["high_write_load", "network_latency", "slave_hardware", "long_running_query"],
            recommended_actions=[
                RecommendedAction("check_replication_status", "database", 95, {}, False, 15),
                RecommendedAction("skip_problematic_transaction", "database", 60, {}, True, 30),
                RecommendedAction("rebuild_replica", "database", 50, {}, True, 3600),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["replication", "lag", "replica", "sync"]
        ))
        
        # DB-004: Deadlock Detected
        self.add_pattern(IncidentPattern(
            pattern_id="db_deadlock_004",
            name="Database Deadlock",
            description="Transactions blocking each other causing deadlock",
            category=PatternCategory.DATABASE,
            subcategory="locking",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("log", "deadlock detected", "contains", True, 3.0),
                Symptom("log", "Deadlock found", "contains", True, 3.0),
                Symptom("metric", "deadlocks_per_minute", "above", 1, 2.5),
            ],
            signals=["deadlock", "waiting for lock", "lock timeout", "transaction rolled back"],
            root_causes=["poor_transaction_design", "long_transactions", "insufficient_indexing", "inconsistent_lock_order"],
            recommended_actions=[
                RecommendedAction("analyze_deadlock_graph", "database", 95, {}, False, 60),
                RecommendedAction("kill_blocking_queries", "database", 80, {}, False, 15),
                RecommendedAction("optimize_transaction_order", "database", 70, {}, True, 600),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=300,
            tags=["deadlock", "lock", "transaction", "blocking"]
        ))
        
        # DB-005: High CPU Usage
        self.add_pattern(IncidentPattern(
            pattern_id="db_high_cpu_005",
            name="Database High CPU",
            description="Database server CPU usage critically high",
            category=PatternCategory.DATABASE,
            subcategory="resource",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "cpu_usage_percent", "above", 90, 3.0),
                Symptom("metric", "active_queries", "above", 50, 2.0),
                Symptom("metric", "query_time_avg_ms", "above", 1000, 1.5),
            ],
            signals=["high cpu", "cpu usage", "busy", "queries running"],
            root_causes=["expensive_queries", "too_many_connections", "missing_indexes", "inefficient_queries"],
            recommended_actions=[
                RecommendedAction("identify_expensive_queries", "database", 95, {}, False, 30),
                RecommendedAction("kill_long_running_queries", "database", 80, {"threshold_seconds": 300}, False, 15),
                RecommendedAction("scale_read_replicas", "database", 70, {"count": 1}, True, 600),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180,
            tags=["cpu", "high", "performance", "queries"]
        ))
        
        # DB-006: Disk Space Critical
        self.add_pattern(IncidentPattern(
            pattern_id="db_disk_space_006",
            name="Database Disk Space Critical",
            description="Database disk space running critically low",
            category=PatternCategory.DATABASE,
            subcategory="storage",
            severity=Severity.CRITICAL,
            symptoms=[
                Symptom("metric", "disk_usage_percent", "above", 90, 3.0),
                Symptom("log", "no space left on device", "contains", True, 3.0),
                Symptom("metric", "disk_free_gb", "below", 5, 2.5),
            ],
            signals=["disk full", "no space", "write failed", "out of disk"],
            root_causes=["log_growth", "temp_files", "data_growth", "backup_files"],
            recommended_actions=[
                RecommendedAction("cleanup_old_logs", "database", 90, {"older_than_days": 7}, False, 60),
                RecommendedAction("cleanup_temp_files", "database", 85, {}, False, 30),
                RecommendedAction("expand_storage", "cloud", 80, {"increase_gb": 50}, True, 300),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=180,
            tags=["disk", "space", "storage", "full"]
        ))
    
    def _add_cloud_patterns(self):
        """Add cloud infrastructure patterns"""
        
        # Cloud-001: Instance Health Check Failed
        self.add_pattern(IncidentPattern(
            pattern_id="cloud_instance_health_001",
            name="Instance Health Check Failed",
            description="Cloud instance failing health checks",
            category=PatternCategory.CLOUD,
            subcategory="compute",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "health check failed", "contains", True, 3.0),
                Symptom("metric", "instance_status", "equals", "unhealthy", 3.0),
                Symptom("metric", "failed_health_checks", "above", 3, 2.0),
            ],
            signals=["unhealthy", "health check", "target failed", "instance failed"],
            root_causes=["application_crash", "port_not_listening", "network_issue", "resource_exhaustion"],
            recommended_actions=[
                RecommendedAction("check_instance_logs", "cloud", 95, {}, False, 30),
                RecommendedAction("restart_instance", "cloud", 80, {}, True, 120),
                RecommendedAction("replace_instance", "cloud", 70, {}, True, 300),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["health", "instance", "check", "failed"]
        ))
        
        # Cloud-002: Auto Scaling Failure
        self.add_pattern(IncidentPattern(
            pattern_id="cloud_autoscaling_002",
            name="Auto Scaling Failure",
            description="Auto scaling group unable to launch new instances",
            category=PatternCategory.CLOUD,
            subcategory="autoscaling",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "Failed to launch", "contains", True, 3.0),
                Symptom("event", "InsufficientInstanceCapacity", "contains", True, 2.5),
                Symptom("metric", "pending_instances", "above", 0, 1.5),
            ],
            signals=["Failed to launch", "capacity", "quota", "limit exceeded", "scaling failed"],
            root_causes=["capacity_shortage", "quota_exceeded", "ami_not_found", "launch_config_error"],
            recommended_actions=[
                RecommendedAction("check_quota_limits", "cloud", 90, {}, False, 30),
                RecommendedAction("try_different_az", "cloud", 80, {}, True, 60),
                RecommendedAction("try_different_instance_type", "cloud", 75, {}, True, 60),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["autoscaling", "launch", "capacity", "quota"]
        ))
        
        # Cloud-003: API Rate Limiting
        self.add_pattern(IncidentPattern(
            pattern_id="cloud_rate_limit_003",
            name="Cloud API Rate Limiting",
            description="Cloud API calls being throttled",
            category=PatternCategory.CLOUD,
            subcategory="api",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("log", "rate exceeded", "contains", True, 3.0),
                Symptom("log", "throttling", "contains", True, 2.5),
                Symptom("metric", "api_throttle_count", "above", 10, 2.0),
            ],
            signals=["throttling", "rate exceeded", "429", "too many requests", "rate limit"],
            root_causes=["too_many_api_calls", "burst_traffic", "misconfigured_retry", "inefficient_polling"],
            recommended_actions=[
                RecommendedAction("implement_exponential_backoff", "application", 90, {}, True, 120),
                RecommendedAction("request_quota_increase", "cloud", 75, {}, True, 86400),
                RecommendedAction("cache_api_responses", "application", 80, {}, True, 300),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=300,
            tags=["rate", "limit", "throttle", "api"]
        ))
        
        # Cloud-004: Load Balancer 5xx Errors
        self.add_pattern(IncidentPattern(
            pattern_id="cloud_lb_5xx_004",
            name="Load Balancer 5xx Errors",
            description="Load balancer returning 5xx errors",
            category=PatternCategory.CLOUD,
            subcategory="loadbalancer",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "http_5xx_rate", "above", 1, 3.0),
                Symptom("metric", "healthy_host_count", "below", 1, 3.0),
                Symptom("metric", "request_count", "above", 0, 1.0),
            ],
            signals=["5xx", "502", "503", "504", "backend error", "no healthy backends"],
            root_causes=["all_backends_down", "backend_timeout", "security_group_issue", "health_check_misconfigured"],
            recommended_actions=[
                RecommendedAction("check_target_health", "cloud", 95, {}, False, 15),
                RecommendedAction("scale_target_group", "cloud", 80, {"count": 2}, True, 120),
                RecommendedAction("rollback_deployment", "cicd", 75, {}, True, 180),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=300,
            tags=["loadbalancer", "5xx", "errors", "backend"]
        ))
    
    def _add_application_patterns(self):
        """Add application-level incident patterns"""
        
        # App-001: Memory Leak
        self.add_pattern(IncidentPattern(
            pattern_id="app_memory_leak_001",
            name="Memory Leak Detected",
            description="Application showing signs of memory leak",
            category=PatternCategory.APPLICATION,
            subcategory="memory",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "memory_usage_percent", "above", 85, 2.0),
                Symptom("metric", "memory_growth_rate", "above", 5, 2.5),
                Symptom("metric", "gc_pause_time_ms", "above", 500, 1.5),
            ],
            signals=["memory leak", "out of memory", "heap", "gc pressure", "memory exhausted"],
            root_causes=["object_retention", "infinite_cache", "event_listener_leak", "closure_retention"],
            recommended_actions=[
                RecommendedAction("capture_heap_dump", "application", 90, {}, False, 60),
                RecommendedAction("restart_application", "application", 85, {}, True, 60),
                RecommendedAction("scale_horizontal", "kubernetes", 70, {"replicas": 1}, False, 60),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=180,
            tags=["memory", "leak", "heap", "gc"]
        ))
        
        # App-002: High Error Rate
        self.add_pattern(IncidentPattern(
            pattern_id="app_error_rate_002",
            name="High Application Error Rate",
            description="Application experiencing elevated error rates",
            category=PatternCategory.APPLICATION,
            subcategory="errors",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "error_rate_percent", "above", 5, 3.0),
                Symptom("metric", "http_5xx_count", "above", 100, 2.5),
                Symptom("log", "error", "contains", True, 1.5),
            ],
            signals=["error", "exception", "failure", "5xx", "unhandled"],
            root_causes=["code_bug", "dependency_failure", "configuration_error", "data_corruption"],
            recommended_actions=[
                RecommendedAction("analyze_error_logs", "application", 95, {}, False, 30),
                RecommendedAction("check_dependencies", "application", 85, {}, False, 60),
                RecommendedAction("rollback_deployment", "cicd", 75, {}, True, 180),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["error", "rate", "exceptions", "5xx"]
        ))
        
        # App-003: Thread Pool Exhaustion
        self.add_pattern(IncidentPattern(
            pattern_id="app_thread_pool_003",
            name="Thread Pool Exhaustion",
            description="Application thread pool fully utilized",
            category=PatternCategory.APPLICATION,
            subcategory="concurrency",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "active_threads", "above", 95, 2.5),
                Symptom("metric", "queued_requests", "above", 100, 2.0),
                Symptom("log", "thread pool exhausted", "contains", True, 3.0),
            ],
            signals=["thread pool", "no threads available", "queued", "blocked", "deadlock"],
            root_causes=["blocking_operations", "slow_downstream", "insufficient_pool_size", "thread_leak"],
            recommended_actions=[
                RecommendedAction("increase_thread_pool", "application", 80, {"size": 100}, True, 60),
                RecommendedAction("restart_application", "application", 85, {}, True, 60),
                RecommendedAction("scale_horizontal", "kubernetes", 75, {"replicas": 1}, False, 60),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180,
            tags=["thread", "pool", "exhausted", "concurrency"]
        ))
        
        # App-004: Circuit Breaker Open
        self.add_pattern(IncidentPattern(
            pattern_id="app_circuit_breaker_004",
            name="Circuit Breaker Open",
            description="Circuit breaker tripped due to downstream failures",
            category=PatternCategory.APPLICATION,
            subcategory="resilience",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("metric", "circuit_breaker_state", "equals", "open", 3.0),
                Symptom("log", "circuit breaker open", "contains", True, 2.5),
                Symptom("metric", "downstream_error_rate", "above", 50, 2.0),
            ],
            signals=["circuit breaker", "open", "fallback", "downstream failure"],
            root_causes=["downstream_outage", "network_issue", "timeout", "overload"],
            recommended_actions=[
                RecommendedAction("check_downstream_health", "application", 95, {}, False, 30),
                RecommendedAction("restart_downstream", "application", 70, {}, True, 120),
                RecommendedAction("enable_fallback", "application", 80, {}, False, 30),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=300,
            tags=["circuit", "breaker", "downstream", "fallback"]
        ))
        
        # App-005: High Latency
        self.add_pattern(IncidentPattern(
            pattern_id="app_high_latency_005",
            name="High Response Latency",
            description="Application response times significantly elevated",
            category=PatternCategory.APPLICATION,
            subcategory="performance",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("metric", "response_time_p99_ms", "above", 5000, 3.0),
                Symptom("metric", "response_time_p50_ms", "above", 1000, 2.0),
                Symptom("metric", "request_rate", "above", 100, 1.0),
            ],
            signals=["slow", "latency", "timeout", "response time", "degraded"],
            root_causes=["database_slow", "external_dependency", "resource_contention", "garbage_collection"],
            recommended_actions=[
                RecommendedAction("analyze_traces", "application", 95, {}, False, 60),
                RecommendedAction("scale_horizontal", "kubernetes", 80, {"replicas": 1}, False, 60),
                RecommendedAction("enable_caching", "application", 70, {}, True, 300),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=180,
            tags=["latency", "slow", "performance", "response"]
        ))
    
    def _add_cicd_patterns(self):
        """Add CI/CD related patterns"""
        
        # CICD-001: Deployment Failed
        self.add_pattern(IncidentPattern(
            pattern_id="cicd_deploy_failed_001",
            name="Deployment Failed",
            description="Deployment to production failed",
            category=PatternCategory.CICD,
            subcategory="deployment",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("event", "deployment failed", "contains", True, 3.0),
                Symptom("metric", "deployment_status", "equals", "failed", 3.0),
                Symptom("log", "rollout failed", "contains", True, 2.5),
            ],
            signals=["deployment failed", "rollout failed", "deploy error", "release failed"],
            root_causes=["image_not_found", "config_error", "health_check_failed", "resource_quota"],
            recommended_actions=[
                RecommendedAction("check_deployment_logs", "cicd", 95, {}, False, 30),
                RecommendedAction("rollback_deployment", "cicd", 85, {}, True, 120),
                RecommendedAction("fix_and_redeploy", "cicd", 70, {}, True, 600),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300,
            tags=["deployment", "failed", "release", "rollout"]
        ))
        
        # CICD-002: Build Failure
        self.add_pattern(IncidentPattern(
            pattern_id="cicd_build_failed_002",
            name="Build Failure",
            description="CI build failed",
            category=PatternCategory.CICD,
            subcategory="build",
            severity=Severity.MEDIUM,
            symptoms=[
                Symptom("event", "build failed", "contains", True, 3.0),
                Symptom("log", "compilation error", "contains", True, 2.5),
                Symptom("log", "test failed", "contains", True, 2.0),
            ],
            signals=["build failed", "compilation error", "test failed", "lint error"],
            root_causes=["code_error", "dependency_issue", "test_failure", "resource_limit"],
            recommended_actions=[
                RecommendedAction("check_build_logs", "cicd", 95, {}, False, 15),
                RecommendedAction("retry_build", "cicd", 70, {}, False, 300),
                RecommendedAction("notify_developer", "cicd", 90, {}, False, 5),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=600,
            tags=["build", "failed", "ci", "compilation"]
        ))
    
    def _add_network_patterns(self):
        """Add network-related patterns"""
        
        # Net-001: High Packet Loss
        self.add_pattern(IncidentPattern(
            pattern_id="net_packet_loss_001",
            name="High Packet Loss",
            description="Network experiencing significant packet loss",
            category=PatternCategory.NETWORK,
            subcategory="connectivity",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "packet_loss_percent", "above", 5, 3.0),
                Symptom("metric", "retransmission_rate", "above", 10, 2.5),
                Symptom("log", "connection timed out", "contains", True, 2.0),
            ],
            signals=["packet loss", "timeout", "connection refused", "unreachable"],
            root_causes=["network_congestion", "hardware_failure", "misconfiguration", "ddos"],
            recommended_actions=[
                RecommendedAction("check_network_metrics", "network", 95, {}, False, 30),
                RecommendedAction("failover_to_backup", "network", 80, {}, True, 60),
                RecommendedAction("contact_network_team", "network", 90, {}, False, 5),
            ],
            autonomous_safe=False,
            blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=600,
            tags=["packet", "loss", "network", "connectivity"]
        ))
        
        # Net-002: SSL Certificate Expiring
        self.add_pattern(IncidentPattern(
            pattern_id="net_ssl_expiry_002",
            name="SSL Certificate Expiring",
            description="SSL certificate nearing expiration",
            category=PatternCategory.NETWORK,
            subcategory="security",
            severity=Severity.HIGH,
            symptoms=[
                Symptom("metric", "ssl_days_until_expiry", "below", 7, 3.0),
                Symptom("log", "certificate expires", "contains", True, 2.5),
            ],
            signals=["certificate", "expiring", "ssl", "tls", "expiry"],
            root_causes=["auto_renewal_failed", "no_renewal_configured", "acme_error"],
            recommended_actions=[
                RecommendedAction("renew_certificate", "network", 95, {}, True, 300),
                RecommendedAction("check_acme_logs", "network", 85, {}, False, 60),
                RecommendedAction("notify_security_team", "network", 90, {}, False, 5),
            ],
            autonomous_safe=True,
            blast_radius=BlastRadius.CRITICAL,
            resolution_time_avg_seconds=600,
            tags=["ssl", "certificate", "expiry", "tls"]
        ))
    
    def _load_custom_patterns(self):
        """Load custom patterns from Redis"""
        if not self.redis:
            return
        
        try:
            pattern_keys = self.redis.keys("knowledge:pattern:*")
            for key in pattern_keys:
                data = self.redis.get(key)
                if data:
                    pattern_data = json.loads(data)
                    # Reconstruct pattern object
                    # ... (simplified for now)
        except Exception as e:
            print(f"Error loading custom patterns: {e}")
    
    def add_pattern(self, pattern: IncidentPattern):
        """Add a pattern to the knowledge base"""
        self.patterns[pattern.pattern_id] = pattern
        
        # Persist to Redis if available
        if self.redis:
            try:
                self.redis.set(
                    f"knowledge:pattern:{pattern.pattern_id}",
                    json.dumps(pattern.to_dict())
                )
            except Exception as e:
                print(f"Error saving pattern {pattern.pattern_id}: {e}")
    
    def find_matching_patterns(
        self,
        anomalies: List[Dict],
        logs: List[Dict] = None,
        min_confidence: float = 50.0
    ) -> List[tuple]:
        """
        Find patterns that match the given anomalies
        
        Returns: List of (pattern, confidence_score) tuples, sorted by confidence
        """
        matches = []
        
        for pattern_id, pattern in self.patterns.items():
            score = pattern.match_score(anomalies, logs)
            if score >= min_confidence:
                matches.append((pattern, score))
        
        # Sort by confidence score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_pattern(self, pattern_id: str) -> Optional[IncidentPattern]:
        """Get a specific pattern by ID"""
        return self.patterns.get(pattern_id)
    
    def get_patterns_by_category(self, category: PatternCategory) -> List[IncidentPattern]:
        """Get all patterns in a category"""
        return [p for p in self.patterns.values() if p.category == category]
    
    def get_autonomous_safe_patterns(self) -> List[IncidentPattern]:
        """Get all patterns that are safe for autonomous remediation"""
        return [p for p in self.patterns.values() if p.autonomous_safe]
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        stats = {
            "total_patterns": len(self.patterns),
            "by_category": {},
            "by_severity": {},
            "autonomous_safe_count": len(self.get_autonomous_safe_patterns())
        }
        
        for pattern in self.patterns.values():
            cat = pattern.category.value
            sev = pattern.severity.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
        
        return stats
    
    def export_for_training(self) -> List[Dict]:
        """Export all patterns for training purposes"""
        return [p.to_dict() for p in self.patterns.values()]


# Convenience function
def get_knowledge_base(redis_client=None) -> DevOpsKnowledgeBase:
    """Get initialized knowledge base"""
    return DevOpsKnowledgeBase(redis_client)
