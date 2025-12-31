"""
Database Models - PostgreSQL Schema
Core tables: Users, Subscriptions, Sessions, Actions, Incidents
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

Base = declarative_base()

# ============================================================================
# Enums
# ============================================================================

class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"
    PAST_DUE = "past_due"

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    TRIAL = "trial"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"

class IncidentStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ============================================================================
# Core Tables
# ============================================================================

class User(Base):
    """User accounts - authentication and profile"""
    __tablename__ = "users"
    
    # Primary key
    user_id = Column(String(255), primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False)
    
    # Profile
    full_name = Column(String(255))
    company = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="approved_by_user")
    
    def __repr__(self):
        return f"<User {self.email}>"


class Subscription(Base):
    """
    Subscription records - SOURCE OF TRUTH for feature access
    This is the MOST IMPORTANT table
    """
    __tablename__ = "subscriptions"
    
    # Primary key
    subscription_id = Column(String(255), primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False, unique=True)
    
    # Subscription details
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False, default=SubscriptionPlan.TRIAL)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.TRIALING)
    
    # Trial information
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    
    # Active subscription periods
    subscription_start = Column(DateTime(timezone=True))
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    
    # Payment integration
    payment_provider = Column(String(50))  # stripe, paypal, etc.
    payment_provider_customer_id = Column(String(255), index=True)
    payment_provider_subscription_id = Column(String(255), index=True)
    payment_method_id = Column(String(255))
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime(timezone=True))
    
    # Feature limits (JSON for flexibility)
    feature_limits = Column(JSON, default={
        "max_services": 10,
        "data_retention_days": 30,
        "max_actions_per_day": 100
    })
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_user_status', 'user_id', 'status'),
        Index('idx_trial_end', 'trial_end'),
        Index('idx_period_end', 'current_period_end'),
    )
    
    def is_active_subscription(self) -> bool:
        """Check if subscription allows feature access"""
        return self.status in [SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE]
    
    def days_until_expiry(self) -> int:
        """Calculate days until subscription expires"""
        if self.status == SubscriptionStatus.TRIALING and self.trial_end:
            delta = self.trial_end - datetime.now(timezone.utc)
            return max(0, delta.days)
        elif self.current_period_end:
            delta = self.current_period_end - datetime.now(timezone.utc)
            return max(0, delta.days)
        return 0
    
    def __repr__(self):
        return f"<Subscription {self.subscription_id} - {self.status.value}>"


class Session(Base):
    """User sessions for authentication"""
    __tablename__ = "sessions"
    
    session_id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    
    # Session data
    token = Column(String(512), unique=True, nullable=False, index=True)
    refresh_token = Column(String(512), unique=True, index=True)
    
    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Client info
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user_expires', 'user_id', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<Session {self.session_id}>"


class Service(Base):
    """Services being monitored"""
    __tablename__ = "services"
    
    service_id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    
    # Service details
    name = Column(String(255), nullable=False)
    environment = Column(String(50))  # production, staging, dev
    
    # Status
    status = Column(String(50), default="healthy")
    last_health_check = Column(DateTime(timezone=True))
    
    # Configuration
    config = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    incidents = relationship("Incident", back_populates="service")
    actions = relationship("Action", back_populates="service")
    
    __table_args__ = (
        Index('idx_service_user', 'user_id'),
        Index('idx_service_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Service {self.name}>"


class Incident(Base):
    """Detected incidents"""
    __tablename__ = "incidents"
    
    incident_id = Column(String(255), primary_key=True, index=True)
    service_id = Column(String(255), ForeignKey("services.service_id"), nullable=False)
    
    # Incident details
    status = Column(SQLEnum(IncidentStatus), default=IncidentStatus.ACTIVE, nullable=False)
    severity = Column(SQLEnum(IncidentSeverity), nullable=False)
    
    # Root cause analysis
    root_cause = Column(Text)
    root_cause_confidence = Column(Float)
    ai_reasoning = Column(Text)
    
    # Metrics
    anomaly_count = Column(Integer, default=0)
    customer_impact = Column(String(255))
    
    # Resolution
    resolved_at = Column(DateTime(timezone=True))
    resolution_time_seconds = Column(Integer)
    was_successful = Column(Boolean)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Relationships
    service = relationship("Service", back_populates="incidents")
    actions = relationship("Action", back_populates="incident")
    anomalies = relationship("Anomaly", back_populates="incident")
    
    __table_args__ = (
        Index('idx_incident_service_status', 'service_id', 'status'),
        Index('idx_incident_severity', 'severity'),
        Index('idx_incident_detected', 'detected_at'),
    )
    
    def __repr__(self):
        return f"<Incident {self.incident_id} - {self.severity.value}>"


class Action(Base):
    """Remediation actions (Phase 2/3)"""
    __tablename__ = "actions"
    
    action_id = Column(String(255), primary_key=True, index=True)
    incident_id = Column(String(255), ForeignKey("incidents.incident_id"), nullable=False)
    service_id = Column(String(255), ForeignKey("services.service_id"), nullable=False)
    
    # Action details
    action_type = Column(String(100), nullable=False)
    status = Column(SQLEnum(ActionStatus), default=ActionStatus.PENDING, nullable=False)
    risk = Column(String(20))  # low, medium, high
    
    # Execution
    params = Column(JSON)
    reasoning = Column(Text)
    result = Column(JSON)
    error_message = Column(Text)
    
    # Approval workflow
    proposed_by = Column(String(100))
    approved_by_user_id = Column(String(255), ForeignKey("users.user_id"))
    approval_notes = Column(Text)
    
    # Autonomous execution (Phase 3)
    autonomous_confidence = Column(Float)
    autonomous_reasoning = Column(Text)
    
    # Timestamps
    proposed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    incident = relationship("Incident", back_populates="actions")
    service = relationship("Service", back_populates="actions")
    approved_by_user = relationship("User", back_populates="actions")
    
    __table_args__ = (
        Index('idx_action_status', 'status'),
        Index('idx_action_incident', 'incident_id'),
        Index('idx_action_service', 'service_id'),
        Index('idx_action_proposed', 'proposed_at'),
    )
    
    def __repr__(self):
        return f"<Action {self.action_type} - {self.status.value}>"


class Anomaly(Base):
    """Detected anomalies"""
    __tablename__ = "anomalies"
    
    anomaly_id = Column(String(255), primary_key=True, index=True)
    incident_id = Column(String(255), ForeignKey("incidents.incident_id"))
    service_id = Column(String(255), ForeignKey("services.service_id"), nullable=False)
    
    # Anomaly details
    metric_name = Column(String(255), nullable=False)
    current_value = Column(Float, nullable=False)
    baseline_mean = Column(Float)
    baseline_std_dev = Column(Float)
    z_score = Column(Float)
    deviation_percent = Column(Float)
    severity = Column(SQLEnum(IncidentSeverity), nullable=False)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    incident = relationship("Incident", back_populates="anomalies")
    
    __table_args__ = (
        Index('idx_anomaly_service', 'service_id'),
        Index('idx_anomaly_detected', 'detected_at'),
        Index('idx_anomaly_severity', 'severity'),
    )
    
    def __repr__(self):
        return f"<Anomaly {self.metric_name} - {self.severity.value}>"


class AuditLog(Base):
    """Audit trail for important actions"""
    __tablename__ = "audit_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.user_id"))
    
    # Event details
    event_type = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    
    # Changes
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_event', 'event_type'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.event_type}>"


class ApiKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    api_key_id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    
    # Key details
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20))  # Show first few chars for identification
    
    # Permissions
    scopes = Column(JSON)  # ["read:metrics", "write:actions", etc.]
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    
    # Expiry
    expires_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_apikey_user', 'user_id'),
        Index('idx_apikey_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ApiKey {self.name}>"