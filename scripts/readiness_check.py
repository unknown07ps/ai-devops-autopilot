#!/usr/bin/env python3
"""
Production Readiness Check

Pre-deployment checklist that reports gaps but does NOT block execution.
Run before deployment to verify system is ready for production.

Usage:
    python scripts/readiness_check.py
    python scripts/readiness_check.py --strict  # Fail on critical issues

Exit Codes:
    0 - All checks passed
    1 - Warnings present (non-blocking)
    2 - Critical issues found (only fails with --strict)
"""

import os
import sys
import json
from typing import Dict, List, Tuple
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ReadinessCheck:
    """Production readiness checker"""
    
    def __init__(self):
        self.results: List[Dict] = []
        self.warnings = 0
        self.failures = 0
        self.passed = 0
    
    def check(self, name: str, condition: bool, message: str, severity: str = "warning"):
        """Record a check result"""
        status = "PASS" if condition else severity.upper()
        
        self.results.append({
            "check": name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        if condition:
            self.passed += 1
        elif severity == "critical":
            self.failures += 1
        else:
            self.warnings += 1
    
    def run_all_checks(self):
        """Run all readiness checks"""
        print("\n" + "=" * 60)
        print("  PRODUCTION READINESS CHECK")
        print("=" * 60 + "\n")
        
        self._check_environment()
        self._check_security()
        self._check_database()
        self._check_redis()
        self._check_dependencies()
        self._check_configuration()
        
        return self._print_report()
    
    def _check_environment(self):
        """Check environment configuration"""
        print("📋 Environment Configuration")
        print("-" * 40)
        
        env = os.getenv("ENVIRONMENT", "development")
        self.check(
            "Environment Set",
            env in ["production", "staging"],
            f"ENVIRONMENT={env}" if env else "Not set (defaults to development)",
            "warning"
        )
        
        debug = os.getenv("DEBUG", "false").lower()
        self.check(
            "Debug Disabled",
            debug != "true",
            f"DEBUG={debug}",
            "critical" if debug == "true" else "warning"
        )
        
        log_level = os.getenv("LOG_LEVEL", "INFO")
        self.check(
            "Log Level Appropriate",
            log_level in ["INFO", "WARNING", "ERROR"],
            f"LOG_LEVEL={log_level}",
            "warning"
        )
        print()
    
    def _check_security(self):
        """Check security configuration"""
        print("🔒 Security Configuration")
        print("-" * 40)
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        self.check(
            "JWT Secret Configured",
            len(jwt_secret) >= 32 and jwt_secret != "change-this-in-production",
            "Strong secret set" if len(jwt_secret) >= 32 else "Weak or default secret",
            "critical"
        )
        
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
        self.check(
            "CORS Restricted",
            allowed_origins != "*",
            f"ALLOWED_ORIGINS configured" if allowed_origins != "*" else "WARNING: Allows all origins",
            "warning"
        )
        
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "*")
        self.check(
            "Trusted Hosts Set",
            allowed_hosts != "*",
            f"ALLOWED_HOSTS configured" if allowed_hosts != "*" else "WARNING: Allows all hosts",
            "warning"
        )
        
        razorpay_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        self.check(
            "Payment Webhook Secret",
            len(razorpay_secret) > 0,
            "Webhook secret configured" if razorpay_secret else "Not configured",
            "critical"
        )
        print()
    
    def _check_database(self):
        """Check database configuration"""
        print("🗄️  Database Configuration")
        print("-" * 40)
        
        db_url = os.getenv("DATABASE_URL", "")
        self.check(
            "Database URL Set",
            len(db_url) > 0,
            "DATABASE_URL configured" if db_url else "Not configured",
            "critical"
        )
        
        if db_url:
            self.check(
                "Using SSL",
                "sslmode=require" in db_url or "ssl=true" in db_url.lower(),
                "SSL enabled" if "ssl" in db_url.lower() else "SSL not detected",
                "warning"
            )
        print()
    
    def _check_redis(self):
        """Check Redis configuration"""
        print("📦 Redis Configuration")
        print("-" * 40)
        
        redis_url = os.getenv("REDIS_URL", "")
        self.check(
            "Redis URL Set",
            len(redis_url) > 0,
            "REDIS_URL configured" if redis_url else "Not configured",
            "critical"
        )
        
        # Try to connect
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url)
                client.ping()
                self.check("Redis Connection", True, "Connection successful")
            except Exception as e:
                self.check("Redis Connection", False, f"Failed: {e}", "critical")
        print()
    
    def _check_dependencies(self):
        """Check required dependencies"""
        print("📚 Dependencies")
        print("-" * 40)
        
        dependencies = [
            ("fastapi", "FastAPI"),
            ("redis", "Redis Client"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pydantic", "Pydantic"),
            ("httpx", "HTTPX"),
        ]
        
        for module, name in dependencies:
            try:
                __import__(module)
                self.check(name, True, "Installed")
            except ImportError:
                self.check(name, False, "Not installed", "critical")
        
        # Optional dependencies
        optional = [
            ("prometheus_client", "Prometheus Metrics"),
            ("slowapi", "Rate Limiting"),
        ]
        
        for module, name in optional:
            try:
                __import__(module)
                self.check(name, True, "Installed")
            except ImportError:
                self.check(name, False, "Not installed (optional)", "warning")
        print()
    
    def _check_configuration(self):
        """Check application configuration files"""
        print("⚙️  Configuration Files")
        print("-" * 40)
        
        files = [
            (".env", "Environment File"),
            ("docker-compose.yml", "Docker Compose"),
            ("requirements.txt", "Dependencies"),
        ]
        
        for file, name in files:
            exists = os.path.exists(file)
            self.check(name, exists, "Present" if exists else "Missing", "warning")
        print()
    
    def _print_report(self) -> int:
        """Print final report and return exit code"""
        print("=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"\n  ✅ Passed:   {self.passed}")
        print(f"  ⚠️  Warnings: {self.warnings}")
        print(f"  ❌ Critical: {self.failures}")
        
        if self.failures > 0:
            print("\n  ⛔ PRODUCTION READINESS: FAILED")
            print("     Address critical issues before deployment.")
            return 2
        elif self.warnings > 0:
            print("\n  ⚠️  PRODUCTION READINESS: WARNINGS")
            print("     Review warnings before deployment.")
            return 1
        else:
            print("\n  ✅ PRODUCTION READINESS: PASSED")
            return 0


def main():
    strict = "--strict" in sys.argv
    
    checker = ReadinessCheck()
    exit_code = checker.run_all_checks()
    
    # Only fail on critical issues if strict mode
    if strict and exit_code == 2:
        sys.exit(2)
    elif exit_code == 2:
        print("\n  Run with --strict to fail on critical issues")
    
    sys.exit(0 if exit_code != 2 else 0)


if __name__ == "__main__":
    main()
