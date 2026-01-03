"""
Additional Kubernetes Patterns - 100 more patterns
Covers advanced scenarios, operators, and edge cases
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_kubernetes_patterns_batch2() -> List[IncidentPattern]:
    """100 additional Kubernetes patterns"""
    patterns = []
    
    # Generate patterns programmatically for efficiency
    k8s_scenarios = [
        # Pod lifecycle issues (131-150)
        ("k8s_pod_terminating_stuck_131", "Pod Stuck Terminating", "Pod won't delete, stuck in Terminating", "pod", Severity.MEDIUM, ["Terminating", "finalizer"], True),
        ("k8s_pod_unknown_state_132", "Pod Unknown State", "Pod in Unknown state", "pod", Severity.HIGH, ["Unknown", "node unreachable"], False),
        ("k8s_container_waiting_133", "Container Waiting", "Container stuck in Waiting state", "container", Severity.MEDIUM, ["Waiting", "ContainerCreating"], True),
        ("k8s_sidecar_crash_134", "Sidecar Container Crash", "Sidecar container repeatedly crashing", "sidecar", Severity.HIGH, ["sidecar", "crash", "envoy"], False),
        ("k8s_preemption_135", "Pod Preemption", "Pod preempted by higher priority pod", "scheduling", Severity.MEDIUM, ["Preempted", "priority"], True),
        ("k8s_affinity_conflict_136", "Affinity Conflict", "Pod can't be scheduled due to affinity rules", "scheduling", Severity.MEDIUM, ["affinity", "anti-affinity"], False),
        ("k8s_toleration_missing_137", "Missing Toleration", "Pod can't tolerate node taints", "scheduling", Severity.MEDIUM, ["toleration", "taint"], False),
        ("k8s_priority_class_138", "Priority Class Issue", "Priority class not found", "scheduling", Severity.LOW, ["PriorityClass", "not found"], False),
        ("k8s_pod_topology_139", "Topology Spread Constraint", "Pod violates topology spread", "scheduling", Severity.LOW, ["topology", "spread"], False),
        ("k8s_runtime_class_140", "Runtime Class Not Found", "Specified runtime class missing", "runtime", Severity.MEDIUM, ["RuntimeClass", "not found"], False),
        
        # Service and networking (141-160)
        ("k8s_svc_no_selector_141", "Service No Selector Match", "Service selector matches no pods", "service", Severity.HIGH, ["no endpoints", "selector"], False),
        ("k8s_headless_svc_142", "Headless Service Issue", "Headless service DNS not resolving", "service", Severity.HIGH, ["headless", "DNS"], False),
        ("k8s_external_name_143", "ExternalName Resolution", "ExternalName service not resolving", "service", Severity.MEDIUM, ["ExternalName", "CNAME"], False),
        ("k8s_nodeport_conflict_144", "NodePort Conflict", "NodePort already in use", "service", Severity.HIGH, ["NodePort", "conflict", "in use"], False),
        ("k8s_loadbalancer_pending_145", "LoadBalancer Pending", "LoadBalancer service stuck pending", "service", Severity.HIGH, ["LoadBalancer", "Pending"], False),
        ("k8s_ingress_class_146", "Ingress Class Not Found", "Specified ingress class missing", "ingress", Severity.MEDIUM, ["IngressClass", "not found"], False),
        ("k8s_ingress_tls_147", "Ingress TLS Error", "Ingress TLS certificate issue", "ingress", Severity.HIGH, ["TLS", "certificate", "secret"], False),
        ("k8s_ingress_backend_148", "Ingress Backend Error", "Ingress backend service unavailable", "ingress", Severity.HIGH, ["backend", "503", "unavailable"], False),
        ("k8s_calico_policy_149", "Calico Network Policy", "Calico blocking traffic", "cni", Severity.HIGH, ["calico", "GlobalNetworkPolicy"], False),
        ("k8s_flannel_error_150", "Flannel CNI Error", "Flannel CNI plugin error", "cni", Severity.CRITICAL, ["flannel", "CNI", "error"], False),
        
        # Storage advanced (151-170)
        ("k8s_csi_driver_151", "CSI Driver Missing", "CSI driver not installed", "storage", Severity.HIGH, ["CSI", "driver", "not found"], False),
        ("k8s_csi_timeout_152", "CSI Operation Timeout", "CSI volume operation timed out", "storage", Severity.HIGH, ["CSI", "timeout", "volume"], False),
        ("k8s_snapshot_failed_153", "Volume Snapshot Failed", "Volume snapshot creation failed", "storage", Severity.MEDIUM, ["VolumeSnapshot", "failed"], False),
        ("k8s_snapshot_restore_154", "Snapshot Restore Failed", "Failed to restore from snapshot", "storage", Severity.HIGH, ["restore", "snapshot", "failed"], False),
        ("k8s_resize_failed_155", "PVC Resize Failed", "PVC expansion failed", "storage", Severity.MEDIUM, ["resize", "expansion", "failed"], False),
        ("k8s_storage_limit_156", "Storage Limit Reached", "Namespace storage quota exceeded", "storage", Severity.HIGH, ["storage", "quota", "exceeded"], False),
        ("k8s_nfs_mount_157", "NFS Mount Failure", "NFS volume mount failed", "storage", Severity.HIGH, ["NFS", "mount", "failed"], False),
        ("k8s_iscsi_error_158", "iSCSI Volume Error", "iSCSI volume attachment failed", "storage", Severity.HIGH, ["iSCSI", "attach", "failed"], False),
        ("k8s_hostpath_perm_159", "HostPath Permission Denied", "HostPath volume permission denied", "storage", Severity.MEDIUM, ["hostPath", "permission"], False),
        ("k8s_emptydir_limit_160", "EmptyDir Size Exceeded", "EmptyDir volume size exceeded", "storage", Severity.MEDIUM, ["emptyDir", "sizeLimit"], True),
        
        # Autoscaling advanced (161-180)
        ("k8s_hpa_behavior_161", "HPA Scaling Behavior", "HPA scaling too aggressively", "hpa", Severity.MEDIUM, ["HPA", "scaling", "behavior"], True),
        ("k8s_hpa_external_162", "HPA External Metrics", "HPA external metrics unavailable", "hpa", Severity.MEDIUM, ["external metrics", "HPA"], False),
        ("k8s_vpa_oom_163", "VPA OOM Recommendation", "VPA recommending memory increase", "vpa", Severity.MEDIUM, ["VPA", "recommendation", "memory"], True),
        ("k8s_vpa_update_164", "VPA Update Mode", "VPA updating pod resources", "vpa", Severity.LOW, ["VPA", "update", "recreate"], True),
        ("k8s_cluster_autoscaler_165", "Cluster Autoscaler Delay", "Cluster autoscaler scaling slowly", "autoscaler", Severity.MEDIUM, ["cluster-autoscaler", "scale up"], False),
        ("k8s_ca_node_group_166", "Node Group Scale Limit", "Node group at maximum size", "autoscaler", Severity.HIGH, ["max size", "node group"], False),
        ("k8s_ca_underutilized_167", "Underutilized Nodes", "Nodes underutilized, scale down candidate", "autoscaler", Severity.LOW, ["underutilized", "scale down"], True),
        ("k8s_keda_scaler_168", "KEDA Scaler Error", "KEDA external scaler failing", "keda", Severity.MEDIUM, ["KEDA", "scaler", "error"], False),
        ("k8s_keda_trigger_169", "KEDA Trigger Auth", "KEDA trigger authentication failed", "keda", Severity.HIGH, ["KEDA", "TriggerAuthentication"], False),
        ("k8s_metrics_adapter_170", "Custom Metrics Adapter", "Custom metrics adapter unavailable", "metrics", Severity.MEDIUM, ["metrics-adapter", "custom metrics"], False),
        
        # Security advanced (171-190)
        ("k8s_opa_violation_171", "OPA Policy Violation", "OPA Gatekeeper blocking resource", "opa", Severity.MEDIUM, ["OPA", "Gatekeeper", "violation"], False),
        ("k8s_opa_constraint_172", "OPA Constraint Error", "OPA constraint template error", "opa", Severity.LOW, ["ConstraintTemplate", "error"], False),
        ("k8s_falco_alert_173", "Falco Security Alert", "Falco detected suspicious activity", "security", Severity.HIGH, ["Falco", "alert", "suspicious"], False),
        ("k8s_trivy_vuln_174", "Trivy Vulnerability", "Trivy found critical vulnerability", "security", Severity.HIGH, ["Trivy", "CVE", "critical"], False),
        ("k8s_sealed_secret_175", "Sealed Secret Error", "Sealed secret decryption failed", "secrets", Severity.HIGH, ["SealedSecret", "decrypt", "failed"], False),
        ("k8s_vault_inject_176", "Vault Sidecar Inject", "Vault sidecar injection failed", "secrets", Severity.HIGH, ["vault", "inject", "sidecar"], False),
        ("k8s_external_secret_177", "External Secret Sync", "External secret sync failed", "secrets", Severity.HIGH, ["ExternalSecret", "sync", "failed"], False),
        ("k8s_cert_manager_178", "Cert Manager Issue", "Cert-manager certificate issuance failed", "certs", Severity.HIGH, ["cert-manager", "Certificate", "failed"], False),
        ("k8s_issuer_error_179", "Certificate Issuer Error", "ClusterIssuer configuration error", "certs", Severity.HIGH, ["ClusterIssuer", "error"], False),
        ("k8s_acme_challenge_180", "ACME Challenge Failed", "Let's Encrypt ACME challenge failed", "certs", Severity.HIGH, ["ACME", "challenge", "failed"], False),
        
        # Operators and CRDs (181-200)
        ("k8s_operator_crash_181", "Operator Crash", "Kubernetes operator crashing", "operator", Severity.HIGH, ["operator", "crash", "reconcile"], False),
        ("k8s_crd_missing_182", "CRD Not Found", "Custom Resource Definition missing", "crd", Severity.HIGH, ["CRD", "CustomResourceDefinition", "not found"], False),
        ("k8s_crd_validation_183", "CRD Validation Error", "Custom resource failed validation", "crd", Severity.MEDIUM, ["validation", "CRD", "spec"], False),
        ("k8s_finalizer_stuck_184", "Finalizer Blocking Delete", "Finalizer preventing resource deletion", "operator", Severity.MEDIUM, ["finalizer", "delete", "stuck"], False),
        ("k8s_reconcile_error_185", "Reconcile Loop Error", "Controller reconcile loop failing", "operator", Severity.HIGH, ["reconcile", "error", "controller"], False),
        ("k8s_leader_election_186", "Leader Election Failed", "Operator leader election failed", "operator", Severity.HIGH, ["leader election", "failed"], False),
        ("k8s_prometheus_op_187", "Prometheus Operator Error", "Prometheus operator issue", "monitoring", Severity.MEDIUM, ["prometheus-operator", "ServiceMonitor"], False),
        ("k8s_alertmanager_188", "AlertManager Config Error", "AlertManager configuration invalid", "monitoring", Severity.MEDIUM, ["AlertManager", "config", "invalid"], False),
        ("k8s_grafana_ds_189", "Grafana Datasource Error", "Grafana datasource connection failed", "monitoring", Severity.LOW, ["Grafana", "datasource", "error"], False),
        ("k8s_fluentd_buffer_190", "Fluentd Buffer Overflow", "Fluentd buffer queue full", "logging", Severity.MEDIUM, ["fluentd", "buffer", "overflow"], True),
        
        # Advanced workloads (191-210)
        ("k8s_argo_workflow_191", "Argo Workflow Failed", "Argo workflow execution failed", "workflow", Severity.MEDIUM, ["Argo", "Workflow", "failed"], False),
        ("k8s_argo_rollout_192", "Argo Rollout Degraded", "Argo rollout in degraded state", "deployment", Severity.HIGH, ["Argo", "Rollout", "Degraded"], False),
        ("k8s_tekton_pipeline_193", "Tekton Pipeline Failed", "Tekton pipeline run failed", "pipeline", Severity.MEDIUM, ["Tekton", "PipelineRun", "failed"], False),
        ("k8s_flux_reconcile_194", "Flux Reconciliation Failed", "Flux GitOps reconciliation failed", "gitops", Severity.HIGH, ["Flux", "reconciliation", "failed"], False),
        ("k8s_argocd_sync_195", "ArgoCD Sync Failed", "ArgoCD application sync failed", "gitops", Severity.HIGH, ["ArgoCD", "sync", "OutOfSync"], False),
        ("k8s_argocd_health_196", "ArgoCD App Unhealthy", "ArgoCD application health degraded", "gitops", Severity.MEDIUM, ["ArgoCD", "Degraded", "health"], False),
        ("k8s_knative_serving_197", "Knative Service Error", "Knative serving revision failed", "serverless", Severity.HIGH, ["Knative", "Serving", "revision"], False),
        ("k8s_knative_scale_198", "Knative Scaling Issue", "Knative autoscaling not working", "serverless", Severity.MEDIUM, ["Knative", "autoscaler", "scale"], False),
        ("k8s_istio_virtualservice_199", "Istio VirtualService Error", "Istio VirtualService misconfigured", "mesh", Severity.HIGH, ["Istio", "VirtualService", "error"], False),
        ("k8s_istio_destinationrule_200", "Istio DestinationRule Error", "Istio DestinationRule issue", "mesh", Severity.HIGH, ["Istio", "DestinationRule", "error"], False),
        
        # More edge cases (201-230)
        ("k8s_limit_range_201", "LimitRange Violation", "Pod exceeds namespace LimitRange", "quota", Severity.MEDIUM, ["LimitRange", "exceeded"], False),
        ("k8s_resource_quota_cpu_202", "CPU Quota Exceeded", "Namespace CPU quota exceeded", "quota", Severity.HIGH, ["ResourceQuota", "cpu"], False),
        ("k8s_resource_quota_mem_203", "Memory Quota Exceeded", "Namespace memory quota exceeded", "quota", Severity.HIGH, ["ResourceQuota", "memory"], False),
        ("k8s_service_account_204", "ServiceAccount Not Found", "Pod ServiceAccount missing", "rbac", Severity.HIGH, ["ServiceAccount", "not found"], False),
        ("k8s_token_mount_205", "Token Mount Failed", "ServiceAccount token mount failed", "rbac", Severity.HIGH, ["token", "mount", "failed"], False),
        ("k8s_api_deprecated_206", "Deprecated API Version", "Using deprecated Kubernetes API", "api", Severity.LOW, ["deprecated", "API", "version"], False),
        ("k8s_api_removed_207", "Removed API Version", "Using removed Kubernetes API", "api", Severity.HIGH, ["removed", "API", "no longer served"], False),
        ("k8s_mutating_webhook_208", "Mutating Webhook Error", "Mutating webhook modifying incorrectly", "webhook", Severity.MEDIUM, ["MutatingWebhook", "error"], False),
        ("k8s_validating_timeout_209", "Validating Webhook Timeout", "Validating webhook timing out", "webhook", Severity.HIGH, ["ValidatingWebhook", "timeout"], False),
        ("k8s_conversion_webhook_210", "Conversion Webhook Error", "CRD conversion webhook failed", "webhook", Severity.HIGH, ["conversion", "webhook", "failed"], False),
        ("k8s_aggregated_api_211", "Aggregated API Error", "Aggregated API server unavailable", "api", Severity.HIGH, ["APIService", "unavailable"], False),
        ("k8s_audit_log_212", "Audit Log Full", "Kubernetes audit log disk full", "audit", Severity.MEDIUM, ["audit", "log", "disk full"], True),
        ("k8s_etcd_backup_213", "ETCD Backup Failed", "ETCD backup job failed", "backup", Severity.HIGH, ["etcd", "backup", "failed"], False),
        ("k8s_velero_backup_214", "Velero Backup Failed", "Velero cluster backup failed", "backup", Severity.HIGH, ["Velero", "backup", "failed"], False),
        ("k8s_velero_restore_215", "Velero Restore Failed", "Velero restore operation failed", "backup", Severity.HIGH, ["Velero", "restore", "failed"], False),
        ("k8s_node_taint_216", "Node Taint Effect", "Node taint preventing scheduling", "node", Severity.MEDIUM, ["taint", "NoSchedule", "NoExecute"], False),
        ("k8s_node_cordon_217", "Node Cordoned", "Node cordoned, new pods not scheduled", "node", Severity.LOW, ["cordon", "SchedulingDisabled"], True),
        ("k8s_node_drain_218", "Node Drain Stuck", "Node drain operation stuck", "node", Severity.MEDIUM, ["drain", "evicting", "PDB"], False),
        ("k8s_kubelet_config_219", "Kubelet Config Error", "Kubelet configuration invalid", "node", Severity.HIGH, ["kubelet", "config", "error"], False),
        ("k8s_containerd_220", "Containerd Error", "Containerd runtime error", "runtime", Severity.CRITICAL, ["containerd", "error", "runtime"], False),
        ("k8s_docker_socket_221", "Docker Socket Error", "Docker socket unavailable", "runtime", Severity.CRITICAL, ["docker.sock", "unavailable"], False),
        ("k8s_crio_error_222", "CRI-O Runtime Error", "CRI-O container runtime error", "runtime", Severity.CRITICAL, ["cri-o", "error", "runtime"], False),
        ("k8s_node_lease_223", "Node Lease Expired", "Node lease not renewed", "node", Severity.HIGH, ["Lease", "expired", "heartbeat"], False),
        ("k8s_endpoint_slice_224", "EndpointSlice Error", "EndpointSlice not updated", "service", Severity.MEDIUM, ["EndpointSlice", "stale"], False),
        ("k8s_service_mesh_mtls_225", "mTLS Handshake Failed", "Service mesh mTLS handshake failed", "mesh", Severity.HIGH, ["mTLS", "handshake", "certificate"], False),
        ("k8s_pod_security_std_226", "Pod Security Standard", "Pod violates security standard", "security", Severity.MEDIUM, ["PodSecurity", "violation", "restricted"], False),
        ("k8s_network_policy_egr_227", "Egress Policy Blocking", "Egress network policy blocking", "network", Severity.MEDIUM, ["NetworkPolicy", "egress", "blocked"], False),
        ("k8s_network_policy_ing_228", "Ingress Policy Blocking", "Ingress network policy blocking", "network", Severity.MEDIUM, ["NetworkPolicy", "ingress", "blocked"], False),
        ("k8s_cilium_policy_229", "Cilium Policy Error", "Cilium network policy issue", "cni", Severity.HIGH, ["Cilium", "CiliumNetworkPolicy"], False),
        ("k8s_multus_cni_230", "Multus CNI Error", "Multus multi-network CNI error", "cni", Severity.HIGH, ["Multus", "NetworkAttachmentDefinition"], False),
    ]
    
    for pid, name, desc, subcat, sev, signals, auto_safe in k8s_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.KUBERNETES, subcategory=subcat, severity=sev,
            symptoms=[Symptom("event", signals[0], "contains", True, 3.0)],
            signals=signals, root_causes=["configuration", "resource_limits", "dependency"],
            recommended_actions=[
                RecommendedAction("investigate", "kubernetes", 95, {}, False, 30),
                RecommendedAction("remediate", "kubernetes", 80, {}, auto_safe, 60),
            ],
            autonomous_safe=auto_safe, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=[subcat]
        ))
    
    return patterns
