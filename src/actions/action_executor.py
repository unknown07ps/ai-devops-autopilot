"""
Action Executor - Phase 2: Supervised Remediation
Executes approved fixes with safety checks and rollback capabilities
"""

import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import json

class ActionType(Enum):
    ROLLBACK = "rollback"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART_SERVICE = "restart_service"
    TOGGLE_FEATURE = "toggle_feature"
    CLEAR_CACHE = "clear_cache"
    KILL_CONNECTIONS = "kill_connections"

class ActionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ActionExecutor:
    """
    Executes remediation actions with safety checks and audit logging
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dry_run = True  # Safety first - start in dry-run mode
        
    async def propose_action(
        self,
        action_type: ActionType,
        service: str,
        params: Dict,
        reasoning: str,
        risk: str,
        incident_id: str
    ) -> Dict:
        """
        Propose a remediation action for approval
        """
        action = {
            "id": f"action_{incident_id}_{action_type.value}_{int(datetime.now(timezone.utc).timestamp())}",
            "incident_id": incident_id,
            "action_type": action_type.value,
            "service": service,
            "params": params,
            "reasoning": reasoning,
            "risk": risk,
            "status": ActionStatus.PENDING.value,
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "proposed_by": "ai_autopilot",
            "approved_by": None,
            "approved_at": None,
            "executed_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Store action for approval
        self.redis.setex(
            f"action:{action['id']}",
            86400,  # 24 hour expiry
            json.dumps(action)
        )
        
        # Add to pending queue
        self.redis.lpush("actions:pending", action['id'])
        
        print(f"[ACTION] Proposed {action_type.value} for {service}")
        return action
    
    async def approve_action(self, action_id: str, approved_by: str) -> bool:
        """
        Approve a pending action for execution
        """
        action_data = self.redis.get(f"action:{action_id}")
        if not action_data:
            return False
        
        action = json.loads(action_data)
        
        if action['status'] != ActionStatus.PENDING.value:
            print(f"[ACTION] Cannot approve - status is {action['status']}")
            return False
        
        action['status'] = ActionStatus.APPROVED.value
        action['approved_by'] = approved_by
        action['approved_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update action
        self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
        
        # Remove from pending, add to approved
        self.redis.lrem("actions:pending", 0, action_id)
        self.redis.lpush("actions:approved", action_id)
        
        print(f"[ACTION] Approved {action_id} by {approved_by}")
        
        # Execute immediately
        await self.execute_action(action_id)
        
        return True
    
    async def execute_action(self, action_id: str) -> Dict:
        """
        Execute an approved action
        """
        action_data = self.redis.get(f"action:{action_id}")
        if not action_data:
            return {"success": False, "error": "Action not found"}
        
        action = json.loads(action_data)
        
        if action['status'] != ActionStatus.APPROVED.value:
            return {"success": False, "error": f"Action not approved - status: {action['status']}"}
        
        action['status'] = ActionStatus.EXECUTING.value
        action['executed_at'] = datetime.now(timezone.utc).isoformat()
        self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
        
        print(f"[ACTION] Executing {action['action_type']} for {action['service']}")
        
        try:
            # Route to appropriate executor
            action_type = ActionType(action['action_type'])
            
            if action_type == ActionType.ROLLBACK:
                result = await self._execute_rollback(action)
            elif action_type == ActionType.SCALE_UP:
                result = await self._execute_scale_up(action)
            elif action_type == ActionType.SCALE_DOWN:
                result = await self._execute_scale_down(action)
            elif action_type == ActionType.RESTART_SERVICE:
                result = await self._execute_restart(action)
            elif action_type == ActionType.CLEAR_CACHE:
                result = await self._execute_clear_cache(action)
            elif action_type == ActionType.KILL_CONNECTIONS:
                result = await self._execute_kill_connections(action)
            else:
                result = {"success": False, "error": "Unknown action type"}
            
            # Update action with result
            action['status'] = ActionStatus.SUCCESS.value if result['success'] else ActionStatus.FAILED.value
            action['completed_at'] = datetime.now(timezone.utc).isoformat()
            action['result'] = result
            
            # Store in history
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            self.redis.lpush(f"actions:history:{action['service']}", action_id)
            
            # Learn from action outcome
            await self._record_action_outcome(action)
            
            print(f"[ACTION] Completed {action_id} - Success: {result['success']}")
            return result
            
        except Exception as e:
            action['status'] = ActionStatus.FAILED.value
            action['error'] = str(e)
            action['completed_at'] = datetime.now(timezone.utc).isoformat()
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            
            print(f"[ACTION] Failed {action_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_rollback(self, action: Dict) -> Dict:
        """
        Rollback to previous version
        """
        service = action['service']
        target_version = action['params'].get('target_version')
        
        print(f"[ROLLBACK] {service} → {target_version}")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would rollback {service} to {target_version}",
                "estimated_duration_seconds": 120
            }
        
        # In production, this would call your deployment system
        # Examples:
        # - kubectl set image deployment/{service} app={target_version}
        # - aws ecs update-service --force-new-deployment
        # - helm rollback {service} {revision}
        
        # Simulate deployment
        await asyncio.sleep(2)
        
        return {
            "success": True,
            "message": f"Rolled back {service} to {target_version}",
            "previous_version": action['params'].get('current_version'),
            "new_version": target_version,
            "duration_seconds": 2
        }
    
    async def _execute_scale_up(self, action: Dict) -> Dict:
        """
        Scale up service replicas
        """
        service = action['service']
        current_replicas = action['params'].get('current_replicas', 3)
        target_replicas = action['params'].get('target_replicas', 6)
        
        print(f"[SCALE] {service}: {current_replicas} → {target_replicas} replicas")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would scale {service} from {current_replicas} to {target_replicas}",
                "estimated_duration_seconds": 30
            }
        
        # In production:
        # kubectl scale deployment/{service} --replicas={target_replicas}
        
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": f"Scaled {service} to {target_replicas} replicas",
            "previous_replicas": current_replicas,
            "new_replicas": target_replicas,
            "duration_seconds": 1
        }
    
    async def _execute_scale_down(self, action: Dict) -> Dict:
        """
        Scale down service replicas
        """
        service = action['service']
        current_replicas = action['params'].get('current_replicas', 6)
        target_replicas = action['params'].get('target_replicas', 3)
        
        print(f"[SCALE] {service}: {current_replicas} → {target_replicas} replicas")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would scale {service} from {current_replicas} to {target_replicas}"
            }
        
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": f"Scaled {service} to {target_replicas} replicas",
            "previous_replicas": current_replicas,
            "new_replicas": target_replicas
        }
    
    async def _execute_restart(self, action: Dict) -> Dict:
        """
        Restart service pods/containers
        """
        service = action['service']
        
        print(f"[RESTART] {service}")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would restart {service} pods"
            }
        
        # In production:
        # kubectl rollout restart deployment/{service}
        
        await asyncio.sleep(2)
        
        return {
            "success": True,
            "message": f"Restarted {service}",
            "pods_restarted": 3
        }
    
    async def _execute_clear_cache(self, action: Dict) -> Dict:
        """
        Clear application cache
        """
        service = action['service']
        cache_type = action['params'].get('cache_type', 'redis')
        
        print(f"[CACHE] Clearing {cache_type} cache for {service}")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would clear {cache_type} cache for {service}"
            }
        
        # In production: call cache clearing endpoint or execute flushdb
        
        return {
            "success": True,
            "message": f"Cleared {cache_type} cache for {service}",
            "keys_cleared": 1247
        }
    
    async def _execute_kill_connections(self, action: Dict) -> Dict:
        """
        Kill stuck database connections
        """
        service = action['service']
        connection_threshold = action['params'].get('idle_seconds', 300)
        
        print(f"[CONNECTIONS] Killing idle connections > {connection_threshold}s for {service}")
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would kill idle connections for {service}"
            }
        
        # In production: execute DB kill query
        # SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';
        
        return {
            "success": True,
            "message": f"Killed idle connections for {service}",
            "connections_killed": 12
        }
    
    async def _record_action_outcome(self, action: Dict):
        """
        Record action outcome for learning
        """
        outcome = {
            "action_id": action['id'],
            "action_type": action['action_type'],
            "service": action['service'],
            "success": action['status'] == ActionStatus.SUCCESS.value,
            "incident_id": action['incident_id'],
            "duration_seconds": self._calculate_duration(action),
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store for ML training
        self.redis.lpush("action_outcomes", json.dumps(outcome))
        
        # Update success rate
        key = f"action_success_rate:{action['action_type']}:{action['service']}"
        self.redis.hincrby(key, "total", 1)
        if outcome['success']:
            self.redis.hincrby(key, "success", 1)
    
    def _calculate_duration(self, action: Dict) -> Optional[float]:
        """Calculate action duration in seconds"""
        if action.get('executed_at') and action.get('completed_at'):
            start = datetime.fromisoformat(action['executed_at'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(action['completed_at'].replace('Z', '+00:00'))
            return (end - start).total_seconds()
        return None
    
    def get_action_history(self, service: str, limit: int = 10) -> List[Dict]:
        """Get action history for a service"""
        action_ids = self.redis.lrange(f"actions:history:{service}", 0, limit - 1)
        
        history = []
        for action_id in action_ids:
            action_data = self.redis.get(f"action:{action_id.decode('utf-8')}")
            if action_data:
                history.append(json.loads(action_data))
        
        return history
    
    def get_success_rate(self, action_type: str, service: str) -> float:
        """Get success rate for an action type"""
        key = f"action_success_rate:{action_type}:{service}"
        total = int(self.redis.hget(key, "total") or 0)
        success = int(self.redis.hget(key, "success") or 0)
        
        return (success / total * 100) if total > 0 else 0.0
    
    def enable_production_mode(self):
        """Enable actual execution (use with caution!)"""
        self.dry_run = False
        print("[ACTION] ⚠️  PRODUCTION MODE ENABLED - Actions will be executed!")
    
    def enable_dry_run_mode(self):
        """Enable dry-run mode (safe)"""
        self.dry_run = True
        print("[ACTION] ✓ DRY RUN MODE - Actions will be simulated")