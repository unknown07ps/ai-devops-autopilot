"""
Additional Application, CI/CD, Network, Security Patterns - 120 more patterns
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_application_patterns_batch2() -> List[IncidentPattern]:
    """40 additional application patterns"""
    patterns = []
    
    app_scenarios = [
        # JVM/Java (431-450)
        ("app_jvm_oom_heap_431", "JVM Heap OOM", "Java heap OutOfMemoryError", "jvm", Severity.CRITICAL, ["OutOfMemoryError", "Heap space"]),
        ("app_jvm_oom_meta_432", "JVM Metaspace OOM", "Metaspace OutOfMemoryError", "jvm", Severity.CRITICAL, ["OutOfMemoryError", "Metaspace"]),
        ("app_jvm_oom_gc_433", "JVM GC Overhead Limit", "GC overhead limit exceeded", "jvm", Severity.CRITICAL, ["GC overhead limit exceeded"]),
        ("app_jvm_thread_oom_434", "JVM Thread OOM", "Unable to create new native thread", "jvm", Severity.CRITICAL, ["unable to create", "native thread"]),
        ("app_jvm_gc_pause_435", "JVM Long GC Pause", "GC pause exceeding threshold", "jvm", Severity.HIGH, ["GC pause", "stop-the-world"]),
        ("app_jvm_classload_436", "JVM Class Loading", "ClassNotFoundException", "jvm", Severity.HIGH, ["ClassNotFoundException", "NoClassDefFoundError"]),
        ("app_jvm_native_437", "JVM Native Memory", "Native memory exhausted", "jvm", Severity.CRITICAL, ["native memory", "allocation"]),
        ("app_jvm_stack_438", "JVM StackOverflow", "StackOverflowError", "jvm", Severity.HIGH, ["StackOverflowError"]),
        ("app_jvm_deadlock_439", "JVM Thread Deadlock", "Thread deadlock detected", "jvm", Severity.CRITICAL, ["deadlock", "BLOCKED"]),
        ("app_jvm_cpu_spin_440", "JVM CPU Spinning", "Thread spinning consuming CPU", "jvm", Severity.HIGH, ["CPU", "spinning", "RUNNABLE"]),
        # Node.js (441-450)
        ("app_node_event_loop_441", "Node Event Loop Blocked", "Event loop delay high", "nodejs", Severity.HIGH, ["event loop", "blocked"]),
        ("app_node_heap_442", "Node Heap Limit", "JavaScript heap out of memory", "nodejs", Severity.CRITICAL, ["heap out of memory"]),
        ("app_node_unhandled_443", "Node Unhandled Rejection", "Unhandled promise rejection", "nodejs", Severity.MEDIUM, ["unhandled", "rejection"]),
        ("app_node_cluster_444", "Node Cluster Worker", "Cluster worker died", "nodejs", Severity.HIGH, ["worker", "died", "exited"]),
        ("app_node_module_445", "Node Module Error", "Module not found Error", "nodejs", Severity.HIGH, ["MODULE_NOT_FOUND"]),
        ("app_python_import_446", "Python Import Error", "ImportError or ModuleNotFoundError", "python", Severity.HIGH, ["ImportError", "ModuleNotFoundError"]),
        ("app_python_memory_447", "Python Memory Leak", "Python process memory growing", "python", Severity.HIGH, ["memory", "leak"]),
        ("app_python_async_448", "Python Async Error", "Asyncio task exception", "python", Severity.MEDIUM, ["asyncio", "exception"]),
        ("app_go_goroutine_449", "Go Goroutine Leak", "Goroutine count growing", "golang", Severity.HIGH, ["goroutine", "leak"]),
        ("app_go_panic_450", "Go Panic", "Runtime panic occurred", "golang", Severity.CRITICAL, ["panic", "runtime error"]),
        # HTTP/API (451-460)
        ("app_api_timeout_451", "API Request Timeout", "API requests timing out", "api", Severity.HIGH, ["timeout", "deadline exceeded"]),
        ("app_api_rate_limit_452", "API Rate Limited", "Rate limit exceeded", "api", Severity.MEDIUM, ["rate limit", "429"]),
        ("app_api_circuit_453", "API Circuit Open", "Circuit breaker open", "api", Severity.MEDIUM, ["circuit", "open"]),
        ("app_api_retry_454", "API Retry Exhausted", "Retry attempts exhausted", "api", Severity.HIGH, ["retry", "exhausted"]),
        ("app_api_auth_455", "API Auth Failure", "Authentication failed", "api", Severity.HIGH, ["401", "unauthorized"]),
        ("app_api_permission_456", "API Permission Denied", "Authorization failed", "api", Severity.MEDIUM, ["403", "forbidden"]),
        ("app_api_validation_457", "API Validation Error", "Request validation failed", "api", Severity.LOW, ["400", "validation"]),
        ("app_api_dependency_458", "API Dependency Down", "Downstream service unavailable", "api", Severity.HIGH, ["dependency", "unavailable"]),
        ("app_api_version_459", "API Version Mismatch", "API version incompatible", "api", Severity.MEDIUM, ["version", "deprecated"]),
        ("app_api_serialization_460", "API Serialization Error", "JSON/XML serialization failed", "api", Severity.MEDIUM, ["serialization", "parse error"]),
        # Messaging/Queue (461-470)
        ("app_queue_backpressure_461", "Queue Backpressure", "Message queue backing up", "queue", Severity.HIGH, ["backpressure", "queue full"]),
        ("app_queue_poison_462", "Queue Poison Message", "Message processing failing repeatedly", "queue", Severity.MEDIUM, ["poison", "redelivery"]),
        ("app_queue_consumer_463", "Queue Consumer Lag", "Consumer falling behind", "queue", Severity.MEDIUM, ["consumer lag", "offset"]),
        ("app_queue_producer_464", "Queue Producer Error", "Producer unable to send", "queue", Severity.HIGH, ["producer", "send failed"]),
        ("app_kafka_partition_465", "Kafka Partition Lag", "Kafka partition lag growing", "kafka", Severity.MEDIUM, ["partition", "lag"]),
        ("app_kafka_rebalance_466", "Kafka Consumer Rebalance", "Frequent consumer rebalances", "kafka", Severity.MEDIUM, ["rebalance", "revoked"]),
        ("app_rabbitmq_queue_467", "RabbitMQ Queue Full", "Queue length exceeded", "rabbitmq", Severity.HIGH, ["queue", "length"]),
        ("app_rabbitmq_conn_468", "RabbitMQ Connection", "Connection to broker failed", "rabbitmq", Severity.HIGH, ["connection", "refused"]),
        ("app_cache_miss_469", "Cache Miss Rate High", "Cache hit ratio dropping", "cache", Severity.MEDIUM, ["cache miss", "hit ratio"]),
        ("app_cache_eviction_470", "Cache Eviction Rate", "Cache evicting too frequently", "cache", Severity.MEDIUM, ["eviction", "memory"]),
    ]
    
    for pid, name, desc, subcat, sev, signals in app_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.APPLICATION, subcategory=subcat, severity=sev,
            symptoms=[Symptom("log", signals[0], "contains", True, 3.0)],
            signals=signals, root_causes=["code", "configuration", "resources"],
            recommended_actions=[
                RecommendedAction("analyze_logs", "application", 95, {}, False, 30),
                RecommendedAction("restart_service", "application", 75, {}, True, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=[subcat]
        ))
    return patterns


def get_cicd_patterns_batch2() -> List[IncidentPattern]:
    """40 additional CI/CD patterns"""
    patterns = []
    
    cicd_scenarios = [
        # Build failures (471-490)
        ("cicd_npm_build_471", "NPM Build Failed", "npm install or build failed", "npm", Severity.MEDIUM),
        ("cicd_yarn_install_472", "Yarn Install Failed", "Yarn dependency installation failed", "yarn", Severity.MEDIUM),
        ("cicd_maven_build_473", "Maven Build Failed", "Maven build or test failed", "maven", Severity.MEDIUM),
        ("cicd_gradle_build_474", "Gradle Build Failed", "Gradle compilation failed", "gradle", Severity.MEDIUM),
        ("cicd_go_build_475", "Go Build Failed", "Go module build failed", "golang", Severity.MEDIUM),
        ("cicd_python_pip_476", "Python Pip Failed", "Pip install failed", "pip", Severity.MEDIUM),
        ("cicd_docker_build_477", "Docker Build Error", "Dockerfile build failed", "docker", Severity.HIGH),
        ("cicd_docker_push_478", "Docker Push Failed", "Docker push to registry failed", "docker", Severity.HIGH),
        ("cicd_docker_manifest_479", "Docker Manifest Error", "Multi-arch manifest issue", "docker", Severity.MEDIUM),
        ("cicd_buildah_480", "Buildah Build Failed", "Buildah container build failed", "buildah", Severity.HIGH),
        # Testing (481-500)
        ("cicd_unit_test_481", "Unit Tests Failed", "Unit test suite failed", "testing", Severity.MEDIUM),
        ("cicd_integ_test_482", "Integration Tests Failed", "Integration tests failed", "testing", Severity.HIGH),
        ("cicd_e2e_test_483", "E2E Tests Failed", "End-to-end tests failed", "testing", Severity.HIGH),
        ("cicd_test_timeout_484", "Test Timeout", "Test execution timed out", "testing", Severity.MEDIUM),
        ("cicd_test_flaky_485", "Flaky Test Detected", "Test failing intermittently", "testing", Severity.LOW),
        ("cicd_coverage_486", "Code Coverage Below", "Code coverage below threshold", "testing", Severity.LOW),
        ("cicd_lint_487", "Linting Failed", "Code linting errors", "quality", Severity.LOW),
        ("cicd_security_scan_488", "Security Scan Failed", "SAST/DAST vulnerabilities found", "security", Severity.HIGH),
        ("cicd_sonar_489", "SonarQube Quality Gate", "Quality gate failed", "quality", Severity.MEDIUM),
        ("cicd_license_490", "License Check Failed", "Dependency license violation", "compliance", Severity.MEDIUM),
        # Deployment (491-510)
        ("cicd_helm_release_491", "Helm Release Failed", "Helm upgrade/install failed", "helm", Severity.HIGH),
        ("cicd_helm_validation_492", "Helm Validation Error", "Helm template validation failed", "helm", Severity.MEDIUM),
        ("cicd_kustomize_493", "Kustomize Build Failed", "Kustomize overlay failed", "kustomize", Severity.MEDIUM),
        ("cicd_terraform_plan_494", "Terraform Plan Failed", "Terraform plan errors", "terraform", Severity.HIGH),
        ("cicd_terraform_apply_495", "Terraform Apply Failed", "Terraform apply failed", "terraform", Severity.CRITICAL),
        ("cicd_terraform_state_496", "Terraform State Lock", "State file locked", "terraform", Severity.HIGH),
        ("cicd_ansible_497", "Ansible Playbook Failed", "Ansible execution failed", "ansible", Severity.HIGH),
        ("cicd_pulumi_498", "Pulumi Update Failed", "Pulumi stack update failed", "pulumi", Severity.HIGH),
        ("cicd_argocd_sync_499", "ArgoCD Sync Failed", "ArgoCD sync error", "argocd", Severity.HIGH),
        ("cicd_flux_reconcile_500", "Flux Reconcile Failed", "Flux GitOps reconciliation failed", "flux", Severity.HIGH),
        ("cicd_spinnaker_501", "Spinnaker Pipeline Failed", "Spinnaker deployment failed", "spinnaker", Severity.HIGH),
        ("cicd_jenkins_502", "Jenkins Job Failed", "Jenkins pipeline failed", "jenkins", Severity.MEDIUM),
        ("cicd_gitlab_503", "GitLab CI Failed", "GitLab CI job failed", "gitlab", Severity.MEDIUM),
        ("cicd_github_504", "GitHub Actions Failed", "GitHub workflow failed", "github", Severity.MEDIUM),
        ("cicd_circle_505", "CircleCI Failed", "CircleCI job failed", "circleci", Severity.MEDIUM),
        ("cicd_artifact_506", "Artifact Upload Failed", "Build artifact upload failed", "artifact", Severity.MEDIUM),
        ("cicd_artifact_download_507", "Artifact Download Failed", "Build artifact not found", "artifact", Severity.MEDIUM),
        ("cicd_cache_508", "CI Cache Error", "Build cache corrupted", "caching", Severity.LOW),
        ("cicd_runner_509", "CI Runner Offline", "CI runner unavailable", "runner", Severity.HIGH),
        ("cicd_secret_510", "CI Secret Error", "CI/CD secret not found", "secrets", Severity.HIGH),
    ]
    
    for pid, name, desc, subcat, sev in cicd_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.CICD, subcategory=subcat, severity=sev,
            symptoms=[Symptom("event", "failed", "contains", True, 3.0)],
            signals=[subcat, "failed", "error"],
            root_causes=["configuration", "dependency", "permission"],
            recommended_actions=[
                RecommendedAction("check_logs", "cicd", 95, {}, False, 30),
                RecommendedAction("retry", "cicd", 75, {}, True, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.LOW,
            resolution_time_avg_seconds=180, tags=["cicd", subcat]
        ))
    return patterns


def get_network_patterns_batch2() -> List[IncidentPattern]:
    """20 additional network patterns"""
    patterns = []
    
    net_scenarios = [
        ("net_mtls_handshake_511", "mTLS Handshake Failed", "Mutual TLS verification failed", "tls", Severity.HIGH),
        ("net_cert_chain_512", "Certificate Chain Invalid", "SSL certificate chain broken", "tls", Severity.HIGH),
        ("net_sni_mismatch_513", "SNI Mismatch", "Server name indication mismatch", "tls", Severity.MEDIUM),
        ("net_ocsp_stapling_514", "OCSP Stapling Error", "OCSP stapling validation failed", "tls", Severity.MEDIUM),
        ("net_tcp_rst_515", "TCP Connection Reset", "TCP RST packets increasing", "tcp", Severity.HIGH),
        ("net_tcp_syn_flood_516", "TCP SYN Flood", "SYN flood detected", "tcp", Severity.CRITICAL),
        ("net_tcp_backlog_517", "TCP Backlog Full", "TCP listen backlog full", "tcp", Severity.HIGH),
        ("net_udp_buffer_518", "UDP Buffer Overflow", "UDP receive buffer overflow", "udp", Severity.HIGH),
        ("net_icmp_blocked_519", "ICMP Blocked", "ICMP responses blocked", "network", Severity.LOW),
        ("net_mtu_issue_520", "MTU Path Discovery", "Path MTU discovery issue", "network", Severity.MEDIUM),
        ("net_arp_storm_521", "ARP Storm", "ARP broadcast storm detected", "network", Severity.HIGH),
        ("net_bgp_flap_522", "BGP Route Flapping", "BGP routes unstable", "routing", Severity.CRITICAL),
        ("net_ospf_neighbor_523", "OSPF Neighbor Down", "OSPF adjacency lost", "routing", Severity.HIGH),
        ("net_vxlan_524", "VXLAN Tunnel Error", "VXLAN encapsulation issue", "overlay", Severity.HIGH),
        ("net_geneve_525", "Geneve Tunnel Error", "Geneve tunnel failure", "overlay", Severity.HIGH),
        ("net_wireguard_526", "WireGuard Tunnel Down", "WireGuard VPN tunnel down", "vpn", Severity.HIGH),
        ("net_ipsec_527", "IPSec Tunnel Error", "IPSec SA negotiation failed", "vpn", Severity.HIGH),
        ("net_sdn_controller_528", "SDN Controller Error", "SDN controller unreachable", "sdn", Severity.CRITICAL),
        ("net_service_mesh_529", "Service Mesh Error", "Service mesh sidecar error", "mesh", Severity.HIGH),
        ("net_grpc_deadline_530", "gRPC Deadline Exceeded", "gRPC call deadline exceeded", "grpc", Severity.HIGH),
    ]
    
    for pid, name, desc, subcat, sev in net_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.NETWORK, subcategory=subcat, severity=sev,
            symptoms=[Symptom("log", subcat, "contains", True, 3.0)],
            signals=[subcat, "network", "connection"],
            root_causes=["configuration", "hardware", "capacity"],
            recommended_actions=[
                RecommendedAction("check_connectivity", "network", 95, {}, False, 30),
                RecommendedAction("restart_service", "network", 75, {}, True, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=180, tags=["network", subcat]
        ))
    return patterns


def get_security_patterns_batch2() -> List[IncidentPattern]:
    """20 additional security patterns"""
    patterns = []
    
    sec_scenarios = [
        ("sec_credential_leak_531", "Credential Leak", "Credentials exposed in logs/code", "credentials", Severity.CRITICAL),
        ("sec_api_key_exposed_532", "API Key Exposed", "API key found in public repo", "credentials", Severity.CRITICAL),
        ("sec_jwt_expired_533", "JWT Token Expired", "JWT validation failed - expired", "auth", Severity.MEDIUM),
        ("sec_jwt_invalid_534", "JWT Token Invalid", "JWT signature verification failed", "auth", Severity.HIGH),
        ("sec_oauth_error_535", "OAuth Flow Error", "OAuth authentication failed", "auth", Severity.HIGH),
        ("sec_saml_error_536", "SAML Assertion Error", "SAML authentication failed", "auth", Severity.HIGH),
        ("sec_cors_violation_537", "CORS Violation", "Cross-origin request blocked", "web", Severity.MEDIUM),
        ("sec_csrf_detected_538", "CSRF Attack Detected", "CSRF token validation failed", "web", Severity.HIGH),
        ("sec_ssrf_attempt_539", "SSRF Attempt", "Server-side request forgery blocked", "web", Severity.CRITICAL),
        ("sec_xxe_detected_540", "XXE Attack Detected", "XML external entity blocked", "web", Severity.CRITICAL),
        ("sec_rce_attempt_541", "RCE Attempt", "Remote code execution blocked", "attack", Severity.CRITICAL),
        ("sec_lfi_detected_542", "LFI Detected", "Local file inclusion blocked", "attack", Severity.HIGH),
        ("sec_directory_traversal_543", "Directory Traversal", "Path traversal attack blocked", "attack", Severity.HIGH),
        ("sec_command_injection_544", "Command Injection", "OS command injection blocked", "attack", Severity.CRITICAL),
        ("sec_privilege_escalation_545", "Privilege Escalation", "Privilege escalation attempt", "access", Severity.CRITICAL),
        ("sec_data_exfil_546", "Data Exfiltration", "Unusual data transfer detected", "data", Severity.CRITICAL),
        ("sec_crypto_mining_547", "Crypto Mining Detected", "Cryptocurrency mining detected", "malware", Severity.HIGH),
        ("sec_malware_detected_548", "Malware Detected", "Malware signature matched", "malware", Severity.CRITICAL),
        ("sec_rootkit_549", "Rootkit Detected", "Rootkit behavior detected", "malware", Severity.CRITICAL),
        ("sec_compliance_550", "Compliance Violation", "Security compliance violation", "compliance", Severity.HIGH),
    ]
    
    for pid, name, desc, subcat, sev in sec_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.SECURITY, subcategory=subcat, severity=sev,
            symptoms=[Symptom("log", subcat, "contains", True, 3.0)],
            signals=[subcat, "security", "attack"],
            root_causes=["attack", "vulnerability", "misconfiguration"],
            recommended_actions=[
                RecommendedAction("investigate", "security", 95, {}, False, 30),
                RecommendedAction("block_source", "security", 85, {}, True, 15),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.CRITICAL,
            resolution_time_avg_seconds=180, tags=["security", subcat]
        ))
    return patterns


def get_all_batch3_patterns() -> List[IncidentPattern]:
    """Get all batch 3 patterns"""
    all_patterns = []
    all_patterns.extend(get_application_patterns_batch2())
    all_patterns.extend(get_cicd_patterns_batch2())
    all_patterns.extend(get_network_patterns_batch2())
    all_patterns.extend(get_security_patterns_batch2())
    return all_patterns
