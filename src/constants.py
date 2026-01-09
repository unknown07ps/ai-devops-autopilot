"""
System Constants and Configuration Values

This module centralizes magic numbers and configuration constants used throughout
the AI DevOps Autopilot system. All values maintain their original defaults.

Usage:
    from src.constants import (
        ALERT_COOLDOWN_SECONDS,
        DEFAULT_PAGINATION_LIMIT,
        ...
    )
"""

import os

# ============================================================================
# TIMEOUTS AND COOLDOWNS
# ============================================================================

# Alert and notification cooldowns
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # 5 minutes

# Action execution timeouts
ACTION_TIMEOUT_SECONDS = int(os.getenv("ACTION_TIMEOUT_SECONDS", "300"))  # 5 minutes
RUNBOOK_TIMEOUT_SECONDS = int(os.getenv("RUNBOOK_TIMEOUT_SECONDS", "1800"))  # 30 minutes
RUNBOOK_STEP_TIMEOUT_SECONDS = int(os.getenv("RUNBOOK_STEP_TIMEOUT_SECONDS", "300"))  # 5 minutes
RUNBOOK_RETRY_DELAY_SECONDS = int(os.getenv("RUNBOOK_RETRY_DELAY_SECONDS", "30"))

# Cooldown between actions on same service
ACTION_COOLDOWN_SECONDS = int(os.getenv("ACTION_COOLDOWN_SECONDS", "300"))  # 5 minutes

# ============================================================================
# LOOKBACK WINDOWS
# ============================================================================

# Incident and log analysis windows
DEFAULT_LOOKBACK_MINUTES = int(os.getenv("DEFAULT_LOOKBACK_MINUTES", "60"))
MAX_LOOKBACK_MINUTES = int(os.getenv("MAX_LOOKBACK_MINUTES", "1440"))  # 24 hours
RECENT_LOGS_WINDOW_MINUTES = int(os.getenv("RECENT_LOGS_WINDOW_MINUTES", "10"))
RECENT_DEPLOYMENTS_WINDOW_MINUTES = int(os.getenv("RECENT_DEPLOYMENTS_WINDOW_MINUTES", "30"))

# Pattern and learning retention
PATTERN_TTL_DAYS = int(os.getenv("PATTERN_TTL_DAYS", "90"))
LOOKBACK_WINDOW_HOURS = int(os.getenv("LOOKBACK_WINDOW_HOURS", "24"))
BASELINE_WINDOW_HOURS = int(os.getenv("BASELINE_WINDOW_HOURS", "168"))  # 7 days
STALE_THRESHOLD_HOURS = int(os.getenv("STALE_THRESHOLD_HOURS", "24"))

# ============================================================================
# PAGINATION AND LIMITS
# ============================================================================

# Default pagination limits
DEFAULT_PAGINATION_LIMIT = int(os.getenv("DEFAULT_PAGINATION_LIMIT", "50"))
DEFAULT_ACTIONS_LIMIT = int(os.getenv("DEFAULT_ACTIONS_LIMIT", "20"))
MAX_ANOMALIES_LIMIT = int(os.getenv("MAX_ANOMALIES_LIMIT", "100"))
MAX_ALERTS_LIMIT = int(os.getenv("MAX_ALERTS_LIMIT", "20"))

# Background processing limits
MAX_PENDING_ACTIONS = int(os.getenv("MAX_PENDING_ACTIONS", "100"))
MAX_OUTCOMES_STORED = int(os.getenv("MAX_OUTCOMES_STORED", "100"))

# ============================================================================
# THRESHOLDS AND CONFIDENCE LEVELS
# ============================================================================

# Confidence thresholds (0-100)
DEFAULT_CONFIDENCE_THRESHOLD = int(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "85"))
MIN_CONFIDENCE_THRESHOLD = int(os.getenv("MIN_CONFIDENCE_THRESHOLD", "50"))
HIGH_CONFIDENCE_THRESHOLD = int(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "90"))

# Incident trigger thresholds
INCIDENT_TRIGGER_THRESHOLD = int(os.getenv("INCIDENT_TRIGGER_THRESHOLD", "10"))

# ============================================================================
# CLOUD AND COST DEFAULTS
# ============================================================================

DEFAULT_COST_LOOKBACK_DAYS = int(os.getenv("DEFAULT_COST_LOOKBACK_DAYS", "30"))

# ============================================================================
# SECURITY AND MASKING
# ============================================================================

MAX_MASK_RECURSION_DEPTH = int(os.getenv("MAX_MASK_RECURSION_DEPTH", "10"))
MIN_TOKEN_LENGTH_FOR_PARTIAL_MASK = int(os.getenv("MIN_TOKEN_LENGTH_FOR_PARTIAL_MASK", "12"))

# ============================================================================
# PERFORMANCE ESTIMATES
# ============================================================================

# Default resolution time estimates (in milliseconds/seconds)
DEFAULT_RESOLUTION_TIME_MS = int(os.getenv("DEFAULT_RESOLUTION_TIME_MS", "1250"))
MANUAL_RESOLUTION_TIME_SECONDS = int(os.getenv("MANUAL_RESOLUTION_TIME_SECONDS", "900"))  # 15 min

# Default estimate for resolution time in seconds
DEFAULT_ESTIMATED_RESOLUTION_SECONDS = int(os.getenv("DEFAULT_ESTIMATED_RESOLUTION_SECONDS", "60"))

# ============================================================================
# REDIS EXPIRATION
# ============================================================================

REDIS_ACTION_EXPIRY_SECONDS = int(os.getenv("REDIS_ACTION_EXPIRY_SECONDS", "86400"))  # 24 hours
REDIS_INCIDENT_EXPIRY_SECONDS = int(os.getenv("REDIS_INCIDENT_EXPIRY_SECONDS", "86400"))  # 24 hours

# ============================================================================
# MAXIMUM CONCURRENT OPERATIONS
# ============================================================================

MAX_CONCURRENT_ACTIONS = int(os.getenv("MAX_CONCURRENT_ACTIONS", "3"))
