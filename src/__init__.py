"""
src/__init__.py - Central Import Configuration

This file ensures all models are properly registered with SQLAlchemy Base
and provides a clean import interface for the rest of the application.

Place this file at: src/__init__.py
"""

# Import Base from database (database.py is in src/ directory)
from .database import Base

# Import all models to register them with Base (models.py is in src/ directory)
from .models import (
    User,
    Subscription,
    Session,
    Service,
    Incident,
    Action,
    Anomaly,
    AuditLog,
    ApiKey,
    # Enums
    SubscriptionStatus,
    SubscriptionPlan,
    ActionStatus,
    IncidentStatus,
    IncidentSeverity
)

__all__ = [
    # Core
    "Base",
    
    # Models
    "User",
    "Subscription",
    "Session",
    "Service",
    "Incident",
    "Action",
    "Anomaly",
    "AuditLog",
    "ApiKey",
    
    # Enums
    "SubscriptionStatus",
    "SubscriptionPlan",
    "ActionStatus",
    "IncidentStatus",
    "IncidentSeverity"
]