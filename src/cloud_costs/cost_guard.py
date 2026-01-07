"""
Cost Guard - Cloud Cost Protection System
Prevents actions that could unknowingly increase cloud costs
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json


# Action types categorized by cost impact
HIGH_COST_ACTIONS = {
    'scale_up': {'impact': 'high', 'est_cost_per_hour': 50, 'warning': 'Scaling up will increase resource costs'},
    'create_instance': {'impact': 'high', 'est_cost_per_hour': 25, 'warning': 'Creating new instances incurs ongoing costs'},
    'start_service': {'impact': 'medium', 'est_cost_per_hour': 15, 'warning': 'Starting services will add to your cloud bill'},
    'enable_feature': {'impact': 'medium', 'est_cost_per_hour': 10, 'warning': 'Some features have additional costs'},
    'add_storage': {'impact': 'high', 'est_cost_per_hour': 5, 'warning': 'Storage costs accumulate over time'},
    'increase_replicas': {'impact': 'high', 'est_cost_per_hour': 40, 'warning': 'More replicas mean higher compute costs'},
    'upgrade_tier': {'impact': 'critical', 'est_cost_per_hour': 100, 'warning': 'Tier upgrades significantly increase costs'},
    'enable_logging': {'impact': 'low', 'est_cost_per_hour': 2, 'warning': 'Logging can add storage costs'},
    'add_monitoring': {'impact': 'low', 'est_cost_per_hour': 3, 'warning': 'Monitoring services have usage-based costs'},
}

# Actions that reduce costs (safe)
COST_REDUCING_ACTIONS = [
    'scale_down', 'terminate', 'stop_service', 'delete_instance',
    'reduce_replicas', 'downgrade_tier', 'disable_feature',
    'cleanup', 'optimize', 'rightsize'
]

# Actions that are cost-neutral
NEUTRAL_ACTIONS = [
    'restart', 'rollback', 'investigate', 'health_check',
    'update_config', 'patch', 'rotate_credentials'
]


class CostGuard:
    """
    Cost protection system that assesses and warns about
    actions that could increase cloud costs
    """
    
    def __init__(self):
        self.cost_threshold_warning = 10  # $/hour triggers warning
        self.cost_threshold_block = 50    # $/hour requires explicit approval
        self.monthly_budget = 45000       # Default monthly budget
        
    def assess_action_cost_impact(self, action_type: str, service: str = None, 
                                   params: dict = None) -> Dict[str, Any]:
        """
        Assess the cost impact of a proposed action
        
        Returns:
            Dictionary with cost assessment details
        """
        action_lower = action_type.lower().replace(' ', '_').replace('-', '_')
        
        # Check if it's a cost-reducing action
        for safe_action in COST_REDUCING_ACTIONS:
            if safe_action in action_lower:
                return {
                    'action': action_type,
                    'cost_impact': 'savings',
                    'impact_level': 'positive',
                    'requires_approval': False,
                    'blocked': False,
                    'message': 'This action may reduce your cloud costs',
                    'estimated_savings_per_hour': 20,  # Estimated
                    'badge_color': 'green'
                }
        
        # Check if it's a neutral action
        for neutral_action in NEUTRAL_ACTIONS:
            if neutral_action in action_lower:
                return {
                    'action': action_type,
                    'cost_impact': 'neutral',
                    'impact_level': 'none',
                    'requires_approval': False,
                    'blocked': False,
                    'message': 'This action has no cost impact',
                    'estimated_cost_per_hour': 0,
                    'badge_color': 'gray'
                }
        
        # Check for high-cost actions
        for cost_action, details in HIGH_COST_ACTIONS.items():
            if cost_action in action_lower or action_lower in cost_action:
                est_cost = details['est_cost_per_hour']
                
                return {
                    'action': action_type,
                    'cost_impact': details['impact'],
                    'impact_level': details['impact'],
                    'requires_approval': est_cost >= self.cost_threshold_warning,
                    'blocked': est_cost >= self.cost_threshold_block,
                    'message': details['warning'],
                    'estimated_cost_per_hour': est_cost,
                    'estimated_cost_per_day': est_cost * 24,
                    'estimated_cost_per_month': est_cost * 24 * 30,
                    'badge_color': 'red' if details['impact'] == 'critical' else 
                                  'orange' if details['impact'] == 'high' else 'yellow'
                }
        
        # Default: unknown action, treat as medium risk
        return {
            'action': action_type,
            'cost_impact': 'unknown',
            'impact_level': 'medium',
            'requires_approval': True,
            'blocked': False,
            'message': 'Unable to assess cost impact - manual review recommended',
            'estimated_cost_per_hour': None,
            'badge_color': 'gray'
        }
    
    def check_budget_impact(self, estimated_monthly_cost: float) -> Dict[str, Any]:
        """
        Check if an action would exceed budget thresholds
        """
        budget_percent = (estimated_monthly_cost / self.monthly_budget) * 100
        
        if budget_percent > 10:
            return {
                'exceeds_threshold': True,
                'budget_impact_percent': round(budget_percent, 1),
                'warning': f'This action would use {budget_percent:.1f}% of your monthly budget',
                'severity': 'critical' if budget_percent > 25 else 'high'
            }
        
        return {
            'exceeds_threshold': False,
            'budget_impact_percent': round(budget_percent, 1),
            'warning': None,
            'severity': 'low'
        }
    
    def get_action_recommendations(self, action_type: str) -> List[str]:
        """
        Get cost-saving recommendations for an action
        """
        recommendations = []
        action_lower = action_type.lower()
        
        if 'scale' in action_lower and 'up' in action_lower:
            recommendations.extend([
                'Consider using auto-scaling instead of manual scale-up',
                'Set a scale-down schedule to reduce costs during off-hours',
                'Review if spot/preemptible instances would work'
            ])
        
        if 'instance' in action_lower or 'create' in action_lower:
            recommendations.extend([
                'Use reserved instances for predictable workloads',
                'Consider smaller instance types first',
                'Enable auto-shutdown for dev/test instances'
            ])
        
        if 'storage' in action_lower:
            recommendations.extend([
                'Use lifecycle policies to move old data to cheaper tiers',
                'Enable compression to reduce storage costs',
                'Review data retention policies'
            ])
            
        return recommendations


# Singleton instance
_cost_guard = None

def get_cost_guard() -> CostGuard:
    """Get or create the CostGuard singleton"""
    global _cost_guard
    if _cost_guard is None:
        _cost_guard = CostGuard()
    return _cost_guard


def assess_action(action_type: str, service: str = None, params: dict = None) -> Dict[str, Any]:
    """
    Convenience function to assess an action's cost impact
    """
    guard = get_cost_guard()
    assessment = guard.assess_action_cost_impact(action_type, service, params)
    assessment['recommendations'] = guard.get_action_recommendations(action_type)
    return assessment
