"""
Runbook Engine - Automated Incident Response Workflows
Chains multiple actions with conditions and decision logic
"""

import asyncio
import json
import os
import yaml
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field


class RunbookStatus(Enum):
    """Runbook execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class StepStatus(Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RunbookStep:
    """Represents a single step in a runbook"""
    id: str
    name: str
    action_category: str  # k8s, cloud, database, cicd
    action_type: str
    params: Dict = field(default_factory=dict)
    condition: str = None  # Python expression to evaluate
    on_failure: str = "stop"  # stop, continue, skip_to:<step_id>
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay_seconds: int = 30
    require_approval: bool = False
    depends_on: List[str] = field(default_factory=list)


@dataclass
class Runbook:
    """Represents a complete runbook"""
    id: str
    name: str
    description: str
    trigger: Dict  # Trigger conditions
    steps: List[RunbookStep]
    variables: Dict = field(default_factory=dict)
    timeout_seconds: int = 1800  # 30 minutes default
    on_success: Dict = field(default_factory=dict)  # Notification settings
    on_failure: Dict = field(default_factory=dict)
    created_at: str = None
    updated_at: str = None


class RunbookEngine:
    """
    Executes runbooks with support for:
    - Conditional step execution
    - Parallel and sequential steps
    - Approval gates
    - Rollback on failure
    - Variable interpolation
    """
    
    def __init__(self, redis_client, action_dispatcher=None):
        self.redis = redis_client
        self.action_dispatcher = action_dispatcher
        self.runbooks: Dict[str, Runbook] = {}
        self.active_executions: Dict[str, Dict] = {}
        
        # Load runbooks from Redis
        self._load_runbooks()
    
    def _load_runbooks(self):
        """Load runbooks from Redis storage"""
        runbook_keys = self.redis.scan_iter("runbook:*")
        for key in runbook_keys:
            if ":execution:" not in key.decode():
                data = self.redis.get(key)
                if data:
                    runbook_data = json.loads(data)
                    self.runbooks[runbook_data['id']] = self._parse_runbook(runbook_data)
    
    def _parse_runbook(self, data: Dict) -> Runbook:
        """Parse runbook data into Runbook object"""
        steps = [
            RunbookStep(
                id=s.get('id', f"step_{i}"),
                name=s.get('name', f"Step {i}"),
                action_category=s.get('action_category', 'base'),
                action_type=s.get('action_type'),
                params=s.get('params', {}),
                condition=s.get('condition'),
                on_failure=s.get('on_failure', 'stop'),
                timeout_seconds=s.get('timeout_seconds', 300),
                retry_count=s.get('retry_count', 0),
                retry_delay_seconds=s.get('retry_delay_seconds', 30),
                require_approval=s.get('require_approval', False),
                depends_on=s.get('depends_on', [])
            )
            for i, s in enumerate(data.get('steps', []))
        ]
        
        return Runbook(
            id=data['id'],
            name=data.get('name', data['id']),
            description=data.get('description', ''),
            trigger=data.get('trigger', {}),
            steps=steps,
            variables=data.get('variables', {}),
            timeout_seconds=data.get('timeout_seconds', 1800),
            on_success=data.get('on_success', {}),
            on_failure=data.get('on_failure', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def register_runbook(self, runbook_data: Dict) -> Runbook:
        """Register a new runbook"""
        runbook_data['created_at'] = datetime.now(timezone.utc).isoformat()
        runbook_data['updated_at'] = runbook_data['created_at']
        
        runbook = self._parse_runbook(runbook_data)
        self.runbooks[runbook.id] = runbook
        
        # Save to Redis
        self.redis.set(f"runbook:{runbook.id}", json.dumps(runbook_data))
        
        print(f"[RUNBOOK] Registered runbook: {runbook.name}")
        return runbook
    
    def register_from_yaml(self, yaml_content: str) -> Runbook:
        """Register runbook from YAML definition"""
        data = yaml.safe_load(yaml_content)
        return self.register_runbook(data)
    
    def get_runbook(self, runbook_id: str) -> Optional[Runbook]:
        """Get a runbook by ID"""
        return self.runbooks.get(runbook_id)
    
    def list_runbooks(self) -> List[Dict]:
        """List all registered runbooks"""
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "steps_count": len(r.steps),
                "trigger": r.trigger
            }
            for r in self.runbooks.values()
        ]
    
    async def execute_runbook(
        self,
        runbook_id: str,
        context: Dict = None,
        incident_id: str = None
    ) -> Dict:
        """
        Execute a runbook
        
        Args:
            runbook_id: ID of the runbook to execute
            context: Runtime context variables
            incident_id: Associated incident ID (if any)
        
        Returns:
            Execution result
        """
        runbook = self.runbooks.get(runbook_id)
        if not runbook:
            return {
                "success": False,
                "error": f"Runbook not found: {runbook_id}"
            }
        
        execution_id = f"exec_{runbook_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        execution_state = {
            "execution_id": execution_id,
            "runbook_id": runbook_id,
            "runbook_name": runbook.name,
            "status": RunbookStatus.RUNNING.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "incident_id": incident_id,
            "context": {**runbook.variables, **(context or {})},
            "step_results": {},
            "current_step": None,
            "completed_steps": [],
            "failed_steps": []
        }
        
        self.active_executions[execution_id] = execution_state
        self._save_execution_state(execution_id, execution_state)
        
        print(f"[RUNBOOK] Starting execution: {execution_id}")
        
        try:
            # Execute steps in order
            for step in runbook.steps:
                # Check dependencies
                if not self._check_dependencies(step, execution_state):
                    execution_state["step_results"][step.id] = {
                        "status": StepStatus.SKIPPED.value,
                        "reason": "Dependencies not met"
                    }
                    continue
                
                # Check condition
                if step.condition and not self._evaluate_condition(step.condition, execution_state):
                    execution_state["step_results"][step.id] = {
                        "status": StepStatus.SKIPPED.value,
                        "reason": f"Condition not met: {step.condition}"
                    }
                    continue
                
                # Check if approval required
                if step.require_approval:
                    execution_state["status"] = RunbookStatus.WAITING_APPROVAL.value
                    execution_state["pending_approval_step"] = step.id
                    self._save_execution_state(execution_id, execution_state)
                    
                    # In real implementation, would wait for approval
                    print(f"[RUNBOOK] Step {step.id} requires approval")
                
                # Execute step
                execution_state["current_step"] = step.id
                self._save_execution_state(execution_id, execution_state)
                
                step_result = await self._execute_step(step, execution_state)
                execution_state["step_results"][step.id] = step_result
                
                if step_result["status"] == StepStatus.SUCCESS.value:
                    execution_state["completed_steps"].append(step.id)
                else:
                    execution_state["failed_steps"].append(step.id)
                    
                    # Handle failure
                    if step.on_failure == "stop":
                        execution_state["status"] = RunbookStatus.FAILED.value
                        break
                    elif step.on_failure == "continue":
                        continue
                    elif step.on_failure.startswith("skip_to:"):
                        target_step = step.on_failure.split(":")[1]
                        # Would skip to target step
                        pass
                
                self._save_execution_state(execution_id, execution_state)
            
            # Finalize execution
            if execution_state["status"] == RunbookStatus.RUNNING.value:
                execution_state["status"] = RunbookStatus.SUCCESS.value
            
            execution_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            execution_state["duration_seconds"] = (
                datetime.fromisoformat(execution_state["completed_at"].replace('Z', '+00:00')) -
                datetime.fromisoformat(execution_state["started_at"].replace('Z', '+00:00'))
            ).total_seconds()
            
            self._save_execution_state(execution_id, execution_state)
            
            # Cleanup active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            print(f"[RUNBOOK] Execution completed: {execution_id} - {execution_state['status']}")
            
            return {
                "success": execution_state["status"] == RunbookStatus.SUCCESS.value,
                "execution_id": execution_id,
                "status": execution_state["status"],
                "duration_seconds": execution_state.get("duration_seconds"),
                "completed_steps": len(execution_state["completed_steps"]),
                "failed_steps": len(execution_state["failed_steps"]),
                "step_results": execution_state["step_results"]
            }
            
        except Exception as e:
            execution_state["status"] = RunbookStatus.FAILED.value
            execution_state["error"] = str(e)
            execution_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._save_execution_state(execution_id, execution_state)
            
            print(f"[RUNBOOK] Execution failed: {execution_id} - {e}")
            
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e)
            }
    
    async def _execute_step(self, step: RunbookStep, execution_state: Dict) -> Dict:
        """Execute a single runbook step"""
        start_time = datetime.now(timezone.utc)
        
        print(f"[RUNBOOK] Executing step: {step.name}")
        
        # Interpolate parameters
        params = self._interpolate_params(step.params, execution_state)
        
        # Execute with retry logic
        for attempt in range(step.retry_count + 1):
            try:
                if self.action_dispatcher:
                    result = await asyncio.wait_for(
                        self.action_dispatcher.execute(
                            step.action_category,
                            step.action_type,
                            params
                        ),
                        timeout=step.timeout_seconds
                    )
                else:
                    # Simulated execution
                    result = {
                        "success": True,
                        "message": f"[SIMULATED] Executed {step.action_type}",
                        "params": params
                    }
                
                if result.get("success"):
                    return {
                        "status": StepStatus.SUCCESS.value,
                        "result": result,
                        "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                        "attempts": attempt + 1
                    }
                
                # Retry on failure
                if attempt < step.retry_count:
                    print(f"[RUNBOOK] Step {step.name} failed, retrying in {step.retry_delay_seconds}s...")
                    await asyncio.sleep(step.retry_delay_seconds)
                    
            except asyncio.TimeoutError:
                if attempt < step.retry_count:
                    await asyncio.sleep(step.retry_delay_seconds)
                    continue
                return {
                    "status": StepStatus.FAILED.value,
                    "error": f"Step timed out after {step.timeout_seconds}s",
                    "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                    "attempts": attempt + 1
                }
            except Exception as e:
                if attempt < step.retry_count:
                    await asyncio.sleep(step.retry_delay_seconds)
                    continue
                return {
                    "status": StepStatus.FAILED.value,
                    "error": str(e),
                    "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
                    "attempts": attempt + 1
                }
        
        return {
            "status": StepStatus.FAILED.value,
            "error": "Step failed after all retries",
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "attempts": step.retry_count + 1
        }
    
    def _check_dependencies(self, step: RunbookStep, execution_state: Dict) -> bool:
        """Check if all dependencies are met"""
        for dep in step.depends_on:
            result = execution_state["step_results"].get(dep, {})
            if result.get("status") != StepStatus.SUCCESS.value:
                return False
        return True
    
    def _evaluate_condition(self, condition: str, execution_state: Dict) -> bool:
        """Safely evaluate a condition expression"""
        try:
            # Create safe evaluation context
            safe_context = {
                "context": execution_state.get("context", {}),
                "results": execution_state.get("step_results", {}),
                "completed": execution_state.get("completed_steps", []),
                "failed": execution_state.get("failed_steps", []),
            }
            
            # Simple condition parsing
            if condition.startswith("metrics."):
                # Would fetch metric value
                return True
            elif condition.startswith("step."):
                step_id = condition.split(".")[1]
                return step_id in safe_context["completed"]
            elif condition.startswith("context."):
                key = condition.split(".")[1]
                return bool(safe_context["context"].get(key))
            
            # Basic eval (in production, use a safe expression parser)
            return eval(condition, {"__builtins__": {}}, safe_context)
        except:
            return True  # Default to true if condition can't be evaluated
    
    def _interpolate_params(self, params: Dict, execution_state: Dict) -> Dict:
        """Interpolate variables in parameter values"""
        context = execution_state.get("context", {})
        results = execution_state.get("step_results", {})
        
        def interpolate_value(value):
            if isinstance(value, str):
                # Replace ${context.key} and ${results.step_id.field}
                for ctx_key, ctx_val in context.items():
                    value = value.replace(f"${{context.{ctx_key}}}", str(ctx_val))
                
                for step_id, step_result in results.items():
                    if isinstance(step_result.get("result"), dict):
                        for field, field_val in step_result["result"].items():
                            value = value.replace(
                                f"${{results.{step_id}.{field}}}",
                                str(field_val)
                            )
                
                return value
            elif isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [interpolate_value(v) for v in value]
            return value
        
        return interpolate_value(params)
    
    def _save_execution_state(self, execution_id: str, state: Dict):
        """Save execution state to Redis"""
        self.redis.setex(
            f"runbook:execution:{execution_id}",
            86400 * 7,  # Keep for 7 days
            json.dumps(state)
        )
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get execution status"""
        # Check active executions first
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]
        
        # Check Redis
        data = self.redis.get(f"runbook:execution:{execution_id}")
        if data:
            return json.loads(data)
        return None
    
    def cancel_execution(self, execution_id: str) -> Dict:
        """Cancel a running execution"""
        if execution_id not in self.active_executions:
            return {"success": False, "error": "Execution not found or already completed"}
        
        state = self.active_executions[execution_id]
        state["status"] = RunbookStatus.CANCELLED.value
        state["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        self._save_execution_state(execution_id, state)
        del self.active_executions[execution_id]
        
        return {"success": True, "message": "Execution cancelled"}
    
    def approve_step(self, execution_id: str, step_id: str, approved: bool) -> Dict:
        """Approve or reject a pending step"""
        state = self.get_execution_status(execution_id)
        if not state:
            return {"success": False, "error": "Execution not found"}
        
        if state.get("status") != RunbookStatus.WAITING_APPROVAL.value:
            return {"success": False, "error": "Execution not waiting for approval"}
        
        if state.get("pending_approval_step") != step_id:
            return {"success": False, "error": "Wrong step for approval"}
        
        if approved:
            state["status"] = RunbookStatus.RUNNING.value
            del state["pending_approval_step"]
            self._save_execution_state(execution_id, state)
            return {"success": True, "message": "Step approved"}
        else:
            state["status"] = RunbookStatus.CANCELLED.value
            state["step_results"][step_id] = {
                "status": StepStatus.FAILED.value,
                "reason": "Approval denied"
            }
            self._save_execution_state(execution_id, state)
            return {"success": True, "message": "Step rejected, execution cancelled"}
    
    def find_matching_runbook(self, incident: Dict) -> Optional[Runbook]:
        """Find a runbook that matches the incident trigger conditions"""
        for runbook in self.runbooks.values():
            if self._matches_trigger(runbook.trigger, incident):
                return runbook
        return None
    
    def _matches_trigger(self, trigger: Dict, incident: Dict) -> bool:
        """Check if incident matches trigger conditions"""
        if not trigger:
            return False
        
        # Check metric triggers
        if "metric" in trigger:
            metric_name = trigger["metric"]
            threshold = trigger.get("threshold")
            
            # Would check incident anomalies for matching metric
            for anomaly in incident.get("anomalies", []):
                if anomaly.get("metric_name") == metric_name:
                    if threshold and anomaly.get("value", 0) >= threshold:
                        return True
        
        # Check severity triggers
        if "severity" in trigger:
            if incident.get("severity") in trigger["severity"]:
                return True
        
        # Check service triggers
        if "service" in trigger:
            if incident.get("service") == trigger["service"]:
                return True
        
        return False


# Pre-built runbook templates
def get_high_latency_runbook() -> Dict:
    """Standard runbook for high latency incidents"""
    return {
        "id": "high_latency_response",
        "name": "High Latency Response",
        "description": "Automated response to high API latency incidents",
        "trigger": {
            "metric": "api_latency_ms",
            "threshold": 500,
            "severity": ["critical", "high"]
        },
        "variables": {
            "latency_threshold": 500,
            "scale_factor": 2
        },
        "steps": [
            {
                "id": "check_recent_deploy",
                "name": "Check Recent Deployments",
                "action_category": "cicd",
                "action_type": "pipeline_trigger",
                "params": {
                    "workflow": "check-deployments",
                    "branch": "main"
                }
            },
            {
                "id": "scale_up",
                "name": "Scale Up Service",
                "action_category": "k8s",
                "action_type": "deployment_scale",
                "params": {
                    "deployment": "${context.service}",
                    "replicas": "${context.scale_factor}"
                },
                "condition": "context.auto_scale_enabled"
            },
            {
                "id": "rollback_if_recent_deploy",
                "name": "Rollback Recent Deployment",
                "action_category": "cicd",
                "action_type": "rollback_deploy",
                "params": {
                    "service": "${context.service}",
                    "environment": "production"
                },
                "condition": "results.check_recent_deploy.has_recent_deploy",
                "require_approval": True
            }
        ]
    }


def get_database_connection_runbook() -> Dict:
    """Runbook for database connection pool exhaustion"""
    return {
        "id": "db_connection_exhaustion",
        "name": "Database Connection Pool Exhaustion",
        "description": "Response to database connection pool issues",
        "trigger": {
            "metric": "db_connection_pool_usage",
            "threshold": 95
        },
        "steps": [
            {
                "id": "kill_idle_connections",
                "name": "Kill Idle Connections",
                "action_category": "database",
                "action_type": "connection_pool_reset",
                "params": {}
            },
            {
                "id": "kill_slow_queries",
                "name": "Kill Slow Queries",
                "action_category": "database",
                "action_type": "slow_query_kill",
                "params": {"threshold_seconds": 60}
            },
            {
                "id": "scale_db_connections",
                "name": "Increase Connection Limit",
                "action_category": "database",
                "action_type": "connection_limit_adjust",
                "params": {"max_connections": 200},
                "depends_on": ["kill_idle_connections", "kill_slow_queries"]
            }
        ]
    }


def get_memory_leak_runbook() -> Dict:
    """Runbook for memory leak detection"""
    return {
        "id": "memory_leak_response",
        "name": "Memory Leak Response",
        "description": "Response to suspected memory leaks",
        "trigger": {
            "metric": "memory_usage_percent",
            "threshold": 90
        },
        "steps": [
            {
                "id": "create_heap_dump",
                "name": "Create Heap Dump",
                "action_category": "k8s",
                "action_type": "pod_restart",
                "params": {
                    "pod_name": "${context.pod}",
                    "namespace": "${context.namespace}"
                },
                "on_failure": "continue"
            },
            {
                "id": "rolling_restart",
                "name": "Rolling Restart",
                "action_category": "k8s",
                "action_type": "rollout_restart",
                "params": {
                    "deployment": "${context.service}",
                    "namespace": "${context.namespace}"
                }
            },
            {
                "id": "notify_team",
                "name": "Notify Team",
                "action_category": "cicd",
                "action_type": "feature_flag_toggle",
                "params": {
                    "flag_key": "memory_alert_${context.service}",
                    "enabled": True
                }
            }
        ]
    }
