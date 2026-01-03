"""
Actions Package - Enterprise DevOps Automation
Exports all action executors and types for the automation platform
"""

from .action_executor import ActionExecutor, ActionType, ActionStatus

# Kubernetes Actions
from .k8s_actions import (
    K8sActionExecutor,
    K8sActionType,
    restart_pod,
    scale_deployment,
    rollout_restart
)

# Cloud Provider Actions
from .cloud_actions import (
    CloudActionExecutor,
    CloudActionType,
    CloudProvider,
    restart_instance,
    create_snapshot
)

# Database Actions
from .database_actions import (
    DatabaseActionExecutor,
    DatabaseActionType,
    DatabaseType,
    kill_slow_queries,
    trigger_backup
)

# CI/CD Actions
from .cicd_actions import (
    CICDActionExecutor,
    CICDActionType,
    CICDProvider,
    trigger_pipeline,
    rollback_deployment,
    toggle_feature
)

__all__ = [
    # Base Action Executor
    "ActionExecutor",
    "ActionType",
    "ActionStatus",
    
    # Kubernetes
    "K8sActionExecutor",
    "K8sActionType",
    "restart_pod",
    "scale_deployment",
    "rollout_restart",
    
    # Cloud
    "CloudActionExecutor",
    "CloudActionType",
    "CloudProvider",
    "restart_instance",
    "create_snapshot",
    
    # Database
    "DatabaseActionExecutor",
    "DatabaseActionType",
    "DatabaseType",
    "kill_slow_queries",
    "trigger_backup",
    
    # CI/CD
    "CICDActionExecutor",
    "CICDActionType",
    "CICDProvider",
    "trigger_pipeline",
    "rollback_deployment",
    "toggle_feature",
]


# Unified action dispatcher
class UnifiedActionDispatcher:
    """
    Unified dispatcher for all action types
    Routes actions to the appropriate executor based on category
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.executors = {
            "base": ActionExecutor(redis_client),
            "k8s": K8sActionExecutor(redis_client),
            "cloud": CloudActionExecutor(redis_client),
            "database": DatabaseActionExecutor(redis_client),
            "cicd": CICDActionExecutor(redis_client),
        }
    
    async def execute(self, category: str, action_type: str, params: dict) -> dict:
        """
        Execute an action through the appropriate executor
        
        Args:
            category: Action category (k8s, cloud, database, cicd)
            action_type: Specific action type
            params: Action parameters
        
        Returns:
            Action result dictionary
        """
        executor = self.executors.get(category)
        if not executor:
            return {
                "success": False,
                "error": f"Unknown category: {category}"
            }
        
        # Map string action type to enum
        action_type_enum = self._get_action_type_enum(category, action_type)
        if not action_type_enum:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type} for category: {category}"
            }
        
        return await executor.execute_action(action_type_enum, params)
    
    def _get_action_type_enum(self, category: str, action_type: str):
        """Map string action type to appropriate enum"""
        type_maps = {
            "k8s": K8sActionType,
            "cloud": CloudActionType,
            "database": DatabaseActionType,
            "cicd": CICDActionType,
        }
        
        type_class = type_maps.get(category)
        if not type_class:
            return None
        
        try:
            return type_class(action_type)
        except ValueError:
            return None
    
    def get_available_actions(self) -> dict:
        """Get all available actions by category"""
        return {
            "k8s": [t.value for t in K8sActionType],
            "cloud": [t.value for t in CloudActionType],
            "database": [t.value for t in DatabaseActionType],
            "cicd": [t.value for t in CICDActionType],
        }
