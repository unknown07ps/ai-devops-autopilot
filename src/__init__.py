"""
src package initialization
Fixed import errors
"""

# Import database components
from .database import engine, SessionLocal, get_db, get_db_context, init_db

# Import models - Base is defined in models.py, not database.py
from .models import Base, User, Subscription, Session, Service, Incident, Action, Anomaly

# Import authentication
from .auth import (
    get_current_user,
    get_current_active_subscription,
    require_superuser,
    create_user,
    authenticate_user,
    hash_password,
    verify_password
)

# Import subscription service
from .subscription_service import (
    create_trial_subscription,
    upgrade_to_paid,
    check_feature_access,
    get_usage_limits,
    check_subscription_expiry
)

# Import autonomous executor
from .autonomous_executor import AutonomousExecutor, ExecutionMode

__all__ = [
    # Database
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_context',
    'init_db',
    
    # Models
    'Base',
    'User',
    'Subscription',
    'Session',
    'Service',
    'Incident',
    'Action',
    'Anomaly',
    
    # Auth
    'get_current_user',
    'get_current_active_subscription',
    'require_superuser',
    'create_user',
    'authenticate_user',
    'hash_password',
    'verify_password',
    
    # Subscription
    'create_trial_subscription',
    'upgrade_to_paid',
    'check_feature_access',
    'get_usage_limits',
    'check_subscription_expiry',
    
    # Autonomous Executor
    'AutonomousExecutor',
    'ExecutionMode',
]