"""
Extended DevOps Patterns - Additional 200+ Kubernetes Patterns
Part 1 of expanded training dataset
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_extended_kubernetes_patterns() -> List[IncidentPattern]:
    """Get extended Kubernetes patterns (100+ additional)"""
    patterns = []
    
    # ==================== POD ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_pending_pod_011",
        name="Pod Stuck in Pending",
        description="Pod cannot be scheduled due to resource constraints",
        category=PatternCategory.KUBERNETES,
        subcategory="scheduling",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "FailedScheduling", "contains", True, 3.0),
            Symptom("event", "Insufficient cpu", "contains", True, 2.5),
            Symptom("event", "Insufficient memory", "contains", True, 2.5),
        ],
        signals=["Pending", "FailedScheduling", "Insufficient", "no nodes available"],
        root_causes=["insufficient_resources", "node_selector_mismatch", "taints_tolerations", "affinity_rules"],
        recommended_actions=[
            RecommendedAction("check_node_resources", "kubernetes", 90, {}, False, 30),
            RecommendedAction("adjust_resource_requests", "kubernetes", 85, {}, False, 60),
            RecommendedAction("add_node", "cloud", 70, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["pending", "scheduling", "resources"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_container_creating_012",
        name="Container Stuck in ContainerCreating",
        description="Container cannot start, stuck in creating state",
        category=PatternCategory.KUBERNETES,
        subcategory="container",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "ContainerCreating", "contains", True, 3.0),
            Symptom("metric", "pod_phase", "equals", "Pending", 2.0),
        ],
        signals=["ContainerCreating", "MountVolume", "secret not found", "configmap not found"],
        root_causes=["volume_mount_failure", "secret_missing", "configmap_missing", "image_pull_slow"],
        recommended_actions=[
            RecommendedAction("describe_pod", "kubernetes", 95, {}, False, 10),
            RecommendedAction("check_secrets", "kubernetes", 85, {}, False, 30),
            RecommendedAction("check_configmaps", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["container", "creating", "stuck"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_init_container_fail_013",
        name="Init Container Failure",
        description="Init container failed preventing main container start",
        category=PatternCategory.KUBERNETES,
        subcategory="init_container",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "Init:Error", "contains", True, 3.0),
            Symptom("event", "Init:CrashLoopBackOff", "contains", True, 3.0),
        ],
        signals=["Init:", "init container", "initialization", "startup"],
        root_causes=["init_script_error", "dependency_unavailable", "permission_denied", "timeout"],
        recommended_actions=[
            RecommendedAction("get_init_container_logs", "kubernetes", 95, {}, False, 15),
            RecommendedAction("check_init_dependencies", "kubernetes", 85, {}, False, 60),
            RecommendedAction("restart_pod", "kubernetes", 70, {}, True, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["init", "container", "startup"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_liveness_fail_014",
        name="Liveness Probe Failure",
        description="Container killed due to liveness probe failures",
        category=PatternCategory.KUBERNETES,
        subcategory="health_probes",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Liveness probe failed", "contains", True, 3.0),
            Symptom("metric", "container_restarts", "above", 3, 2.0),
        ],
        signals=["Liveness", "probe failed", "killing", "unhealthy"],
        root_causes=["slow_startup", "resource_starvation", "deadlock", "incorrect_probe_config"],
        recommended_actions=[
            RecommendedAction("adjust_liveness_probe", "kubernetes", 85, {"initial_delay_seconds": 30}, False, 30),
            RecommendedAction("check_application_health", "kubernetes", 90, {}, False, 30),
            RecommendedAction("increase_probe_timeout", "kubernetes", 75, {}, False, 30),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["liveness", "probe", "health"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_readiness_fail_015",
        name="Readiness Probe Failure",
        description="Pod removed from service due to readiness probe failures",
        category=PatternCategory.KUBERNETES,
        subcategory="health_probes",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Readiness probe failed", "contains", True, 3.0),
            Symptom("metric", "endpoints_ready", "below", 1, 2.0),
        ],
        signals=["Readiness", "probe failed", "not ready", "removed from service"],
        root_causes=["dependency_unavailable", "slow_response", "database_connection", "warmup_time"],
        recommended_actions=[
            RecommendedAction("check_dependencies", "kubernetes", 90, {}, False, 30),
            RecommendedAction("adjust_readiness_probe", "kubernetes", 80, {}, False, 30),
            RecommendedAction("check_resource_limits", "kubernetes", 75, {}, False, 30),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["readiness", "probe", "health"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_startup_probe_fail_016",
        name="Startup Probe Failure",
        description="Container killed during startup due to probe failures",
        category=PatternCategory.KUBERNETES,
        subcategory="health_probes",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "Startup probe failed", "contains", True, 3.0),
            Symptom("event", "will be restarted", "contains", True, 2.0),
        ],
        signals=["Startup", "probe failed", "startup", "slow start"],
        root_causes=["slow_application_startup", "insufficient_startup_time", "dependency_delay"],
        recommended_actions=[
            RecommendedAction("increase_startup_probe_time", "kubernetes", 90, {"failure_threshold": 30}, False, 30),
            RecommendedAction("optimize_startup_time", "application", 70, {}, True, 600),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["startup", "probe", "slow"]
    ))
    
    # ==================== RESOURCE ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_cpu_limit_017",
        name="CPU Limit Exceeded",
        description="Container CPU usage at or near limit",
        category=PatternCategory.KUBERNETES,
        subcategory="resources",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "cpu_usage_percent", "above", 95, 2.5),
            Symptom("metric", "cpu_throttle_percent", "above", 25, 2.0),
        ],
        signals=["cpu limit", "throttling", "slow", "cpu"],
        root_causes=["insufficient_cpu_limit", "cpu_intensive_operation", "inefficient_code"],
        recommended_actions=[
            RecommendedAction("increase_cpu_limit", "kubernetes", 85, {"increase_percent": 50}, False, 30),
            RecommendedAction("scale_horizontal", "kubernetes", 80, {"replicas": 1}, False, 60),
            RecommendedAction("profile_cpu_usage", "application", 70, {}, True, 300),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=60,
        tags=["cpu", "limit", "throttle"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_memory_limit_018",
        name="Memory Near Limit",
        description="Container memory usage approaching limit",
        category=PatternCategory.KUBERNETES,
        subcategory="resources",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "memory_usage_percent", "above", 90, 3.0),
            Symptom("metric", "memory_working_set", "above", 90, 2.5),
        ],
        signals=["memory", "limit", "high memory", "approaching limit"],
        root_causes=["memory_leak", "insufficient_limit", "cache_growth", "large_dataset"],
        recommended_actions=[
            RecommendedAction("increase_memory_limit", "kubernetes", 85, {"increase_percent": 25}, False, 30),
            RecommendedAction("restart_pod", "kubernetes", 80, {}, False, 30),
            RecommendedAction("analyze_memory_usage", "application", 70, {}, True, 300),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=60,
        tags=["memory", "limit", "high"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_ephemeral_storage_019",
        name="Ephemeral Storage Exceeded",
        description="Pod using excessive ephemeral storage",
        category=PatternCategory.KUBERNETES,
        subcategory="storage",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "ephemeral-storage", "contains", True, 3.0),
            Symptom("event", "Evicted", "contains", True, 2.5),
        ],
        signals=["ephemeral-storage", "disk", "storage limit", "evicted"],
        root_causes=["log_growth", "temp_files", "cache_growth", "no_limit_set"],
        recommended_actions=[
            RecommendedAction("cleanup_logs", "kubernetes", 85, {}, False, 60),
            RecommendedAction("set_ephemeral_limit", "kubernetes", 80, {}, False, 30),
            RecommendedAction("add_log_rotation", "application", 70, {}, True, 120),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["ephemeral", "storage", "disk"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_resource_quota_020",
        name="Resource Quota Exceeded",
        description="Namespace resource quota limit reached",
        category=PatternCategory.KUBERNETES,
        subcategory="quota",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "exceeded quota", "contains", True, 3.0),
            Symptom("event", "forbidden", "contains", True, 2.0),
        ],
        signals=["quota", "exceeded", "limit", "forbidden"],
        root_causes=["quota_too_low", "resource_leak", "unexpected_growth"],
        recommended_actions=[
            RecommendedAction("check_quota_usage", "kubernetes", 95, {}, False, 15),
            RecommendedAction("increase_quota", "kubernetes", 80, {}, True, 60),
            RecommendedAction("cleanup_unused_resources", "kubernetes", 75, {}, False, 120),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["quota", "limit", "namespace"]
    ))
    
    # ==================== NETWORK ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_service_unavailable_021",
        name="Service Endpoints Unavailable",
        description="Kubernetes service has no available endpoints",
        category=PatternCategory.KUBERNETES,
        subcategory="networking",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("metric", "endpoints_ready", "equals", 0, 3.0),
            Symptom("event", "no endpoints available", "contains", True, 2.5),
        ],
        signals=["no endpoints", "service unavailable", "connection refused"],
        root_causes=["all_pods_down", "selector_mismatch", "network_policy", "readiness_failure"],
        recommended_actions=[
            RecommendedAction("check_pod_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("check_service_selector", "kubernetes", 90, {}, False, 30),
            RecommendedAction("scale_deployment", "kubernetes", 80, {"replicas": 2}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["service", "endpoints", "unavailable"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_network_policy_022",
        name="Network Policy Blocking Traffic",
        description="Network policy preventing pod communication",
        category=PatternCategory.KUBERNETES,
        subcategory="networking",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "connection refused", "contains", True, 2.5),
            Symptom("log", "connection timed out", "contains", True, 2.5),
        ],
        signals=["network policy", "blocked", "denied", "connection refused"],
        root_causes=["restrictive_policy", "missing_egress_rule", "missing_ingress_rule"],
        recommended_actions=[
            RecommendedAction("check_network_policies", "kubernetes", 95, {}, False, 30),
            RecommendedAction("test_connectivity", "kubernetes", 90, {}, False, 30),
            RecommendedAction("update_network_policy", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["network", "policy", "blocked"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_service_mesh_023",
        name="Service Mesh Sidecar Issues",
        description="Istio/Envoy sidecar causing connectivity issues",
        category=PatternCategory.KUBERNETES,
        subcategory="service_mesh",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "upstream connect error", "contains", True, 3.0),
            Symptom("log", "envoy", "contains", True, 1.5),
            Symptom("metric", "istio_requests_total", "above", 0, 1.0),
        ],
        signals=["envoy", "istio", "sidecar", "upstream", "503"],
        root_causes=["sidecar_not_ready", "mtls_misconfiguration", "destination_rule_error"],
        recommended_actions=[
            RecommendedAction("check_sidecar_status", "kubernetes", 90, {}, False, 30),
            RecommendedAction("check_destination_rules", "kubernetes", 85, {}, False, 30),
            RecommendedAction("restart_sidecar", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["istio", "envoy", "sidecar", "mesh"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_coredns_issues_024",
        name="CoreDNS Performance Issues",
        description="CoreDNS experiencing high latency or failures",
        category=PatternCategory.KUBERNETES,
        subcategory="dns",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("metric", "coredns_dns_request_duration_seconds", "above", 1, 3.0),
            Symptom("metric", "coredns_dns_responses_total", "above", 0, 1.0),
        ],
        signals=["coredns", "dns", "resolution", "timeout", "SERVFAIL"],
        root_causes=["coredns_overloaded", "upstream_dns_slow", "cache_pressure"],
        recommended_actions=[
            RecommendedAction("scale_coredns", "kubernetes", 85, {"replicas": 3}, False, 60),
            RecommendedAction("check_coredns_config", "kubernetes", 90, {}, False, 30),
            RecommendedAction("enable_dns_cache", "kubernetes", 75, {}, True, 120),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["coredns", "dns", "latency"]
    ))
    
    # ==================== STORAGE ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_pv_reclaim_025",
        name="PersistentVolume Reclaim Failed",
        description="PV stuck in Released state, cannot be reclaimed",
        category=PatternCategory.KUBERNETES,
        subcategory="storage",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Released", "contains", True, 2.5),
            Symptom("event", "reclaim", "contains", True, 2.0),
        ],
        signals=["Released", "reclaim", "PersistentVolume", "stuck"],
        root_causes=["reclaim_policy_retain", "manual_intervention_needed", "data_cleanup_required"],
        recommended_actions=[
            RecommendedAction("check_pv_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("delete_pv_claim", "kubernetes", 70, {}, True, 30),
            RecommendedAction("recreate_pv", "kubernetes", 65, {}, True, 120),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["pv", "reclaim", "storage"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_storage_class_026",
        name="StorageClass Provisioning Failed",
        description="Dynamic volume provisioning failed",
        category=PatternCategory.KUBERNETES,
        subcategory="storage",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "ProvisioningFailed", "contains", True, 3.0),
            Symptom("event", "failed to provision volume", "contains", True, 2.5),
        ],
        signals=["ProvisioningFailed", "StorageClass", "provisioner", "volume"],
        root_causes=["provisioner_error", "quota_exceeded", "storage_backend_issue"],
        recommended_actions=[
            RecommendedAction("check_storage_class", "kubernetes", 90, {}, False, 30),
            RecommendedAction("check_provisioner_logs", "kubernetes", 85, {}, False, 30),
            RecommendedAction("use_different_storage_class", "kubernetes", 70, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["storageclass", "provisioning", "pvc"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_volume_mount_027",
        name="Volume Mount Failure",
        description="Pod cannot mount required volume",
        category=PatternCategory.KUBERNETES,
        subcategory="storage",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "MountVolume.SetUp failed", "contains", True, 3.0),
            Symptom("event", "Unable to attach or mount volumes", "contains", True, 2.5),
        ],
        signals=["MountVolume", "mount failed", "attach", "volumes"],
        root_causes=["volume_already_attached", "node_issue", "permission_denied", "path_not_found"],
        recommended_actions=[
            RecommendedAction("describe_pod", "kubernetes", 95, {}, False, 10),
            RecommendedAction("check_node_status", "kubernetes", 85, {}, False, 30),
            RecommendedAction("force_detach_volume", "kubernetes", 70, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["volume", "mount", "attach"]
    ))
    
    # ==================== DEPLOYMENT ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_rollout_stuck_028",
        name="Deployment Rollout Stuck",
        description="Deployment rollout not progressing",
        category=PatternCategory.KUBERNETES,
        subcategory="deployment",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "ProgressDeadlineExceeded", "contains", True, 3.0),
            Symptom("metric", "deployment_replicas_unavailable", "above", 0, 2.0),
        ],
        signals=["ProgressDeadlineExceeded", "rollout", "stuck", "not progressing"],
        root_causes=["insufficient_resources", "image_pull_error", "crash_loop", "deadline_too_short"],
        recommended_actions=[
            RecommendedAction("check_rollout_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("describe_deployment", "kubernetes", 90, {}, False, 10),
            RecommendedAction("rollback_deployment", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["deployment", "rollout", "stuck"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_replica_mismatch_029",
        name="Replica Count Mismatch",
        description="Actual replicas not matching desired replicas",
        category=PatternCategory.KUBERNETES,
        subcategory="deployment",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "deployment_replicas_available", "below", "deployment_replicas_desired", 3.0),
            Symptom("event", "FailedCreate", "contains", True, 2.0),
        ],
        signals=["replica", "mismatch", "unavailable", "FailedCreate"],
        root_causes=["resource_quota", "scheduling_failure", "pod_disruption_budget"],
        recommended_actions=[
            RecommendedAction("check_events", "kubernetes", 95, {}, False, 15),
            RecommendedAction("check_resource_quota", "kubernetes", 85, {}, False, 30),
            RecommendedAction("scale_deployment", "kubernetes", 80, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["replica", "deployment", "scale"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_config_change_030",
        name="ConfigMap/Secret Change Not Applied",
        description="Application not picking up configuration changes",
        category=PatternCategory.KUBERNETES,
        subcategory="configuration",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("log", "old config", "contains", True, 2.0),
            Symptom("event", "ConfigMap updated", "contains", True, 1.5),
        ],
        signals=["configmap", "secret", "reload", "config change"],
        root_causes=["no_config_reload", "volume_not_updated", "env_from_not_refreshed"],
        recommended_actions=[
            RecommendedAction("restart_pods", "kubernetes", 85, {}, False, 60),
            RecommendedAction("use_reloader", "kubernetes", 75, {}, True, 120),
            RecommendedAction("trigger_config_reload", "application", 80, {}, False, 30),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["configmap", "secret", "config"]
    ))
    
    # ==================== NODE ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_node_disk_pressure_031",
        name="Node Disk Pressure",
        description="Node experiencing disk pressure",
        category=PatternCategory.KUBERNETES,
        subcategory="node",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "DiskPressure", "contains", True, 3.0),
            Symptom("metric", "node_disk_usage_percent", "above", 85, 2.5),
        ],
        signals=["DiskPressure", "disk", "storage", "eviction"],
        root_causes=["log_accumulation", "image_cache", "container_logs", "emptydir_growth"],
        recommended_actions=[
            RecommendedAction("cleanup_node_disk", "kubernetes", 85, {}, False, 120),
            RecommendedAction("prune_unused_images", "kubernetes", 80, {}, False, 60),
            RecommendedAction("cordon_and_drain", "kubernetes", 70, {}, True, 180),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["node", "disk", "pressure"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_node_memory_pressure_032",
        name="Node Memory Pressure",
        description="Node experiencing memory pressure",
        category=PatternCategory.KUBERNETES,
        subcategory="node",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "MemoryPressure", "contains", True, 3.0),
            Symptom("metric", "node_memory_usage_percent", "above", 90, 2.5),
        ],
        signals=["MemoryPressure", "memory", "eviction", "oom"],
        root_causes=["overcommit", "memory_leak", "burst_traffic", "too_many_pods"],
        recommended_actions=[
            RecommendedAction("identify_memory_heavy_pods", "kubernetes", 90, {}, False, 30),
            RecommendedAction("evict_low_priority_pods", "kubernetes", 75, {}, True, 60),
            RecommendedAction("add_node", "cloud", 70, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=180,
        tags=["node", "memory", "pressure"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_node_pid_pressure_033",
        name="Node PID Pressure",
        description="Node running out of available PIDs",
        category=PatternCategory.KUBERNETES,
        subcategory="node",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("event", "PIDPressure", "contains", True, 3.0),
            Symptom("log", "cannot allocate memory", "contains", True, 2.0),
        ],
        signals=["PIDPressure", "pid", "process", "fork"],
        root_causes=["process_leak", "zombie_processes", "too_many_containers"],
        recommended_actions=[
            RecommendedAction("identify_pid_heavy_pods", "kubernetes", 90, {}, False, 30),
            RecommendedAction("restart_affected_pods", "kubernetes", 80, {}, True, 60),
            RecommendedAction("check_for_zombies", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=180,
        tags=["node", "pid", "process"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_node_network_unavailable_034",
        name="Node Network Unavailable",
        description="Node CNI or network not ready",
        category=PatternCategory.KUBERNETES,
        subcategory="node",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("event", "NetworkUnavailable", "contains", True, 3.0),
            Symptom("event", "network not ready", "contains", True, 2.5),
        ],
        signals=["NetworkUnavailable", "CNI", "network not ready", "calico", "flannel"],
        root_causes=["cni_failure", "cni_not_installed", "network_plugin_crash"],
        recommended_actions=[
            RecommendedAction("check_cni_status", "kubernetes", 95, {}, False, 30),
            RecommendedAction("restart_cni_pods", "kubernetes", 80, {}, True, 60),
            RecommendedAction("cordon_node", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=300,
        tags=["node", "network", "cni"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_kubelet_not_ready_035",
        name="Kubelet Not Ready",
        description="Kubelet on node is not responding",
        category=PatternCategory.KUBERNETES,
        subcategory="node",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("event", "NodeNotReady", "contains", True, 3.0),
            Symptom("log", "kubelet", "contains", True, 1.5),
        ],
        signals=["kubelet", "NotReady", "node status", "heartbeat"],
        root_causes=["kubelet_crash", "kubelet_overloaded", "disk_full", "certificate_expired"],
        recommended_actions=[
            RecommendedAction("check_kubelet_logs", "kubernetes", 95, {}, False, 30),
            RecommendedAction("restart_kubelet", "kubernetes", 80, {}, True, 60),
            RecommendedAction("drain_node", "kubernetes", 70, {}, True, 180),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=300,
        tags=["kubelet", "node", "notready"]
    ))
    
    # ==================== RBAC/SECURITY ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_rbac_denied_036",
        name="RBAC Permission Denied",
        description="Operation denied due to RBAC restrictions",
        category=PatternCategory.KUBERNETES,
        subcategory="rbac",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("log", "forbidden", "contains", True, 3.0),
            Symptom("log", "cannot", "contains", True, 2.0),
        ],
        signals=["forbidden", "RBAC", "cannot", "User cannot", "permission denied"],
        root_causes=["missing_role_binding", "wrong_service_account", "restrictive_policy"],
        recommended_actions=[
            RecommendedAction("check_rbac_permissions", "kubernetes", 95, {}, False, 30),
            RecommendedAction("check_service_account", "kubernetes", 90, {}, False, 15),
            RecommendedAction("create_role_binding", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["rbac", "permission", "forbidden"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_psp_violation_037",
        name="Pod Security Policy Violation",
        description="Pod creation blocked by security policy",
        category=PatternCategory.KUBERNETES,
        subcategory="security",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "PodSecurityPolicy", "contains", True, 3.0),
            Symptom("event", "forbidden", "contains", True, 2.5),
        ],
        signals=["PodSecurityPolicy", "PSP", "security context", "forbidden"],
        root_causes=["privileged_container", "host_network", "root_user", "capability_error"],
        recommended_actions=[
            RecommendedAction("check_security_context", "kubernetes", 90, {}, False, 30),
            RecommendedAction("assign_appropriate_psp", "kubernetes", 80, {}, True, 60),
            RecommendedAction("modify_pod_spec", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["psp", "security", "policy"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_secret_not_found_038",
        name="Secret Not Found",
        description="Pod cannot start due to missing secret",
        category=PatternCategory.KUBERNETES,
        subcategory="secrets",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "secret", "contains", True, 2.5),
            Symptom("event", "not found", "contains", True, 2.5),
        ],
        signals=["secret", "not found", "MountVolume", "CreateContainerConfigError"],
        root_causes=["secret_not_created", "wrong_secret_name", "wrong_namespace"],
        recommended_actions=[
            RecommendedAction("list_secrets", "kubernetes", 95, {}, False, 15),
            RecommendedAction("check_secret_name", "kubernetes", 90, {}, False, 15),
            RecommendedAction("create_missing_secret", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["secret", "missing", "configuration"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_cert_expired_039",
        name="Certificate Expired",
        description="Kubernetes certificate has expired",
        category=PatternCategory.KUBERNETES,
        subcategory="certificates",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "certificate has expired", "contains", True, 3.0),
            Symptom("log", "x509", "contains", True, 2.0),
        ],
        signals=["certificate", "expired", "x509", "tls"],
        root_causes=["cert_not_renewed", "auto_renewal_failed", "ca_expired"],
        recommended_actions=[
            RecommendedAction("check_certificate_expiry", "kubernetes", 95, {}, False, 15),
            RecommendedAction("renew_certificates", "kubernetes", 85, {}, True, 300),
            RecommendedAction("restart_control_plane", "kubernetes", 70, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=600,
        tags=["certificate", "expired", "tls"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_admission_webhook_040",
        name="Admission Webhook Failure",
        description="Admission webhook blocking or timing out",
        category=PatternCategory.KUBERNETES,
        subcategory="webhooks",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("event", "admission webhook", "contains", True, 3.0),
            Symptom("event", "denied the request", "contains", True, 2.5),
        ],
        signals=["admission webhook", "denied", "timeout", "mutating", "validating"],
        root_causes=["webhook_unavailable", "webhook_timeout", "webhook_rejection"],
        recommended_actions=[
            RecommendedAction("check_webhook_status", "kubernetes", 95, {}, False, 30),
            RecommendedAction("check_webhook_logs", "kubernetes", 90, {}, False, 30),
            RecommendedAction("disable_failing_webhook", "kubernetes", 70, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=180,
        tags=["webhook", "admission", "validation"]
    ))
    
    # ==================== WORKLOAD ISSUES ====================
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_job_failed_041",
        name="Job Failed",
        description="Kubernetes Job failed to complete",
        category=PatternCategory.KUBERNETES,
        subcategory="jobs",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Job has reached the specified backoff limit", "contains", True, 3.0),
            Symptom("metric", "job_failed", "above", 0, 2.5),
        ],
        signals=["Job", "failed", "backoff limit", "FailedCreate"],
        root_causes=["application_error", "resource_issue", "timeout", "dependency_failure"],
        recommended_actions=[
            RecommendedAction("check_job_logs", "kubernetes", 95, {}, False, 30),
            RecommendedAction("describe_job", "kubernetes", 90, {}, False, 15),
            RecommendedAction("retry_job", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["job", "failed", "batch"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_cronjob_missed_042",
        name="CronJob Missed Schedule",
        description="CronJob missed its scheduled execution",
        category=PatternCategory.KUBERNETES,
        subcategory="cronjobs",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Missed scheduled time", "contains", True, 3.0),
            Symptom("metric", "cronjob_last_schedule_time", "below", "expected", 2.0),
        ],
        signals=["CronJob", "missed", "schedule", "too many missed"],
        root_causes=["controller_overload", "concurrency_policy", "deadline_exceeded"],
        recommended_actions=[
            RecommendedAction("check_cronjob_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("trigger_manual_run", "kubernetes", 80, {}, False, 30),
            RecommendedAction("adjust_deadline", "kubernetes", 70, {}, True, 60),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=120,
        tags=["cronjob", "missed", "schedule"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_statefulset_stuck_043",
        name="StatefulSet Update Stuck",
        description="StatefulSet rolling update not progressing",
        category=PatternCategory.KUBERNETES,
        subcategory="statefulset",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "statefulset_replicas_ready", "below", "statefulset_replicas", 3.0),
            Symptom("event", "StatefulSet", "contains", True, 1.5),
        ],
        signals=["StatefulSet", "update", "stuck", "not ready"],
        root_causes=["pvc_issue", "previous_pod_not_ready", "volume_attachment"],
        recommended_actions=[
            RecommendedAction("check_pod_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("check_pvc_status", "kubernetes", 90, {}, False, 30),
            RecommendedAction("delete_stuck_pod", "kubernetes", 75, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=300,
        tags=["statefulset", "update", "stuck"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_daemonset_not_scheduled_044",
        name="DaemonSet Pod Not Scheduled",
        description="DaemonSet pod cannot be scheduled on nodes",
        category=PatternCategory.KUBERNETES,
        subcategory="daemonset",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "daemonset_number_unavailable", "above", 0, 3.0),
            Symptom("event", "FailedScheduling", "contains", True, 2.0),
        ],
        signals=["DaemonSet", "not scheduled", "FailedScheduling", "toleration"],
        root_causes=["taints_without_tolerations", "node_selector_mismatch", "resource_constraints"],
        recommended_actions=[
            RecommendedAction("check_node_taints", "kubernetes", 90, {}, False, 30),
            RecommendedAction("add_tolerations", "kubernetes", 80, {}, True, 60),
            RecommendedAction("check_resource_requests", "kubernetes", 75, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["daemonset", "scheduling", "taints"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_pdb_violation_045",
        name="PodDisruptionBudget Violation",
        description="Eviction blocked by PodDisruptionBudget",
        category=PatternCategory.KUBERNETES,
        subcategory="disruption",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("event", "Cannot evict pod", "contains", True, 3.0),
            Symptom("event", "PodDisruptionBudget", "contains", True, 2.5),
        ],
        signals=["PodDisruptionBudget", "PDB", "cannot evict", "disruption"],
        root_causes=["pdb_too_restrictive", "insufficient_replicas", "unhealthy_pods"],
        recommended_actions=[
            RecommendedAction("check_pdb_status", "kubernetes", 95, {}, False, 15),
            RecommendedAction("scale_up_first", "kubernetes", 80, {"replicas": 1}, True, 60),
            RecommendedAction("adjust_pdb", "kubernetes", 70, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["pdb", "disruption", "eviction"]
    ))
    
    # Add more patterns...
    patterns.append(IncidentPattern(
        pattern_id="k8s_api_server_slow_046",
        name="API Server Slow Response",
        description="Kubernetes API server responding slowly",
        category=PatternCategory.KUBERNETES,
        subcategory="control_plane",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "apiserver_request_latencies_bucket", "above", 1000, 3.0),
            Symptom("log", "slow", "contains", True, 1.5),
        ],
        signals=["api server", "slow", "latency", "timeout"],
        root_causes=["etcd_slow", "high_load", "webhook_slow", "audit_logging"],
        recommended_actions=[
            RecommendedAction("check_etcd_health", "kubernetes", 90, {}, False, 30),
            RecommendedAction("check_api_server_metrics", "kubernetes", 95, {}, False, 15),
            RecommendedAction("scale_api_servers", "kubernetes", 70, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=300,
        tags=["api", "server", "slow"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_etcd_slow_047",
        name="ETCD Slow or Unhealthy",
        description="ETCD cluster experiencing issues",
        category=PatternCategory.KUBERNETES,
        subcategory="control_plane",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("metric", "etcd_disk_wal_fsync_duration_seconds", "above", 0.1, 3.0),
            Symptom("log", "etcd", "contains", True, 1.5),
        ],
        signals=["etcd", "slow", "disk", "leader election", "quorum"],
        root_causes=["disk_io_slow", "network_latency", "leader_election", "compaction"],
        recommended_actions=[
            RecommendedAction("check_etcd_metrics", "kubernetes", 95, {}, False, 30),
            RecommendedAction("defragment_etcd", "kubernetes", 75, {}, True, 600),
            RecommendedAction("check_disk_io", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=600,
        tags=["etcd", "control", "plane"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_scheduler_failure_048",
        name="Scheduler Failure",
        description="Kubernetes scheduler not functioning properly",
        category=PatternCategory.KUBERNETES,
        subcategory="control_plane",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("event", "FailedScheduling", "contains", True, 3.0),
            Symptom("log", "scheduler", "contains", True, 1.5),
        ],
        signals=["scheduler", "FailedScheduling", "no nodes available"],
        root_causes=["scheduler_crash", "leader_election_issue", "resource_exhaustion"],
        recommended_actions=[
            RecommendedAction("check_scheduler_logs", "kubernetes", 95, {}, False, 30),
            RecommendedAction("restart_scheduler", "kubernetes", 80, {}, True, 60),
            RecommendedAction("check_leader_election", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=300,
        tags=["scheduler", "control", "plane"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_controller_manager_049",
        name="Controller Manager Issues",
        description="Kubernetes controller manager not reconciling",
        category=PatternCategory.KUBERNETES,
        subcategory="control_plane",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "controller-manager", "contains", True, 2.0),
            Symptom("metric", "workqueue_depth", "above", 100, 2.5),
        ],
        signals=["controller-manager", "reconcile", "workqueue", "sync"],
        root_causes=["controller_overloaded", "api_server_slow", "resource_contention"],
        recommended_actions=[
            RecommendedAction("check_controller_logs", "kubernetes", 95, {}, False, 30),
            RecommendedAction("restart_controller_manager", "kubernetes", 75, {}, True, 120),
            RecommendedAction("check_workqueue_metrics", "kubernetes", 85, {}, False, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=300,
        tags=["controller", "manager", "control", "plane"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="k8s_namespace_terminating_050",
        name="Namespace Stuck in Terminating",
        description="Namespace cannot be deleted, stuck in Terminating state",
        category=PatternCategory.KUBERNETES,
        subcategory="namespace",
        severity=Severity.LOW,
        symptoms=[
            Symptom("event", "Terminating", "contains", True, 2.0),
            Symptom("metric", "namespace_phase", "equals", "Terminating", 3.0),
        ],
        signals=["Terminating", "namespace", "stuck", "finalizer"],
        root_causes=["finalizer_stuck", "resources_remaining", "api_resources_pending"],
        recommended_actions=[
            RecommendedAction("check_remaining_resources", "kubernetes", 95, {}, False, 30),
            RecommendedAction("remove_finalizers", "kubernetes", 75, {}, True, 60),
            RecommendedAction("delete_stuck_resources", "kubernetes", 80, {}, True, 120),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["namespace", "terminating", "stuck"]
    ))
    
    return patterns
