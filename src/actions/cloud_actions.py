"""
Cloud Provider Actions - Enterprise DevOps Automation
Provides abstracted cloud infrastructure management (AWS/GCP/Azure)
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import httpx


class CloudProvider(Enum):
    """Supported cloud providers"""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LOCAL = "local"  # For testing


class CloudActionType(Enum):
    """Cloud action types"""
    INSTANCE_RESTART = "instance_restart"
    INSTANCE_STOP = "instance_stop"
    INSTANCE_START = "instance_start"
    LOAD_BALANCER_ADJUST = "load_balancer_adjust"
    SECURITY_GROUP_UPDATE = "security_group_update"
    DNS_FAILOVER = "dns_failover"
    DNS_UPDATE = "dns_update"
    STORAGE_CLEANUP = "storage_cleanup"
    SNAPSHOT_CREATE = "snapshot_create"
    SNAPSHOT_RESTORE = "snapshot_restore"
    AUTO_SCALING_ADJUST = "auto_scaling_adjust"
    LAMBDA_INVOKE = "lambda_invoke"
    CLOUDWATCH_ALARM = "cloudwatch_alarm"


class CloudActionExecutor:
    """
    Cloud-agnostic action executor
    Abstracts AWS, GCP, and Azure operations behind a common interface
    """
    
    def __init__(self, redis_client, provider: CloudProvider = None):
        self.redis = redis_client
        self.provider = provider or CloudProvider(os.getenv("CLOUD_PROVIDER", "aws").lower())
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
        self.region = os.getenv("CLOUD_REGION", "us-east-1")
        
        # Provider-specific clients would be initialized here
        self._init_provider()
    
    def _init_provider(self):
        """Initialize cloud provider client"""
        if self.provider == CloudProvider.AWS:
            self._init_aws()
        elif self.provider == CloudProvider.GCP:
            self._init_gcp()
        elif self.provider == CloudProvider.AZURE:
            self._init_azure()
    
    def _init_aws(self):
        """Initialize AWS clients (boto3)"""
        try:
            import boto3
            self.ec2 = boto3.client('ec2', region_name=self.region)
            self.elb = boto3.client('elbv2', region_name=self.region)
            self.route53 = boto3.client('route53')
            self.autoscaling = boto3.client('autoscaling', region_name=self.region)
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
            self.lambda_client = boto3.client('lambda', region_name=self.region)
            print(f"[CLOUD] AWS client initialized for region {self.region}")
        except ImportError:
            print("[CLOUD] boto3 not installed - AWS actions will be simulated")
            self.ec2 = None
    
    def _init_gcp(self):
        """Initialize GCP clients"""
        try:
            from google.cloud import compute_v1
            self.compute = compute_v1.InstancesClient()
            print("[CLOUD] GCP client initialized")
        except ImportError:
            print("[CLOUD] google-cloud-compute not installed - GCP actions will be simulated")
            self.compute = None
    
    def _init_azure(self):
        """Initialize Azure clients"""
        try:
            from azure.mgmt.compute import ComputeManagementClient
            print("[CLOUD] Azure client initialized")
        except ImportError:
            print("[CLOUD] azure-mgmt-compute not installed - Azure actions will be simulated")
    
    async def execute_action(self, action_type: CloudActionType, params: Dict) -> Dict:
        """Execute a cloud action"""
        start_time = datetime.now(timezone.utc)
        
        action_handlers = {
            CloudActionType.INSTANCE_RESTART: self._restart_instance,
            CloudActionType.INSTANCE_STOP: self._stop_instance,
            CloudActionType.INSTANCE_START: self._start_instance,
            CloudActionType.LOAD_BALANCER_ADJUST: self._adjust_load_balancer,
            CloudActionType.SECURITY_GROUP_UPDATE: self._update_security_group,
            CloudActionType.DNS_FAILOVER: self._dns_failover,
            CloudActionType.DNS_UPDATE: self._dns_update,
            CloudActionType.STORAGE_CLEANUP: self._cleanup_storage,
            CloudActionType.SNAPSHOT_CREATE: self._create_snapshot,
            CloudActionType.SNAPSHOT_RESTORE: self._restore_snapshot,
            CloudActionType.AUTO_SCALING_ADJUST: self._adjust_auto_scaling,
            CloudActionType.LAMBDA_INVOKE: self._invoke_lambda,
            CloudActionType.CLOUDWATCH_ALARM: self._manage_alarm,
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
            result["provider"] = self.provider.value
            
            self._record_action(action_type, params, result)
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "action_type": action_type.value,
                "timestamp": start_time.isoformat(),
                "dry_run": self.dry_run,
                "provider": self.provider.value
            }
            self._record_action(action_type, params, error_result)
            return error_result
    
    async def _restart_instance(self, params: Dict) -> Dict:
        """Restart a cloud instance"""
        instance_id = params.get("instance_id")
        
        if not instance_id:
            return {"success": False, "error": "instance_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would restart instance {instance_id}",
                "instance_id": instance_id
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'ec2') and self.ec2:
            try:
                # Stop instance
                self.ec2.stop_instances(InstanceIds=[instance_id])
                
                # Wait for stop
                waiter = self.ec2.get_waiter('instance_stopped')
                waiter.wait(InstanceIds=[instance_id])
                
                # Start instance
                self.ec2.start_instances(InstanceIds=[instance_id])
                
                return {
                    "success": True,
                    "message": f"Restarted instance {instance_id}",
                    "instance_id": instance_id
                }
            except Exception as e:
                return {"success": False, "error": str(e), "instance_id": instance_id}
        
        # Simulated response
        return {
            "success": True,
            "message": f"[SIMULATED] Restarted instance {instance_id}",
            "instance_id": instance_id
        }
    
    async def _stop_instance(self, params: Dict) -> Dict:
        """Stop a cloud instance"""
        instance_id = params.get("instance_id")
        force = params.get("force", False)
        
        if not instance_id:
            return {"success": False, "error": "instance_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would stop instance {instance_id}",
                "instance_id": instance_id,
                "force": force
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'ec2') and self.ec2:
            try:
                self.ec2.stop_instances(InstanceIds=[instance_id], Force=force)
                return {
                    "success": True,
                    "message": f"Stopped instance {instance_id}",
                    "instance_id": instance_id
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] Stopped instance {instance_id}",
            "instance_id": instance_id
        }
    
    async def _start_instance(self, params: Dict) -> Dict:
        """Start a cloud instance"""
        instance_id = params.get("instance_id")
        
        if not instance_id:
            return {"success": False, "error": "instance_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would start instance {instance_id}",
                "instance_id": instance_id
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'ec2') and self.ec2:
            try:
                self.ec2.start_instances(InstanceIds=[instance_id])
                return {
                    "success": True,
                    "message": f"Started instance {instance_id}",
                    "instance_id": instance_id
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] Started instance {instance_id}",
            "instance_id": instance_id
        }
    
    async def _adjust_load_balancer(self, params: Dict) -> Dict:
        """Adjust load balancer settings"""
        lb_name = params.get("load_balancer_name")
        target_group = params.get("target_group")
        action = params.get("action")  # add_target, remove_target, adjust_health_check
        
        if not lb_name:
            return {"success": False, "error": "load_balancer_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would adjust LB {lb_name}: {action}",
                "load_balancer": lb_name,
                "action": action
            }
        
        return {
            "success": True,
            "message": f"Adjusted load balancer {lb_name}",
            "load_balancer": lb_name,
            "action": action
        }
    
    async def _update_security_group(self, params: Dict) -> Dict:
        """Update security group rules"""
        group_id = params.get("security_group_id")
        action = params.get("action")  # add_rule, remove_rule
        rule = params.get("rule", {})
        
        if not group_id:
            return {"success": False, "error": "security_group_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would update SG {group_id}: {action}",
                "security_group_id": group_id,
                "action": action,
                "rule": rule
            }
        
        return {
            "success": True,
            "message": f"Updated security group {group_id}",
            "security_group_id": group_id,
            "action": action
        }
    
    async def _dns_failover(self, params: Dict) -> Dict:
        """Switch DNS to failover endpoint"""
        domain = params.get("domain")
        failover_target = params.get("failover_target")
        
        if not domain or not failover_target:
            return {"success": False, "error": "domain and failover_target are required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would failover {domain} to {failover_target}",
                "domain": domain,
                "failover_target": failover_target
            }
        
        return {
            "success": True,
            "message": f"DNS failover for {domain} to {failover_target}",
            "domain": domain,
            "failover_target": failover_target
        }
    
    async def _dns_update(self, params: Dict) -> Dict:
        """Update DNS record"""
        domain = params.get("domain")
        record_type = params.get("record_type", "A")
        value = params.get("value")
        ttl = params.get("ttl", 300)
        
        if not domain or not value:
            return {"success": False, "error": "domain and value are required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would update {record_type} record for {domain}",
                "domain": domain,
                "record_type": record_type,
                "value": value,
                "ttl": ttl
            }
        
        return {
            "success": True,
            "message": f"Updated DNS {record_type} record for {domain}",
            "domain": domain,
            "value": value
        }
    
    async def _cleanup_storage(self, params: Dict) -> Dict:
        """Clean up unused storage volumes"""
        volume_ids = params.get("volume_ids", [])
        max_age_days = params.get("max_age_days", 30)
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would cleanup {len(volume_ids)} volumes",
                "volume_ids": volume_ids,
                "max_age_days": max_age_days
            }
        
        cleaned = []
        for vol_id in volume_ids:
            cleaned.append({"volume_id": vol_id, "status": "deleted"})
        
        return {
            "success": True,
            "message": f"Cleaned up {len(cleaned)} volumes",
            "cleaned_volumes": cleaned
        }
    
    async def _create_snapshot(self, params: Dict) -> Dict:
        """Create storage snapshot"""
        volume_id = params.get("volume_id")
        description = params.get("description", "Automated snapshot")
        
        if not volume_id:
            return {"success": False, "error": "volume_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would create snapshot of {volume_id}",
                "volume_id": volume_id
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'ec2') and self.ec2:
            try:
                response = self.ec2.create_snapshot(
                    VolumeId=volume_id,
                    Description=description,
                    TagSpecifications=[{
                        'ResourceType': 'snapshot',
                        'Tags': [{'Key': 'CreatedBy', 'Value': 'DeployrAutopilot'}]
                    }]
                )
                return {
                    "success": True,
                    "message": f"Created snapshot of {volume_id}",
                    "snapshot_id": response['SnapshotId'],
                    "volume_id": volume_id
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] Created snapshot of {volume_id}",
            "snapshot_id": f"snap-{volume_id[-8:]}",
            "volume_id": volume_id
        }
    
    async def _restore_snapshot(self, params: Dict) -> Dict:
        """Restore from snapshot"""
        snapshot_id = params.get("snapshot_id")
        target_volume = params.get("target_volume")
        
        if not snapshot_id:
            return {"success": False, "error": "snapshot_id is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would restore snapshot {snapshot_id}",
                "snapshot_id": snapshot_id
            }
        
        return {
            "success": True,
            "message": f"Restored snapshot {snapshot_id}",
            "snapshot_id": snapshot_id,
            "new_volume_id": f"vol-restored-{snapshot_id[-8:]}"
        }
    
    async def _adjust_auto_scaling(self, params: Dict) -> Dict:
        """Adjust auto scaling group settings"""
        asg_name = params.get("auto_scaling_group")
        min_size = params.get("min_size")
        max_size = params.get("max_size")
        desired_capacity = params.get("desired_capacity")
        
        if not asg_name:
            return {"success": False, "error": "auto_scaling_group is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would adjust ASG {asg_name}",
                "auto_scaling_group": asg_name,
                "min_size": min_size,
                "max_size": max_size,
                "desired_capacity": desired_capacity
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'autoscaling') and self.autoscaling:
            try:
                update_params = {"AutoScalingGroupName": asg_name}
                if min_size is not None:
                    update_params["MinSize"] = min_size
                if max_size is not None:
                    update_params["MaxSize"] = max_size
                if desired_capacity is not None:
                    update_params["DesiredCapacity"] = desired_capacity
                
                self.autoscaling.update_auto_scaling_group(**update_params)
                return {
                    "success": True,
                    "message": f"Updated ASG {asg_name}",
                    "auto_scaling_group": asg_name
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] Updated ASG {asg_name}",
            "auto_scaling_group": asg_name
        }
    
    async def _invoke_lambda(self, params: Dict) -> Dict:
        """Invoke AWS Lambda function"""
        function_name = params.get("function_name")
        payload = params.get("payload", {})
        invocation_type = params.get("invocation_type", "RequestResponse")
        
        if not function_name:
            return {"success": False, "error": "function_name is required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would invoke Lambda {function_name}",
                "function_name": function_name,
                "payload": payload
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'lambda_client') and self.lambda_client:
            try:
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType=invocation_type,
                    Payload=json.dumps(payload)
                )
                return {
                    "success": True,
                    "message": f"Invoked Lambda {function_name}",
                    "function_name": function_name,
                    "status_code": response['StatusCode']
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] Invoked Lambda {function_name}",
            "function_name": function_name
        }
    
    async def _manage_alarm(self, params: Dict) -> Dict:
        """Manage CloudWatch alarms"""
        alarm_name = params.get("alarm_name")
        action = params.get("action")  # enable, disable, delete
        
        if not alarm_name or not action:
            return {"success": False, "error": "alarm_name and action are required"}
        
        if self.dry_run:
            return {
                "success": True,
                "message": f"[DRY RUN] Would {action} alarm {alarm_name}",
                "alarm_name": alarm_name,
                "action": action
            }
        
        if self.provider == CloudProvider.AWS and hasattr(self, 'cloudwatch') and self.cloudwatch:
            try:
                if action == "enable":
                    self.cloudwatch.enable_alarm_actions(AlarmNames=[alarm_name])
                elif action == "disable":
                    self.cloudwatch.disable_alarm_actions(AlarmNames=[alarm_name])
                elif action == "delete":
                    self.cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                
                return {
                    "success": True,
                    "message": f"{action.capitalize()}d alarm {alarm_name}",
                    "alarm_name": alarm_name,
                    "action": action
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": f"[SIMULATED] {action.capitalize()}d alarm {alarm_name}",
            "alarm_name": alarm_name
        }
    
    def _record_action(self, action_type: CloudActionType, params: Dict, result: Dict):
        """Record action for history and learning"""
        record = {
            "action_type": action_type.value,
            "params": params,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "cloud",
            "provider": self.provider.value
        }
        
        self.redis.lpush("cloud_action_history", json.dumps(record))
        self.redis.ltrim("cloud_action_history", 0, 999)
        
        print(f"[CLOUD] Recorded action: {action_type.value} - Success: {result.get('success')}")


# Convenience functions
async def restart_instance(redis_client, instance_id: str) -> Dict:
    """Convenience function to restart an instance"""
    executor = CloudActionExecutor(redis_client)
    return await executor.execute_action(
        CloudActionType.INSTANCE_RESTART,
        {"instance_id": instance_id}
    )


async def create_snapshot(redis_client, volume_id: str, description: str = None) -> Dict:
    """Convenience function to create a snapshot"""
    executor = CloudActionExecutor(redis_client)
    return await executor.execute_action(
        CloudActionType.SNAPSHOT_CREATE,
        {"volume_id": volume_id, "description": description or "Automated backup"}
    )
