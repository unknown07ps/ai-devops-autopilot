"""
Additional Cloud and Infrastructure Patterns - 100 more patterns
Covers AWS, GCP, Azure, and general cloud infrastructure
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_cloud_patterns_batch2() -> List[IncidentPattern]:
    """100 additional cloud patterns"""
    patterns = []
    
    cloud_scenarios = [
        # AWS EC2/Compute (331-360)
        ("aws_ec2_impaired_331", "EC2 Instance Impaired", "EC2 hardware status check failed", "ec2", Severity.CRITICAL),
        ("aws_ec2_scheduled_332", "EC2 Scheduled Event", "EC2 maintenance scheduled", "ec2", Severity.MEDIUM),
        ("aws_ec2_spot_term_333", "EC2 Spot Termination", "Spot instance termination notice", "ec2", Severity.HIGH),
        ("aws_ec2_capacity_334", "EC2 Insufficient Capacity", "Instance type not available", "ec2", Severity.HIGH),
        ("aws_ec2_credit_335", "EC2 CPU Credits Exhausted", "T-series CPU credits depleted", "ec2", Severity.MEDIUM),
        ("aws_ec2_ebs_detach_336", "EC2 EBS Detachment", "EBS volume forcefully detached", "ebs", Severity.HIGH),
        ("aws_ec2_network_337", "EC2 Network Performance", "Network bandwidth limit reached", "ec2", Severity.MEDIUM),
        ("aws_ec2_eni_limit_338", "EC2 ENI Limit", "ENI attachment limit reached", "ec2", Severity.MEDIUM),
        ("aws_ebs_iops_339", "EBS IOPS Limit", "EBS IOPS limit reached", "ebs", Severity.HIGH),
        ("aws_ebs_throughput_340", "EBS Throughput Limit", "EBS throughput exceeded", "ebs", Severity.HIGH),
        ("aws_ebs_snapshot_341", "EBS Snapshot Failed", "EBS snapshot creation failed", "ebs", Severity.MEDIUM),
        ("aws_ebs_stuck_342", "EBS Volume Stuck", "EBS volume stuck in state", "ebs", Severity.HIGH),
        # AWS RDS (343-355)
        ("aws_rds_cpu_343", "RDS CPU High", "RDS CPU utilization critical", "rds", Severity.HIGH),
        ("aws_rds_memory_344", "RDS Memory Pressure", "RDS freeable memory low", "rds", Severity.HIGH),
        ("aws_rds_iops_345", "RDS IOPS Throttled", "RDS IOPS being throttled", "rds", Severity.HIGH),
        ("aws_rds_connections_346", "RDS Max Connections", "RDS connection limit reached", "rds", Severity.CRITICAL),
        ("aws_rds_replication_347", "RDS Replication Lag", "RDS read replica lag high", "rds", Severity.HIGH),
        ("aws_rds_failover_348", "RDS Failover Event", "RDS Multi-AZ failover occurred", "rds", Severity.HIGH),
        ("aws_rds_maintenance_349", "RDS Maintenance Window", "RDS maintenance scheduled", "rds", Severity.MEDIUM),
        ("aws_rds_backup_350", "RDS Backup Failed", "RDS automated backup failed", "rds", Severity.HIGH),
        ("aws_rds_parameter_351", "RDS Parameter Change", "RDS parameter group change pending", "rds", Severity.LOW),
        ("aws_rds_storage_352", "RDS Storage Full", "RDS storage space exhausted", "rds", Severity.CRITICAL),
        ("aws_rds_certificate_353", "RDS SSL Certificate", "RDS SSL certificate expiring", "rds", Severity.HIGH),
        ("aws_rds_proxy_354", "RDS Proxy Connection", "RDS Proxy connection failed", "rds", Severity.HIGH),
        ("aws_rds_aurora_355", "Aurora Failover", "Aurora failover triggered", "rds", Severity.HIGH),
        # AWS Lambda (356-365)
        ("aws_lambda_cold_356", "Lambda Cold Start", "Lambda cold start latency high", "lambda", Severity.MEDIUM),
        ("aws_lambda_memory_357", "Lambda Memory Exceeded", "Lambda out of memory", "lambda", Severity.HIGH),
        ("aws_lambda_concurrent_358", "Lambda Concurrency Limit", "Lambda concurrent execution limit", "lambda", Severity.HIGH),
        ("aws_lambda_duration_359", "Lambda Timeout", "Lambda function timed out", "lambda", Severity.HIGH),
        ("aws_lambda_provisioned_360", "Lambda Provisioned Concurrency", "Provisioned concurrency spillover", "lambda", Severity.MEDIUM),
        ("aws_lambda_dlq_361", "Lambda DLQ Messages", "Lambda DLQ receiving messages", "lambda", Severity.MEDIUM),
        ("aws_lambda_layer_362", "Lambda Layer Error", "Lambda layer loading failed", "lambda", Severity.HIGH),
        ("aws_lambda_vpc_363", "Lambda VPC Configuration", "Lambda ENI creation failed", "lambda", Severity.HIGH),
        ("aws_lambda_iam_364", "Lambda IAM Error", "Lambda execution role denied", "lambda", Severity.HIGH),
        ("aws_lambda_dest_365", "Lambda Destination Failed", "Lambda destination delivery failed", "lambda", Severity.MEDIUM),
        # AWS Networking (366-380)
        ("aws_vpc_nat_366", "VPC NAT Gateway Error", "NAT Gateway error response", "vpc", Severity.HIGH),
        ("aws_vpc_flow_367", "VPC Flow Log Issue", "VPC flow logs delivery failed", "vpc", Severity.MEDIUM),
        ("aws_vpc_quota_368", "VPC Quota Exceeded", "VPC resource quota exceeded", "vpc", Severity.HIGH),
        ("aws_elb_unhealthy_369", "ELB Unhealthy Targets", "ELB targets unhealthy", "elb", Severity.HIGH),
        ("aws_elb_5xx_370", "ELB 5xx Errors", "ELB returning 5xx errors", "elb", Severity.HIGH),
        ("aws_elb_latency_371", "ELB High Latency", "ELB target response latency high", "elb", Severity.MEDIUM),
        ("aws_alb_rules_372", "ALB Rule Limit", "ALB rule limit reached", "elb", Severity.MEDIUM),
        ("aws_nlb_target_373", "NLB Target Deregistration", "NLB target deregistration delay", "elb", Severity.MEDIUM),
        ("aws_cf_error_374", "CloudFront Error Rate", "CloudFront error rate high", "cloudfront", Severity.HIGH),
        ("aws_cf_origin_375", "CloudFront Origin Error", "CloudFront origin connection failed", "cloudfront", Severity.HIGH),
        ("aws_r53_health_376", "Route53 Health Check", "Route53 health check failing", "route53", Severity.CRITICAL),
        ("aws_r53_latency_377", "Route53 Latency", "Route53 DNS resolution slow", "route53", Severity.MEDIUM),
        ("aws_api_gw_378", "API Gateway Error", "API Gateway returning errors", "apigateway", Severity.HIGH),
        ("aws_api_throttle_379", "API Gateway Throttle", "API Gateway request throttled", "apigateway", Severity.MEDIUM),
        ("aws_api_quota_380", "API Gateway Quota", "API Gateway quota exceeded", "apigateway", Severity.HIGH),
        # AWS Containers (381-395)
        ("aws_ecs_task_381", "ECS Task Failed", "ECS task stopped unexpectedly", "ecs", Severity.HIGH),
        ("aws_ecs_service_382", "ECS Service Unstable", "ECS service deployment unstable", "ecs", Severity.HIGH),
        ("aws_ecs_capacity_383", "ECS Capacity Provider", "ECS capacity provider issue", "ecs", Severity.HIGH),
        ("aws_ecs_container_384", "ECS Container Instance", "ECS container instance unhealthy", "ecs", Severity.HIGH),
        ("aws_ecr_pull_385", "ECR Pull Error", "ECR image pull failed", "ecr", Severity.HIGH),
        ("aws_ecr_scan_386", "ECR Vulnerability", "ECR scan found vulnerabilities", "ecr", Severity.MEDIUM),
        ("aws_eks_addon_387", "EKS Addon Degraded", "EKS addon in degraded state", "eks", Severity.MEDIUM),
        ("aws_eks_control_388", "EKS Control Plane", "EKS control plane issue", "eks", Severity.CRITICAL),
        ("aws_eks_node_389", "EKS Node Group", "EKS node group scaling failed", "eks", Severity.HIGH),
        ("aws_eks_fargate_390", "EKS Fargate Profile", "EKS Fargate pod scheduling failed", "eks", Severity.HIGH),
        ("aws_fargate_cpu_391", "Fargate CPU Limit", "Fargate task CPU throttled", "fargate", Severity.MEDIUM),
        ("aws_fargate_memory_392", "Fargate Memory Limit", "Fargate task memory exceeded", "fargate", Severity.HIGH),
        ("aws_fargate_eni_393", "Fargate ENI Limit", "Fargate ENI allocation failed", "fargate", Severity.HIGH),
        ("aws_app_runner_394", "App Runner Failed", "App Runner service failed", "apprunner", Severity.HIGH),
        ("aws_batch_job_395", "Batch Job Failed", "AWS Batch job failed", "batch", Severity.MEDIUM),
        # AWS Storage/Data (396-410)
        ("aws_s3_access_396", "S3 Access Denied", "S3 bucket access denied", "s3", Severity.HIGH),
        ("aws_s3_throttle_397", "S3 Request Throttling", "S3 requests being throttled", "s3", Severity.MEDIUM),
        ("aws_s3_replication_398", "S3 Replication Failed", "S3 cross-region replication failed", "s3", Severity.HIGH),
        ("aws_dynamodb_throttle_399", "DynamoDB Throttling", "DynamoDB read/write throttled", "dynamodb", Severity.HIGH),
        ("aws_dynamodb_capacity_400", "DynamoDB Capacity", "DynamoDB capacity exceeded", "dynamodb", Severity.HIGH),
        ("aws_dynamodb_gsi_401", "DynamoDB GSI Throttle", "DynamoDB GSI being throttled", "dynamodb", Severity.MEDIUM),
        ("aws_elasticache_cpu_402", "ElastiCache CPU", "ElastiCache CPU high", "elasticache", Severity.HIGH),
        ("aws_elasticache_mem_403", "ElastiCache Memory", "ElastiCache memory pressure", "elasticache", Severity.HIGH),
        ("aws_elasticache_evict_404", "ElastiCache Evictions", "ElastiCache evicting keys", "elasticache", Severity.MEDIUM),
        ("aws_sqs_dlq_405", "SQS Dead Letter Queue", "SQS messages going to DLQ", "sqs", Severity.MEDIUM),
        ("aws_sqs_age_406", "SQS Message Age", "SQS oldest message age high", "sqs", Severity.MEDIUM),
        ("aws_sns_delivery_407", "SNS Delivery Failed", "SNS message delivery failed", "sns", Severity.HIGH),
        ("aws_kinesis_throttle_408", "Kinesis Throttling", "Kinesis stream throttled", "kinesis", Severity.HIGH),
        ("aws_kinesis_iterator_409", "Kinesis Iterator Age", "Kinesis iterator age high", "kinesis", Severity.MEDIUM),
        ("aws_msk_broker_410", "MSK Broker Issues", "MSK broker unhealthy", "msk", Severity.HIGH),
        # GCP (411-420)
        ("gcp_gce_preempt_411", "GCE Preemption", "GCE preemptible VM terminated", "gce", Severity.HIGH),
        ("gcp_gce_quota_412", "GCE Quota Exceeded", "GCE quota limit reached", "gce", Severity.HIGH),
        ("gcp_gke_control_413", "GKE Control Plane", "GKE control plane unavailable", "gke", Severity.CRITICAL),
        ("gcp_gke_node_414", "GKE Node Pool", "GKE node pool issue", "gke", Severity.HIGH),
        ("gcp_cloud_sql_415", "Cloud SQL Error", "Cloud SQL instance error", "cloudsql", Severity.HIGH),
        ("gcp_cloud_run_416", "Cloud Run Cold Start", "Cloud Run cold start latency", "cloudrun", Severity.MEDIUM),
        ("gcp_pubsub_417", "Pub/Sub Backlog", "Pub/Sub subscription backlog high", "pubsub", Severity.MEDIUM),
        ("gcp_gcs_access_418", "GCS Access Denied", "GCS bucket access denied", "gcs", Severity.HIGH),
        ("gcp_lb_health_419", "GCP LB Health Check", "GCP load balancer backend unhealthy", "lb", Severity.HIGH),
        ("gcp_vpc_peering_420", "GCP VPC Peering", "VPC peering connection issue", "vpc", Severity.HIGH),
        # Azure (421-430)
        ("azure_vm_impaired_421", "Azure VM Impaired", "Azure VM health degraded", "vm", Severity.HIGH),
        ("azure_aks_node_422", "AKS Node Issue", "AKS node pool problem", "aks", Severity.HIGH),
        ("azure_sql_dtl_423", "Azure SQL DTU", "Azure SQL DTU limit reached", "sql", Severity.HIGH),
        ("azure_cosmos_ru_424", "Cosmos DB RU Exceeded", "Cosmos DB request units exceeded", "cosmosdb", Severity.HIGH),
        ("azure_storage_throttle_425", "Azure Storage Throttle", "Azure storage being throttled", "storage", Severity.MEDIUM),
        ("azure_fn_timeout_426", "Azure Function Timeout", "Azure Function timed out", "functions", Severity.HIGH),
        ("azure_lb_probe_427", "Azure LB Probe Failed", "Azure load balancer probe failed", "lb", Severity.HIGH),
        ("azure_appgw_5xx_428", "Azure App Gateway 5xx", "App Gateway returning 5xx", "appgw", Severity.HIGH),
        ("azure_redis_cpu_429", "Azure Redis CPU", "Azure Redis CPU critical", "redis", Severity.HIGH),
        ("azure_eventhub_430", "Azure Event Hub Error", "Event Hub ingestion error", "eventhub", Severity.HIGH),
    ]
    
    for pid, name, desc, subcat, sev in cloud_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.CLOUD, subcategory=subcat, severity=sev,
            symptoms=[Symptom("metric", f"{subcat}_status", "equals", "error", 3.0)],
            signals=[subcat, "cloud", desc.split()[0].lower()],
            root_causes=["configuration", "capacity", "quota"],
            recommended_actions=[
                RecommendedAction("check_cloud_status", "cloud", 95, {}, False, 30),
                RecommendedAction("scale_or_remediate", "cloud", 80, {}, False, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=["cloud", subcat]
        ))
    
    return patterns
