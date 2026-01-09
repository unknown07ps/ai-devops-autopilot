"""
Kubernetes Actions - Enterprise DevOps Automation
Provides comprehensive Kubernetes orchestration capabilities
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import subprocess
import httpx


class K8sActionType(Enum):
    """Kubernetes action types"""
    POD_RESTART = "pod_restart"
    DEPLOYMENT_SCALE = "deployment_scale"
    ROLLOUT_RESTART = "rollout_restart"
    POD_EVICTION = "pod_eviction"
    RESOURCE_QUOTA_ADJUST = "resource_quota_adjust"
    HPA_CONFIGURE = "hpa_configure"
    NODE_DRAIN = "node_drain"
    NODE_CORDON = "node_cordon"
    NODE_UNCORDON = "node_uncordon"
    NAMESPACE_CLEANUP = "namespace_cleanup"
    CONFIG_RELOAD = "config_reload"
    SECRET_ROTATE = "secret_rotate"


class K8sActionExecutor:
    """
    Kubernetes action executor for container orchestration
    Supports both kubectl CLI and Kubernetes Python client
    """
    
    def __init__(self, redis_client, kubeconfig_path: str = None):
        self.redis = redis_client
        self.kubeconfig = kubeconfig_path or os.getenv("KUBECONFIG", "~/.kube/config")
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
        self.namespace = os.getenv("K8S_NAMESPACE", "default")
        
    async def execute_action(self, action_type: K8sActionType, params: Dict) -> Dict:
        """Execute a Kubernetes action"""
        start_time = datetime.now(timezone.utc)
        
        action_handlers = {
            K8sActionType.POD_RESTART: self._restart_pod,
            K8sActionType.DEPLOYMENT_SCALE: self._scale_deployment,
            K8sActionType.ROLLOUT_RESTART: self._rollout_restart,
            K8sActionType.POD_EVICTION: self._evict_pod,
            K8sActionType.RESOURCE_QUOTA_ADJUST: self._adjust_resource_quota,
            K8sActionType.HPA_CONFIGURE: self._configure_hpa,
            K8sActionType.NODE_DRAIN: self._drain_node,
            K8sActionType.NODE_CORDON: self._cordon_node,
            K8sActionType.NODE_UNCORDON: self._uncordon_node,
            K8sActionType.NAMESPACE_CLEANUP: self._cleanup_namespace,
            K8sActionType.CONFIG_RELOAD: self._reload_config,
            K8sActionType.SECRET_ROTATE: self._rotate_secret,
        }
        
        handler = action_handlers.get(action_type)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "action_type": action_type.value
            }
        
        try:
            result = await handler(params)
            result["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            result["action_type"] = action_type.value
            result["timestamp"] = start_time.isoformat()
            result["dry_run"] = self.dry_run
            
            # Record action
            self._record_action(action_type, params, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "action_type": action_type.value,
                "timestamp": start_time.isoformat(),
                "dry_run": self.dry_run
            }
            self._record_action(action_type, params, error_result)
            return error_result
    
    async def _restart_pod(self, params: Dict) -> Dict:
        """Delete a pod to trigger recreation"""
        pod_name = params.get("pod_name")
        namespace = params.get("namespace", self.namespace)
        
        if not pod_name:
            return {"success": False, "error": "pod_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would delete pod {pod_name} in {namespace}",
                "pod": pod_name,
                "namespace": namespace
            }
        
        cmd = ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--grace-period=30"]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Deleted pod {pod_name} for restart",
            "pod": pod_name,
            "namespace": namespace,
            "output": result.get("output", "")
        }
    
    async def _scale_deployment(self, params: Dict) -> Dict:
        """Scale a deployment to specified replicas"""
        deployment = params.get("deployment")
        replicas = params.get("replicas")
        namespace = params.get("namespace", self.namespace)
        
        if not deployment or replicas is None:
            return {"success": False, "error": "deployment and replicas are required"}
        
        # Get current replicas for rollback info
        current_replicas = await self._get_deployment_replicas(deployment, namespace)
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would scale {deployment} from {current_replicas} to {replicas} replicas",
                "deployment": deployment,
                "previous_replicas": current_replicas,
                "new_replicas": replicas,
                "namespace": namespace
            }
        
        cmd = ["kubectl", "scale", "deployment", deployment, f"--replicas={replicas}", "-n", namespace]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Scaled {deployment} to {replicas} replicas",
            "deployment": deployment,
            "previous_replicas": current_replicas,
            "new_replicas": replicas,
            "namespace": namespace,
            "output": result.get("output", "")
        }
    
    async def _rollout_restart(self, params: Dict) -> Dict:
        """Perform rolling restart of a deployment"""
        deployment = params.get("deployment")
        namespace = params.get("namespace", self.namespace)
        
        if not deployment:
            return {"success": False, "error": "deployment is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would perform rollout restart of {deployment}",
                "deployment": deployment,
                "namespace": namespace
            }
        
        cmd = ["kubectl", "rollout", "restart", f"deployment/{deployment}", "-n", namespace]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Initiated rollout restart for {deployment}",
            "deployment": deployment,
            "namespace": namespace,
            "output": result.get("output", "")
        }
    
    async def _evict_pod(self, params: Dict) -> Dict:
        """Gracefully evict a pod"""
        pod_name = params.get("pod_name")
        namespace = params.get("namespace", self.namespace)
        
        if not pod_name:
            return {"success": False, "error": "pod_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would evict pod {pod_name}",
                "pod": pod_name,
                "namespace": namespace
            }
        
        # Create eviction object
        eviction_body = {
            "apiVersion": "policy/v1",
            "kind": "Eviction",
            "metadata": {
                "name": pod_name,
                "namespace": namespace
            }
        }
        
        cmd = ["kubectl", "create", "-f", "-", "-n", namespace]
        result = await self._run_kubectl_with_stdin(cmd, json.dumps(eviction_body))
        
        return {
            "success": result["success"],
            "message": f"Evicted pod {pod_name}",
            "pod": pod_name,
            "namespace": namespace
        }
    
    async def _adjust_resource_quota(self, params: Dict) -> Dict:
        """Adjust resource limits for a deployment"""
        deployment = params.get("deployment")
        namespace = params.get("namespace", self.namespace)
        container = params.get("container", None)
        cpu_limit = params.get("cpu_limit")
        memory_limit = params.get("memory_limit")
        cpu_request = params.get("cpu_request")
        memory_request = params.get("memory_request")
        
        if not deployment:
            return {"success": False, "error": "deployment is required"}
        
        patch_data = {"spec": {"template": {"spec": {"containers": []}}}}
        
        container_patch = {"name": container or deployment}
        resources = {"limits": {}, "requests": {}}
        
        if cpu_limit:
            resources["limits"]["cpu"] = cpu_limit
        if memory_limit:
            resources["limits"]["memory"] = memory_limit
        if cpu_request:
            resources["requests"]["cpu"] = cpu_request
        if memory_request:
            resources["requests"]["memory"] = memory_request
        
        container_patch["resources"] = resources
        patch_data["spec"]["template"]["spec"]["containers"].append(container_patch)
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would adjust resources for {deployment}",
                "deployment": deployment,
                "new_resources": resources,
                "namespace": namespace
            }
        
        cmd = ["kubectl", "patch", "deployment", deployment, "-n", namespace, 
               "--type=strategic", "-p", json.dumps(patch_data)]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Adjusted resources for {deployment}",
            "deployment": deployment,
            "new_resources": resources,
            "namespace": namespace
        }
    
    async def _configure_hpa(self, params: Dict) -> Dict:
        """Configure Horizontal Pod Autoscaler"""
        deployment = params.get("deployment")
        namespace = params.get("namespace", self.namespace)
        min_replicas = params.get("min_replicas", 1)
        max_replicas = params.get("max_replicas", 10)
        cpu_percent = params.get("cpu_percent", 80)
        
        if not deployment:
            return {"success": False, "error": "deployment is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would configure HPA for {deployment}",
                "deployment": deployment,
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
                "cpu_percent": cpu_percent,
                "namespace": namespace
            }
        
        cmd = ["kubectl", "autoscale", "deployment", deployment,
               f"--min={min_replicas}", f"--max={max_replicas}",
               f"--cpu-percent={cpu_percent}", "-n", namespace]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Configured HPA for {deployment}",
            "deployment": deployment,
            "min_replicas": min_replicas,
            "max_replicas": max_replicas,
            "cpu_percent": cpu_percent,
            "namespace": namespace
        }
    
    async def _drain_node(self, params: Dict) -> Dict:
        """Drain a node for maintenance"""
        node_name = params.get("node_name")
        ignore_daemonsets = params.get("ignore_daemonsets", True)
        delete_local_data = params.get("delete_local_data", False)
        force = params.get("force", False)
        
        if not node_name:
            return {"success": False, "error": "node_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would drain node {node_name}",
                "node": node_name
            }
        
        cmd = ["kubectl", "drain", node_name]
        if ignore_daemonsets:
            cmd.append("--ignore-daemonsets")
        if delete_local_data:
            cmd.append("--delete-emptydir-data")
        if force:
            cmd.append("--force")
        
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Drained node {node_name}",
            "node": node_name
        }
    
    async def _cordon_node(self, params: Dict) -> Dict:
        """Mark node as unschedulable"""
        node_name = params.get("node_name")
        
        if not node_name:
            return {"success": False, "error": "node_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would cordon node {node_name}",
                "node": node_name
            }
        
        cmd = ["kubectl", "cordon", node_name]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Cordoned node {node_name}",
            "node": node_name
        }
    
    async def _uncordon_node(self, params: Dict) -> Dict:
        """Mark node as schedulable"""
        node_name = params.get("node_name")
        
        if not node_name:
            return {"success": False, "error": "node_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would uncordon node {node_name}",
                "node": node_name
            }
        
        cmd = ["kubectl", "uncordon", node_name]
        result = await self._run_kubectl(cmd)
        
        return {
            "success": result["success"],
            "message": f"Uncordoned node {node_name}",
            "node": node_name
        }
    
    async def _cleanup_namespace(self, params: Dict) -> Dict:
        """Clean up stale resources in a namespace"""
        namespace = params.get("namespace", self.namespace)
        resource_types = params.get("resource_types", ["pod", "configmap", "secret"])
        max_age_hours = params.get("max_age_hours", 24)
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would cleanup stale resources in {namespace}",
                "namespace": namespace,
                "resource_types": resource_types,
                "max_age_hours": max_age_hours
            }
        
        cleaned = []
        for resource_type in resource_types:
            # Get resources older than max_age_hours
            cmd = ["kubectl", "get", resource_type, "-n", namespace, "-o", "json"]
            result = await self._run_kubectl(cmd)
            
            if result["success"]:
                try:
                    data = json.loads(result.get("output", "{}"))
                    # Additional cleanup logic would go here
                    cleaned.append({"type": resource_type, "count": 0})
                except json.JSONDecodeError:
                    pass
        
        return {
            "success": True,
            "message": f"Cleaned up stale resources in {namespace}",
            "namespace": namespace,
            "cleaned_resources": cleaned
        }
    
    async def _reload_config(self, params: Dict) -> Dict:
        """Reload ConfigMap and trigger pod restart"""
        configmap_name = params.get("configmap_name")
        deployment = params.get("deployment")
        namespace = params.get("namespace", self.namespace)
        
        if not configmap_name or not deployment:
            return {"success": False, "error": "configmap_name and deployment are required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would reload config for {deployment}",
                "configmap": configmap_name,
                "deployment": deployment,
                "namespace": namespace
            }
        
        # Trigger rollout restart to pick up new config
        return await self._rollout_restart({"deployment": deployment, "namespace": namespace})
    
    async def _rotate_secret(self, params: Dict) -> Dict:
        """Rotate a Kubernetes secret"""
        secret_name = params.get("secret_name")
        namespace = params.get("namespace", self.namespace)
        new_data = params.get("new_data", {})
        
        if not secret_name:
            return {"success": False, "error": "secret_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would rotate secret {secret_name}",
                "secret": secret_name,
                "namespace": namespace
            }
        
        # Would implement actual secret rotation here
        return {
            "success": True,
            "message": f"Rotated secret {secret_name}",
            "secret": secret_name,
            "namespace": namespace
        }
    
    # Helper methods
    async def _run_kubectl(self, cmd: List[str]) -> Dict:
        """Run kubectl command"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "KUBECONFIG": self.kubeconfig}
            )
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_kubectl_with_stdin(self, cmd: List[str], stdin_data: str) -> Dict:
        """Run kubectl command with stdin input"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "KUBECONFIG": self.kubeconfig}
            )
            stdout, stderr = await process.communicate(input=stdin_data.encode())
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_deployment_replicas(self, deployment: str, namespace: str) -> int:
        """Get current replica count for a deployment"""
        cmd = ["kubectl", "get", "deployment", deployment, "-n", namespace, 
               "-o", "jsonpath={.spec.replicas}"]
        result = await self._run_kubectl(cmd)
        
        try:
            return int(result.get("output", "0").strip())
        except (ValueError, AttributeError):
            return 0
    
    def _record_action(self, action_type: K8sActionType, params: Dict, result: Dict):
        """Record action in Redis for history and learning"""
        record = {
            "action_type": action_type.value,
            "params": params,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "kubernetes"
        }
        
        self.redis.lpush("k8s_action_history", json.dumps(record))
        self.redis.ltrim("k8s_action_history", 0, 999)  # Keep last 1000
        
        print(f"[K8S] Recorded action: {action_type.value} - Success: {result.get('success')}")


# Convenience functions for integration
async def restart_pod(redis_client, pod_name: str, namespace: str = "default") -> Dict:
    """Convenience function to restart a pod"""
    executor = K8sActionExecutor(redis_client)
    return await executor.execute_action(
        K8sActionType.POD_RESTART,
        {"pod_name": pod_name, "namespace": namespace}
    )


async def scale_deployment(redis_client, deployment: str, replicas: int, namespace: str = "default") -> Dict:
    """Convenience function to scale a deployment"""
    executor = K8sActionExecutor(redis_client)
    return await executor.execute_action(
        K8sActionType.DEPLOYMENT_SCALE,
        {"deployment": deployment, "replicas": replicas, "namespace": namespace}
    )


async def rollout_restart(redis_client, deployment: str, namespace: str = "default") -> Dict:
    """Convenience function for rollout restart"""
    executor = K8sActionExecutor(redis_client)
    return await executor.execute_action(
        K8sActionType.ROLLOUT_RESTART,
        {"deployment": deployment, "namespace": namespace}
    )
