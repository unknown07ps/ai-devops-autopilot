"""
Production Infrastructure Executor
==================================
Real infrastructure management functions for production-level remediation.
Supports: Kubernetes, AWS, GCP, Azure, Databases, Cache, and more.

IMPORTANT: These functions execute REAL changes in production!
Use with caution and ensure proper IAM/RBAC permissions are configured.
"""

import os
import asyncio
import subprocess
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from abc import ABC, abstractmethod
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("production_executor")


# =============================================================================
# INFRASTRUCTURE CLIENTS
# =============================================================================

class InfrastructureClient(ABC):
    """Base class for infrastructure clients"""
    
    @abstractmethod
    async def execute(self, action: str, params: Dict) -> Dict:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class KubernetesClient(InfrastructureClient):
    """
    Kubernetes cluster operations via kubectl
    Requires: kubectl configured with proper kubeconfig
    """
    
    def __init__(self, kubeconfig: str = None, context: str = None):
        self.kubeconfig = kubeconfig or os.getenv("KUBECONFIG", "~/.kube/config")
        self.context = context or os.getenv("KUBE_CONTEXT")
        self.namespace = os.getenv("KUBE_NAMESPACE", "default")
    
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client", "--short"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _build_cmd(self, args: List[str]) -> List[str]:
        cmd = ["kubectl"]
        if self.context:
            cmd.extend(["--context", self.context])
        cmd.extend(["-n", self.namespace])
        cmd.extend(args)
        return cmd
    
    async def execute(self, action: str, params: Dict) -> Dict:
        """Execute Kubernetes action"""
        
        if action == "rollout_restart":
            return await self.rollout_restart(params["deployment"])
        
        elif action == "scale":
            return await self.scale_deployment(
                params["deployment"], 
                params["replicas"]
            )
        
        elif action == "rollback":
            return await self.rollback_deployment(
                params["deployment"],
                params.get("revision")
            )
        
        elif action == "drain_node":
            return await self.drain_node(params["node"])
        
        elif action == "cordon_node":
            return await self.cordon_node(params["node"])
        
        elif action == "delete_pod":
            return await self.delete_pod(params["pod"])
        
        elif action == "apply_resource_limits":
            return await self.patch_resources(
                params["deployment"],
                params.get("cpu_limit"),
                params.get("memory_limit")
            )
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    async def rollout_restart(self, deployment: str) -> Dict:
        """Rolling restart a deployment"""
        cmd = self._build_cmd(["rollout", "restart", f"deployment/{deployment}"])
        logger.info(f"[K8S] Rollout restart: {deployment}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr,
            "command": " ".join(cmd)
        }
    
    async def scale_deployment(self, deployment: str, replicas: int) -> Dict:
        """Scale deployment replicas"""
        cmd = self._build_cmd(["scale", f"deployment/{deployment}", f"--replicas={replicas}"])
        logger.info(f"[K8S] Scale: {deployment} -> {replicas} replicas")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr,
            "replicas": replicas
        }
    
    async def rollback_deployment(self, deployment: str, revision: int = None) -> Dict:
        """Rollback deployment to previous revision"""
        cmd = self._build_cmd(["rollout", "undo", f"deployment/{deployment}"])
        if revision:
            cmd.append(f"--to-revision={revision}")
        
        logger.info(f"[K8S] Rollback: {deployment}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def drain_node(self, node: str) -> Dict:
        """Drain a node for maintenance"""
        cmd = self._build_cmd([
            "drain", node, 
            "--ignore-daemonsets", 
            "--delete-emptydir-data",
            "--force"
        ])
        
        logger.info(f"[K8S] Drain node: {node}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def cordon_node(self, node: str) -> Dict:
        """Cordon a node (mark unschedulable)"""
        cmd = self._build_cmd(["cordon", node])
        
        logger.info(f"[K8S] Cordon node: {node}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def delete_pod(self, pod: str) -> Dict:
        """Delete a pod (force restart)"""
        cmd = self._build_cmd(["delete", "pod", pod, "--grace-period=30"])
        
        logger.info(f"[K8S] Delete pod: {pod}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def patch_resources(self, deployment: str, cpu_limit: str = None, memory_limit: str = None) -> Dict:
        """Update resource limits for a deployment"""
        patch = {"spec": {"template": {"spec": {"containers": [{"name": deployment, "resources": {"limits": {}}}]}}}}
        
        if cpu_limit:
            patch["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["cpu"] = cpu_limit
        if memory_limit:
            patch["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = memory_limit
        
        cmd = self._build_cmd([
            "patch", f"deployment/{deployment}",
            "--type", "strategic",
            "-p", json.dumps(patch)
        ])
        
        logger.info(f"[K8S] Patch resources: {deployment}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def get_pods(self, label_selector: str = None) -> List[Dict]:
        """Get pods with optional label selector"""
        cmd = self._build_cmd(["get", "pods", "-o", "json"])
        if label_selector:
            cmd.extend(["-l", label_selector])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("items", [])
        return []


class AWSClient(InfrastructureClient):
    """
    AWS operations via AWS CLI/boto3
    Requires: AWS CLI configured or boto3 with proper credentials
    """
    
    def __init__(self, region: str = None, profile: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.profile = profile or os.getenv("AWS_PROFILE")
        self._boto3_available = False
        
        try:
            import boto3
            self.boto3 = boto3
            self._boto3_available = True
            self.ec2 = boto3.client('ec2', region_name=self.region)
            self.ecs = boto3.client('ecs', region_name=self.region)
            self.rds = boto3.client('rds', region_name=self.region)
            self.autoscaling = boto3.client('autoscaling', region_name=self.region)
            self.lambda_client = boto3.client('lambda', region_name=self.region)
        except ImportError:
            logger.warning("boto3 not available, AWS features will be limited")
    
    def is_available(self) -> bool:
        if self._boto3_available:
            try:
                self.ec2.describe_regions(DryRun=False)
                return True
            except Exception:
                pass
        
        # Fallback to CLI
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def execute(self, action: str, params: Dict) -> Dict:
        """Execute AWS action"""
        
        if action == "terminate_instance":
            return await self.terminate_instance(params["instance_id"])
        
        elif action == "restart_instance":
            return await self.restart_instance(params["instance_id"])
        
        elif action == "scale_asg":
            return await self.scale_asg(
                params["asg_name"],
                params["desired_capacity"],
                params.get("min_size"),
                params.get("max_size")
            )
        
        elif action == "force_ecs_deployment":
            return await self.force_ecs_deployment(
                params["cluster"],
                params["service"]
            )
        
        elif action == "rds_failover":
            return await self.rds_failover(params["db_cluster_id"])
        
        elif action == "invoke_lambda":
            return await self.invoke_lambda(
                params["function_name"],
                params.get("payload", {})
            )
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    async def terminate_instance(self, instance_id: str) -> Dict:
        """Terminate an unhealthy EC2 instance"""
        logger.info(f"[AWS] Terminate instance: {instance_id}")
        
        if self._boto3_available:
            try:
                self.ec2.terminate_instances(InstanceIds=[instance_id])
                return {"success": True, "instance_id": instance_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}
    
    async def restart_instance(self, instance_id: str) -> Dict:
        """Restart an EC2 instance"""
        logger.info(f"[AWS] Restart instance: {instance_id}")
        
        if self._boto3_available:
            try:
                self.ec2.reboot_instances(InstanceIds=[instance_id])
                return {"success": True, "instance_id": instance_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}
    
    async def scale_asg(self, asg_name: str, desired: int, min_size: int = None, max_size: int = None) -> Dict:
        """Scale Auto Scaling Group"""
        logger.info(f"[AWS] Scale ASG: {asg_name} -> {desired}")
        
        if self._boto3_available:
            try:
                params = {
                    "AutoScalingGroupName": asg_name,
                    "DesiredCapacity": desired
                }
                if min_size is not None:
                    params["MinSize"] = min_size
                if max_size is not None:
                    params["MaxSize"] = max_size
                
                self.autoscaling.update_auto_scaling_group(**params)
                return {"success": True, "asg": asg_name, "desired": desired}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}
    
    async def force_ecs_deployment(self, cluster: str, service: str) -> Dict:
        """Force new ECS deployment"""
        logger.info(f"[AWS] Force ECS deployment: {cluster}/{service}")
        
        if self._boto3_available:
            try:
                self.ecs.update_service(
                    cluster=cluster,
                    service=service,
                    forceNewDeployment=True
                )
                return {"success": True, "cluster": cluster, "service": service}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}
    
    async def rds_failover(self, db_cluster_id: str) -> Dict:
        """Trigger RDS Aurora failover"""
        logger.info(f"[AWS] RDS failover: {db_cluster_id}")
        
        if self._boto3_available:
            try:
                self.rds.failover_db_cluster(DBClusterIdentifier=db_cluster_id)
                return {"success": True, "cluster": db_cluster_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}
    
    async def invoke_lambda(self, function_name: str, payload: Dict) -> Dict:
        """Invoke a Lambda function"""
        logger.info(f"[AWS] Invoke Lambda: {function_name}")
        
        if self._boto3_available:
            try:
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(payload)
                )
                return {
                    "success": True,
                    "function": function_name,
                    "status_code": response['StatusCode']
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "boto3 not available"}


class DatabaseClient(InfrastructureClient):
    """
    Database operations for PostgreSQL, MySQL, MongoDB, Redis
    """
    
    def __init__(self):
        self.connections = {}
    
    def is_available(self) -> bool:
        return True  # Individual connections checked per operation
    
    async def execute(self, action: str, params: Dict) -> Dict:
        """Execute database action"""
        
        if action == "kill_idle_connections":
            return await self.kill_idle_connections(
                params["db_type"],
                params["connection_string"],
                params.get("idle_seconds", 300)
            )
        
        elif action == "flush_cache":
            return await self.flush_cache(
                params.get("redis_url", "redis://localhost:6379"),
                params.get("pattern", "*")
            )
        
        elif action == "vacuum_analyze":
            return await self.vacuum_analyze(
                params["connection_string"],
                params.get("table")
            )
        
        elif action == "reindex":
            return await self.reindex(
                params["connection_string"],
                params["table"]
            )
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    async def kill_idle_connections(self, db_type: str, conn_string: str, idle_seconds: int) -> Dict:
        """Kill idle database connections"""
        logger.info(f"[DB] Kill idle connections > {idle_seconds}s")
        
        if db_type == "postgresql":
            try:
                import psycopg2
                conn = psycopg2.connect(conn_string)
                cur = conn.cursor()
                
                cur.execute(f"""
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE state = 'idle' 
                    AND state_change < NOW() - INTERVAL '{idle_seconds} seconds'
                    AND pid != pg_backend_pid()
                """)
                
                killed = cur.rowcount
                conn.commit()
                cur.close()
                conn.close()
                
                return {"success": True, "connections_killed": killed}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"Unsupported db_type: {db_type}"}
    
    async def flush_cache(self, redis_url: str, pattern: str = "*") -> Dict:
        """Flush Redis cache"""
        logger.info(f"[REDIS] Flush cache pattern: {pattern}")
        
        try:
            import redis
            r = redis.from_url(redis_url)
            
            if pattern == "*":
                r.flushdb()
                return {"success": True, "flushed": "all"}
            else:
                keys = r.keys(pattern)
                if keys:
                    r.delete(*keys)
                return {"success": True, "keys_deleted": len(keys)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def vacuum_analyze(self, conn_string: str, table: str = None) -> Dict:
        """Run VACUUM ANALYZE on PostgreSQL"""
        logger.info(f"[DB] VACUUM ANALYZE: {table or 'all tables'}")
        
        try:
            import psycopg2
            conn = psycopg2.connect(conn_string)
            conn.autocommit = True
            cur = conn.cursor()
            
            if table:
                cur.execute(f"VACUUM ANALYZE {table}")
            else:
                cur.execute("VACUUM ANALYZE")
            
            cur.close()
            conn.close()
            
            return {"success": True, "table": table or "all"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def reindex(self, conn_string: str, table: str) -> Dict:
        """Reindex a table"""
        logger.info(f"[DB] REINDEX: {table}")
        
        try:
            import psycopg2
            conn = psycopg2.connect(conn_string)
            conn.autocommit = True
            cur = conn.cursor()
            
            cur.execute(f"REINDEX TABLE {table}")
            
            cur.close()
            conn.close()
            
            return {"success": True, "table": table}
        except Exception as e:
            return {"success": False, "error": str(e)}


class DockerClient(InfrastructureClient):
    """Docker operations"""
    
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def execute(self, action: str, params: Dict) -> Dict:
        if action == "restart_container":
            return await self.restart_container(params["container"])
        
        elif action == "recreate_container":
            return await self.recreate_container(params["service"])
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    async def restart_container(self, container: str) -> Dict:
        """Restart a Docker container"""
        logger.info(f"[DOCKER] Restart container: {container}")
        
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True, text=True
        )
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }
    
    async def recreate_container(self, service: str) -> Dict:
        """Recreate container using docker-compose"""
        logger.info(f"[DOCKER] Recreate service: {service}")
        
        result = subprocess.run(
            ["docker-compose", "up", "-d", "--force-recreate", service],
            capture_output=True, text=True
        )
        
        return {
            "success": result.returncode == 0,
            "message": result.stdout or result.stderr
        }


# =============================================================================
# PRODUCTION EXECUTOR
# =============================================================================

class ProductionExecutor:
    """
    Main production executor that routes actions to appropriate infrastructure clients
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
        
        # Initialize infrastructure clients
        self.k8s = KubernetesClient()
        self.aws = AWSClient()
        self.db = DatabaseClient()
        self.docker = DockerClient()
        
        # Action to infrastructure mapping
        self.action_routing = {
            # Kubernetes actions
            "rollback": ("k8s", "rollback"),
            "scale_up": ("k8s", "scale"),
            "scale_down": ("k8s", "scale"),
            "restart_service": ("k8s", "rollout_restart"),
            "drain_node": ("k8s", "drain_node"),
            "cordon_node": ("k8s", "cordon_node"),
            "delete_pod": ("k8s", "delete_pod"),
            "update_resources": ("k8s", "apply_resource_limits"),
            
            # AWS actions
            "terminate_instance": ("aws", "terminate_instance"),
            "restart_instance": ("aws", "restart_instance"),
            "scale_asg": ("aws", "scale_asg"),
            "ecs_redeploy": ("aws", "force_ecs_deployment"),
            "rds_failover": ("aws", "rds_failover"),
            "invoke_lambda": ("aws", "invoke_lambda"),
            
            # Database actions
            "kill_connections": ("db", "kill_idle_connections"),
            "clear_cache": ("db", "flush_cache"),
            "vacuum_analyze": ("db", "vacuum_analyze"),
            "reindex": ("db", "reindex"),
            
            # Docker actions
            "restart_container": ("docker", "restart_container"),
            "recreate_container": ("docker", "recreate_container"),
        }
        
        logger.info(f"[PRODUCTION] Executor initialized (dry_run={self.dry_run})")
        self._log_availability()
    
    def _log_availability(self):
        """Log which infrastructure clients are available"""
        clients = {
            "Kubernetes": self.k8s.is_available(),
            "AWS": self.aws.is_available(),
            "Docker": self.docker.is_available(),
        }
        for name, available in clients.items():
            status = "✓ Available" if available else "✗ Not configured"
            logger.info(f"[PRODUCTION] {name}: {status}")
    
    def get_client(self, client_type: str) -> InfrastructureClient:
        """Get infrastructure client by type"""
        clients = {
            "k8s": self.k8s,
            "aws": self.aws,
            "db": self.db,
            "docker": self.docker,
        }
        return clients.get(client_type)
    
    async def execute_action(self, action_type: str, service: str, params: Dict) -> Dict:
        """
        Execute a production action
        
        Args:
            action_type: Type of action (rollback, scale_up, restart_service, etc.)
            service: Target service name
            params: Action-specific parameters
        
        Returns:
            Dict with success status and result details
        """
        
        # Check if action is routable
        routing = self.action_routing.get(action_type)
        if not routing:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "available_actions": list(self.action_routing.keys())
            }
        
        client_type, client_action = routing
        client = self.get_client(client_type)
        
        if not client:
            return {"success": False, "error": f"Client not found: {client_type}"}
        
        # Dry run check
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would execute {action_type} on {service}",
                "action": client_action,
                "params": params
            }
        
        # Check client availability
        if not client.is_available():
            return {
                "success": False,
                "error": f"{client_type} client not available/configured"
            }
        
        # Add service to params if needed
        params["service"] = service
        if "deployment" not in params:
            params["deployment"] = service
        
        # Execute the action
        logger.info(f"[PRODUCTION] Executing {action_type} on {service}")
        
        try:
            result = await client.execute(client_action, params)
            
            # Record to Redis if available
            if self.redis:
                self._record_execution(action_type, service, result)
            
            return result
            
        except Exception as e:
            logger.error(f"[PRODUCTION] Action failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _record_execution(self, action_type: str, service: str, result: Dict):
        """Record action execution to Redis"""
        record = {
            "action_type": action_type,
            "service": service,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.redis.lpush("production_executions", json.dumps(record))
        self.redis.ltrim("production_executions", 0, 999)  # Keep last 1000
    
    def enable_production_mode(self):
        """Disable dry-run - USE WITH CAUTION"""
        self.dry_run = False
        logger.warning("[PRODUCTION] ⚠️  PRODUCTION MODE ENABLED - Actions will execute!")
    
    def enable_dry_run_mode(self):
        """Enable dry-run mode (safe)"""
        self.dry_run = True
        logger.info("[PRODUCTION] ✓ DRY RUN MODE - Actions will be simulated")
    
    def get_supported_actions(self) -> Dict:
        """Get all supported actions grouped by infrastructure"""
        by_infra = {}
        for action_type, (infra, _) in self.action_routing.items():
            if infra not in by_infra:
                by_infra[infra] = []
            by_infra[infra].append(action_type)
        return by_infra


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def quick_restart_service(service: str, namespace: str = "default") -> Dict:
    """Quick function to restart a Kubernetes service"""
    executor = ProductionExecutor()
    return await executor.execute_action(
        "restart_service",
        service,
        {"namespace": namespace}
    )


async def quick_scale_service(service: str, replicas: int, namespace: str = "default") -> Dict:
    """Quick function to scale a Kubernetes service"""
    executor = ProductionExecutor()
    return await executor.execute_action(
        "scale_up" if replicas > 1 else "scale_down",
        service,
        {"replicas": replicas, "namespace": namespace}
    )


async def quick_clear_cache(redis_url: str = "redis://localhost:6379") -> Dict:
    """Quick function to clear Redis cache"""
    executor = ProductionExecutor()
    return await executor.execute_action(
        "clear_cache",
        "redis",
        {"redis_url": redis_url}
    )


# =============================================================================
# MAIN - For testing
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        executor = ProductionExecutor()
        
        # Show supported actions
        print("\n📋 Supported Actions:")
        for infra, actions in executor.get_supported_actions().items():
            print(f"  {infra.upper()}: {', '.join(actions)}")
        
        # Test dry-run execution
        print("\n🧪 Testing dry-run execution:")
        result = await executor.execute_action(
            "restart_service",
            "test-service",
            {"namespace": "default"}
        )
        print(f"  Result: {result}")
    
    asyncio.run(test())
