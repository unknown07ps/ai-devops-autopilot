"""
Centralized Logging Configuration for AI DevOps Autopilot

Provides structured logging with:
- JSON format for production
- Colored console output for development
- Log levels based on environment
- Contextual loggers for each module
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import Optional
import json


# ============================================================================
# Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")  # 'console' or 'json'
LOG_FILE = os.getenv("LOG_FILE")  # Optional file path


# ============================================================================
# Custom Formatters
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Add timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format based on level
        if record.levelname in ['ERROR', 'CRITICAL']:
            prefix = f"{color}[{record.levelname}]{self.RESET}"
        else:
            prefix = f"{color}[{record.name}]{self.RESET}"
        
        return f"{timestamp} {prefix} {record.getMessage()}"


class JSONFormatter(logging.Formatter):
    """JSON formatter for production/log aggregation"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


# ============================================================================
# Logger Setup
# ============================================================================

def setup_logging():
    """Configure the root logger with appropriate handlers"""
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    if LOG_FORMAT == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Usage:
        from src.logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.info("Server started")
        logger.error("Connection failed", exc_info=True)
        logger.warning("High memory usage detected")
    """
    return logging.getLogger(name)


# ============================================================================
# Convenience Functions (for gradual migration from print)
# ============================================================================

# Module-level logger for direct imports
_default_logger = None


def _get_default_logger():
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger("deployr")
    return _default_logger


def log_info(message: str, **kwargs):
    """Log an info message (replaces print for info/status)"""
    _get_default_logger().info(message, extra={"extra_fields": kwargs} if kwargs else None)


def log_warning(message: str, **kwargs):
    """Log a warning message"""
    _get_default_logger().warning(message, extra={"extra_fields": kwargs} if kwargs else None)


def log_error(message: str, exc_info: bool = False, **kwargs):
    """Log an error message (replaces print for errors)"""
    _get_default_logger().error(message, exc_info=exc_info, extra={"extra_fields": kwargs} if kwargs else None)


def log_debug(message: str, **kwargs):
    """Log a debug message"""
    _get_default_logger().debug(message, extra={"extra_fields": kwargs} if kwargs else None)


def log_critical(message: str, exc_info: bool = True, **kwargs):
    """Log a critical message"""
    _get_default_logger().critical(message, exc_info=exc_info, extra={"extra_fields": kwargs} if kwargs else None)


# ============================================================================
# Initialize on import
# ============================================================================

# Auto-setup logging when this module is imported
setup_logging()
