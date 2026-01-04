"""
Analytics Package - Enterprise DevOps Automation
"""

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "ActionAnalytics":
        from .action_analytics import ActionAnalytics
        return ActionAnalytics
    elif name == "DecisionLogger":
        from .decision_logger import DecisionLogger
        return DecisionLogger
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["ActionAnalytics", "DecisionLogger"]
