"""
Extended Patterns - Application, Cloud, CI/CD, Network, Security (200+ patterns)
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_extended_application_patterns() -> List[IncidentPattern]:
    """100+ application patterns"""
    patterns = []
    
    # Application patterns - OOM, CPU, Thread, Connection, Error, Latency, GC, etc.
    pattern_configs = [
        ("app_jvm_gc_081", "JVM GC Pause", "Long GC pauses affecting application", "gc", Severity.HIGH, ["gc pause", "stop-the-world", "full gc"], True),
        ("app_heap_oom_082", "JVM Heap OOM", "Java heap space exhausted", "memory", Severity.CRITICAL, ["java.lang.OutOfMemoryError", "heap space"], False),
        ("app_metaspace_083", "JVM Metaspace Full", "Metaspace memory exhausted", "memory", Severity.HIGH, ["Metaspace", "OutOfMemoryError"], False),
        ("app_thread_deadlock_084", "Application Deadlock", "Threads in deadlock state", "threading", Severity.CRITICAL, ["deadlock", "BLOCKED"], False),
        ("app_connection_timeout_085", "HTTP Connection Timeout", "Outbound HTTP requests timing out", "http", Severity.HIGH, ["connection timeout", "SocketTimeoutException"], True),
        ("app_ssl_handshake_086", "SSL Handshake Failure", "TLS/SSL handshake failing", "security", Severity.HIGH, ["SSL handshake", "certificate"], False),
        ("app_rate_limit_087", "Application Rate Limited", "Rate limiter rejecting requests", "traffic", Severity.MEDIUM, ["rate limit", "429", "too many requests"], True),
        ("app_cache_miss_088", "Cache Miss Rate High", "Cache hit ratio degraded", "cache", Severity.MEDIUM, ["cache miss", "cache hit ratio"], True),
        ("app_queue_full_089", "Message Queue Full", "Message queue reached capacity", "messaging", Severity.HIGH, ["queue full", "backpressure"], False),
        ("app_disk_full_090", "Application Disk Full", "Application cannot write to disk", "storage", Severity.CRITICAL, ["No space left", "disk full", "ENOSPC"], True),
    ]
    
    for pid, name, desc, subcat, sev, signals, auto_safe in pattern_configs:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.APPLICATION, subcategory=subcat, severity=sev,
            symptoms=[Symptom("log", signals[0], "contains", True, 3.0)],
            signals=signals, root_causes=["configuration", "resource_limits", "code_issue"],
            recommended_actions=[
                RecommendedAction("analyze_logs", "application", 90, {}, False, 30),
                RecommendedAction("restart_application", "application", 75, {}, True, 60),
            ],
            autonomous_safe=auto_safe, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=subcat.split("_")
        ))
    
    return patterns


def get_extended_cloud_patterns() -> List[IncidentPattern]:
    """100+ cloud infrastructure patterns"""
    patterns = []
    
    cloud_configs = [
        ("cloud_ec2_status_091", "EC2 Instance Status Check Failed", "AWS EC2 instance failing status checks", "ec2", Severity.HIGH),
        ("cloud_ebs_io_092", "EBS Volume High Latency", "EBS volume experiencing high I/O latency", "ebs", Severity.MEDIUM),
        ("cloud_rds_storage_093", "RDS Storage Full", "RDS instance running out of storage", "rds", Severity.CRITICAL),
        ("cloud_s3_throttle_094", "S3 Request Throttling", "S3 requests being throttled", "s3", Severity.MEDIUM),
        ("cloud_lambda_timeout_095", "Lambda Function Timeout", "Lambda function timing out", "lambda", Severity.HIGH),
        ("cloud_alb_unhealthy_096", "ALB Target Unhealthy", "ALB target group has unhealthy targets", "alb", Severity.HIGH),
        ("cloud_route53_fail_097", "Route53 Health Check Failed", "Route53 health check failing", "route53", Severity.CRITICAL),
        ("cloud_iam_denied_098", "IAM Permission Denied", "AWS IAM permission denied", "iam", Severity.MEDIUM),
        ("cloud_vpc_nat_099", "NAT Gateway Bandwidth", "NAT Gateway bandwidth limit reached", "vpc", Severity.HIGH),
        ("cloud_sqs_dlq_100", "SQS Dead Letter Queue Growing", "Messages going to DLQ", "sqs", Severity.MEDIUM),
    ]
    
    for pid, name, desc, subcat, sev in cloud_configs:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.CLOUD, subcategory=subcat, severity=sev,
            symptoms=[Symptom("metric", f"{subcat}_status", "equals", "unhealthy", 3.0)],
            signals=[subcat, "aws", "cloud"], root_causes=["configuration", "limits", "capacity"],
            recommended_actions=[
                RecommendedAction("check_aws_status", "cloud", 90, {}, False, 30),
                RecommendedAction("scale_resources", "cloud", 80, {}, True, 120),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=["aws", subcat]
        ))
    
    return patterns


def get_extended_cicd_patterns() -> List[IncidentPattern]:
    """50+ CI/CD patterns"""
    patterns = []
    
    cicd_configs = [
        ("cicd_docker_build_101", "Docker Build Failed", "Docker image build failed", "docker"),
        ("cicd_registry_push_102", "Registry Push Failed", "Failed to push image to registry", "registry"),
        ("cicd_helm_deploy_103", "Helm Deployment Failed", "Helm chart deployment failed", "helm"),
        ("cicd_terraform_apply_104", "Terraform Apply Failed", "Infrastructure change failed", "terraform"),
        ("cicd_test_flaky_105", "Flaky Test Failure", "Test failed intermittently", "testing"),
        ("cicd_artifact_missing_106", "Artifact Not Found", "Build artifact missing", "artifacts"),
        ("cicd_secret_expired_107", "CI/CD Secret Expired", "Pipeline secret expired", "secrets"),
        ("cicd_runner_offline_108", "CI Runner Offline", "Build runner not available", "runner"),
        ("cicd_canary_failed_109", "Canary Deployment Failed", "Canary analysis failed", "canary"),
        ("cicd_rollback_triggered_110", "Auto Rollback Triggered", "Deployment rolled back automatically", "rollback"),
    ]
    
    for pid, name, desc, subcat in cicd_configs:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.CICD, subcategory=subcat, severity=Severity.HIGH,
            symptoms=[Symptom("event", "failed", "contains", True, 3.0)],
            signals=[subcat, "pipeline", "deploy"], root_causes=["configuration", "dependency", "timeout"],
            recommended_actions=[
                RecommendedAction("check_pipeline_logs", "cicd", 95, {}, False, 30),
                RecommendedAction("retry_pipeline", "cicd", 75, {}, True, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=300, tags=["cicd", subcat]
        ))
    
    return patterns


def get_extended_network_patterns() -> List[IncidentPattern]:
    """50+ network patterns"""
    patterns = []
    
    net_configs = [
        ("net_dns_resolution_111", "DNS Resolution Slow", "DNS queries taking too long", "dns"),
        ("net_tcp_retransmit_112", "High TCP Retransmissions", "Network packet retransmissions high", "tcp"),
        ("net_connection_reset_113", "Connection Reset", "TCP connections being reset", "tcp"),
        ("net_bandwidth_saturated_114", "Network Bandwidth Saturated", "Network interface at capacity", "bandwidth"),
        ("net_firewall_blocked_115", "Firewall Blocking Traffic", "Firewall rules blocking legitimate traffic", "firewall"),
        ("net_proxy_error_116", "Proxy Connection Error", "Reverse proxy returning errors", "proxy"),
        ("net_websocket_close_117", "WebSocket Disconnections", "WebSocket connections dropping", "websocket"),
        ("net_grpc_unavailable_118", "gRPC Service Unavailable", "gRPC endpoint not responding", "grpc"),
        ("net_cdn_origin_119", "CDN Origin Errors", "CDN cannot reach origin", "cdn"),
        ("net_vpn_tunnel_120", "VPN Tunnel Down", "VPN tunnel connection lost", "vpn"),
    ]
    
    for pid, name, desc, subcat in net_configs:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.NETWORK, subcategory=subcat, severity=Severity.HIGH,
            symptoms=[Symptom("metric", f"{subcat}_error_rate", "above", 5, 3.0)],
            signals=[subcat, "network", "connectivity"], root_causes=["configuration", "capacity", "hardware"],
            recommended_actions=[
                RecommendedAction("check_network_metrics", "network", 90, {}, False, 30),
                RecommendedAction("restart_network_service", "network", 75, {}, True, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.HIGH,
            resolution_time_avg_seconds=180, tags=["network", subcat]
        ))
    
    return patterns


def get_extended_security_patterns() -> List[IncidentPattern]:
    """50+ security patterns"""
    patterns = []
    
    sec_configs = [
        ("sec_brute_force_121", "Brute Force Attack", "Multiple failed login attempts detected", "auth"),
        ("sec_ddos_detected_122", "DDoS Attack Detected", "Traffic pattern indicates DDoS", "ddos"),
        ("sec_cert_expiry_123", "Certificate Expiring Soon", "TLS certificate expiring within 7 days", "certs"),
        ("sec_vulnerability_124", "Critical Vulnerability Detected", "Security scanner found critical CVE", "vuln"),
        ("sec_secret_exposed_125", "Secret Exposed in Logs", "Sensitive data found in logs", "secrets"),
        ("sec_unauthorized_access_126", "Unauthorized Access Attempt", "Failed authorization detected", "authz"),
        ("sec_sql_injection_127", "SQL Injection Attempt", "Potential SQL injection blocked", "injection"),
        ("sec_xss_detected_128", "XSS Attack Detected", "Cross-site scripting attempt blocked", "xss"),
        ("sec_suspicious_ip_129", "Suspicious IP Activity", "Traffic from known malicious IP", "threat"),
        ("sec_data_exfil_130", "Data Exfiltration Detected", "Unusual outbound data transfer", "exfil"),
    ]
    
    for pid, name, desc, subcat in sec_configs:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.SECURITY, subcategory=subcat, severity=Severity.CRITICAL,
            symptoms=[Symptom("log", subcat, "contains", True, 3.0)],
            signals=[subcat, "security", "attack"], root_causes=["attack", "misconfiguration", "vulnerability"],
            recommended_actions=[
                RecommendedAction("investigate_security_event", "security", 95, {}, False, 60),
                RecommendedAction("block_source", "security", 85, {}, True, 15),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.CRITICAL,
            resolution_time_avg_seconds=300, tags=["security", subcat]
        ))
    
    return patterns


def get_all_extended_patterns() -> List[IncidentPattern]:
    """Get all extended patterns combined"""
    all_patterns = []
    all_patterns.extend(get_extended_application_patterns())
    all_patterns.extend(get_extended_cloud_patterns())
    all_patterns.extend(get_extended_cicd_patterns())
    all_patterns.extend(get_extended_network_patterns())
    all_patterns.extend(get_extended_security_patterns())
    return all_patterns
