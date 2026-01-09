"""
User Suppression Rules API
Allows users to configure their own alert suppression rules
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone

from src.auth import get_current_user
from src.models import User
from src.rate_limiting import limiter

router = APIRouter(prefix="/api/suppression", tags=["Suppression Rules"])


# ============================================================================
# Models
# ============================================================================

class SuppressionRuleCreate(BaseModel):
    """Create a new suppression rule"""
    rule_type: str  # "duplicate", "flapping", "low_actionability", "maintenance"
    enabled: bool = True
    config: Dict = {}  # Type-specific configuration

class SuppressionRuleUpdate(BaseModel):
    """Update suppression rule"""
    enabled: Optional[bool] = None
    config: Optional[Dict] = None

class SuppressionRuleResponse(BaseModel):
    """Suppression rule response"""
    id: str
    rule_type: str
    name: str
    description: str
    enabled: bool
    config: Dict


# ============================================================================
# In-Memory Storage (use database in production)
# ============================================================================

# Default suppression rules for each user
DEFAULT_RULES = [
    {
        "id": "rule_duplicate",
        "rule_type": "duplicate",
        "name": "Duplicate Alert Suppression",
        "description": "Suppress duplicate alerts within time window",
        "enabled": True,
        "config": {
            "window_minutes": 5,
            "description": "5min window"
        }
    },
    {
        "id": "rule_flapping",
        "rule_type": "flapping",
        "name": "Flapping Detection",
        "description": "Detect and aggregate rapidly flapping alerts",
        "enabled": True,
        "config": {
            "threshold_changes": 5,
            "window_minutes": 10,
            "description": "5+ changes/10min"
        }
    },
    {
        "id": "rule_low_actionability",
        "rule_type": "low_actionability",
        "name": "Low Actionability Filter",
        "description": "Suppress alerts with low actionability scores",
        "enabled": True,
        "config": {
            "min_score": 40,
            "description": "<40%"
        }
    },
    {
        "id": "rule_maintenance",
        "rule_type": "maintenance",
        "name": "Maintenance Window",
        "description": "Suppress alerts during scheduled maintenance",
        "enabled": False,
        "config": {
            "services": [],
            "description": "Not scheduled"
        }
    }
]

# User rules storage (user_id -> list of rules)
_user_rules: Dict[str, List[Dict]] = {}


def get_user_rules(user_id: str) -> List[Dict]:
    """Get suppression rules for a user"""
    if user_id not in _user_rules:
        # Initialize with default rules
        import copy
        _user_rules[user_id] = copy.deepcopy(DEFAULT_RULES)
    return _user_rules[user_id]


def save_user_rules(user_id: str, rules: List[Dict]):
    """Save user rules"""
    _user_rules[user_id] = rules


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/rules", response_model=List[SuppressionRuleResponse])
async def get_suppression_rules(
    current_user: User = Depends(get_current_user)
):
    """Get all suppression rules for the current user"""
    rules = get_user_rules(current_user.user_id)
    return rules


@router.put("/rules/{rule_id}")
@limiter.limit("30/minute")  # Rule update rate limit
async def update_suppression_rule(
    request: Request,
    rule_id: str,
    update: SuppressionRuleUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a specific suppression rule"""
    rules = get_user_rules(current_user.user_id)
    
    # Find the rule
    for rule in rules:
        if rule["id"] == rule_id:
            if update.enabled is not None:
                rule["enabled"] = update.enabled
            if update.config is not None:
                rule["config"].update(update.config)
            
            save_user_rules(current_user.user_id, rules)
            return {"success": True, "rule": rule}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Rule {rule_id} not found"
    )


@router.post("/rules/{rule_id}/toggle")
@limiter.limit("30/minute")  # Rule toggle rate limit
async def toggle_suppression_rule(
    request: Request,
    rule_id: str,
    current_user: User = Depends(get_current_user)
):
    """Toggle a suppression rule on/off"""
    rules = get_user_rules(current_user.user_id)
    
    for rule in rules:
        if rule["id"] == rule_id:
            rule["enabled"] = not rule["enabled"]
            save_user_rules(current_user.user_id, rules)
            return {"success": True, "enabled": rule["enabled"]}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Rule {rule_id} not found"
    )


@router.post("/maintenance")
@limiter.limit("10/minute")  # Maintenance window rate limit
async def set_maintenance_window(
    request: Request,
    service: str,
    duration_minutes: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Set a maintenance window for a service"""
    rules = get_user_rules(current_user.user_id)
    
    # Update maintenance rule
    for rule in rules:
        if rule["rule_type"] == "maintenance":
            if "services" not in rule["config"]:
                rule["config"]["services"] = []
            
            # Add this service
            end_time = datetime.now(timezone.utc).isoformat()
            rule["config"]["services"].append({
                "service": service,
                "duration_minutes": duration_minutes,
                "start_time": datetime.now(timezone.utc).isoformat()
            })
            rule["enabled"] = True
            rule["config"]["description"] = f"{len(rule['config']['services'])} service(s)"
            
            save_user_rules(current_user.user_id, rules)
            return {
                "success": True,
                "message": f"Maintenance window set for {service} ({duration_minutes}min)"
            }
    
    return {"success": False, "message": "Maintenance rule not found"}


@router.get("/stats")
async def get_suppression_stats(
    current_user: User = Depends(get_current_user)
):
    """Get suppression statistics"""
    rules = get_user_rules(current_user.user_id)
    
    enabled_count = sum(1 for r in rules if r["enabled"])
    
    return {
        "total_rules": len(rules),
        "enabled_rules": enabled_count,
        "disabled_rules": len(rules) - enabled_count,
        "rules": [
            {
                "id": r["id"],
                "name": r["name"],
                "enabled": r["enabled"],
                "type": r["rule_type"]
            }
            for r in rules
        ]
    }
