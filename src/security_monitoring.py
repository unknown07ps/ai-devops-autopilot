"""
Security Monitoring & Intrusion Detection Module
Detects and alerts on suspicious authentication and access behavior
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import os

try:
    import redis
except ImportError:
    redis = None


class SecurityMonitor:
    """
    Monitors security events and detects suspicious behavior patterns:
    - Failed login attempts (brute force detection)
    - Unusual access patterns
    - Suspicious IP addresses
    - Privilege escalation attempts
    - Session anomalies
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        
        # Thresholds for anomaly detection
        self.config = {
            # Failed login thresholds
            "max_failed_logins_per_ip": int(os.getenv("MAX_FAILED_LOGINS_IP", "5")),
            "max_failed_logins_per_user": int(os.getenv("MAX_FAILED_LOGINS_USER", "3")),
            "failed_login_window_minutes": 15,
            
            # Rate limiting
            "max_requests_per_minute": int(os.getenv("MAX_REQUESTS_MINUTE", "100")),
            "max_auth_attempts_per_hour": int(os.getenv("MAX_AUTH_HOUR", "20")),
            
            # Session anomalies
            "max_concurrent_sessions": int(os.getenv("MAX_SESSIONS", "5")),
            "session_geo_change_alert": True,
            
            # Lockout
            "lockout_duration_minutes": int(os.getenv("LOCKOUT_MINUTES", "30")),
            "auto_lockout_enabled": os.getenv("AUTO_LOCKOUT", "true").lower() == "true"
        }
        
        # In-memory tracking (fallback if Redis not available)
        self._failed_logins_by_ip = defaultdict(list)
        self._failed_logins_by_user = defaultdict(list)
        self._locked_ips = {}
        self._locked_users = {}
        self._security_events = []
    
    # =========================================================================
    # Failed Login Detection
    # =========================================================================
    
    def record_failed_login(
        self,
        email: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        reason: str = "invalid_credentials"
    ) -> Dict:
        """
        Record a failed login attempt and check for brute force
        
        Returns:
            {
                "blocked": bool,
                "reason": str,
                "attempts": int,
                "lockout_remaining": int (seconds)
            }
        """
        now = datetime.now(timezone.utc)
        
        event = {
            "type": "failed_login",
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "reason": reason,
            "timestamp": now.isoformat()
        }
        
        # Store event
        self._store_security_event(event)
        
        # Track by IP
        self._failed_logins_by_ip[ip_address].append(now)
        self._cleanup_old_attempts(self._failed_logins_by_ip[ip_address])
        
        # Track by user
        self._failed_logins_by_user[email].append(now)
        self._cleanup_old_attempts(self._failed_logins_by_user[email])
        
        # Check for brute force
        ip_attempts = len(self._failed_logins_by_ip[ip_address])
        user_attempts = len(self._failed_logins_by_user[email])
        
        blocked = False
        block_reason = None
        
        # Check IP threshold
        if ip_attempts >= self.config["max_failed_logins_per_ip"]:
            blocked = True
            block_reason = f"Too many failed attempts from IP ({ip_attempts})"
            self._trigger_lockout(ip_address=ip_address)
            self._alert_security_event("brute_force_ip", {
                "ip_address": ip_address,
                "attempts": ip_attempts
            })
        
        # Check user threshold
        if user_attempts >= self.config["max_failed_logins_per_user"]:
            blocked = True
            block_reason = f"Too many failed attempts for account ({user_attempts})"
            self._trigger_lockout(email=email)
            self._alert_security_event("brute_force_user", {
                "email": email,
                "attempts": user_attempts
            })
        
        return {
            "blocked": blocked,
            "reason": block_reason,
            "ip_attempts": ip_attempts,
            "user_attempts": user_attempts,
            "lockout_remaining": self._get_lockout_remaining(ip_address, email)
        }
    
    def is_blocked(self, ip_address: str = None, email: str = None) -> tuple:
        """
        Check if an IP or user is currently blocked
        
        Returns:
            (is_blocked: bool, reason: str, remaining_seconds: int)
        """
        now = datetime.now(timezone.utc)
        
        # Check IP lockout
        if ip_address and ip_address in self._locked_ips:
            lockout_until = self._locked_ips[ip_address]
            if now < lockout_until:
                remaining = int((lockout_until - now).total_seconds())
                return True, "IP temporarily blocked", remaining
            else:
                del self._locked_ips[ip_address]
        
        # Check user lockout
        if email and email in self._locked_users:
            lockout_until = self._locked_users[email]
            if now < lockout_until:
                remaining = int((lockout_until - now).total_seconds())
                return True, "Account temporarily locked", remaining
            else:
                del self._locked_users[email]
        
        return False, None, 0
    
    def record_successful_login(
        self,
        user_id: str,
        email: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """Record successful login and clear failed attempts"""
        # Clear failed attempts for this user
        if email in self._failed_logins_by_user:
            del self._failed_logins_by_user[email]
        
        # Store success event for audit
        event = {
            "type": "successful_login",
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._store_security_event(event)
        
        # Check for suspicious login (new IP, unusual time, etc.)
        self._check_login_anomalies(user_id, email, ip_address, user_agent)
    
    # =========================================================================
    # Suspicious Activity Detection
    # =========================================================================
    
    def detect_privilege_escalation(
        self,
        user_id: str,
        action: str,
        resource: str,
        ip_address: str
    ):
        """Detect and alert on privilege escalation attempts"""
        suspicious_actions = [
            "modify_subscription",
            "admin_access",
            "superuser_action",
            "bypass_auth",
            "modify_permissions"
        ]
        
        if any(sa in action.lower() for sa in suspicious_actions):
            event = {
                "type": "privilege_escalation_attempt",
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "ip_address": ip_address,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "high"
            }
            self._store_security_event(event)
            self._alert_security_event("privilege_escalation", event)
    
    def detect_unusual_access(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        ip_address: str
    ):
        """Detect unusual API access patterns"""
        sensitive_endpoints = [
            "/api/auth/admin",
            "/api/v3/autonomous/emergency",
            "/api/cloud/connect",
            "/api/subscription/upgrade"
        ]
        
        if any(se in endpoint for se in sensitive_endpoints):
            event = {
                "type": "sensitive_access",
                "user_id": user_id,
                "endpoint": endpoint,
                "method": method,
                "ip_address": ip_address,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._store_security_event(event)
    
    # =========================================================================
    # Session Anomaly Detection
    # =========================================================================
    
    def check_session_anomaly(
        self,
        user_id: str,
        session_id: str,
        ip_address: str,
        user_agent: str,
        previous_ip: Optional[str] = None
    ) -> Dict:
        """
        Check for session anomalies like:
        - IP address changes
        - User agent changes
        - Concurrent session limits
        """
        anomalies = []
        
        # Check IP change
        if previous_ip and previous_ip != ip_address:
            anomalies.append({
                "type": "ip_change",
                "previous": previous_ip,
                "current": ip_address
            })
            
            if self.config["session_geo_change_alert"]:
                self._alert_security_event("session_ip_change", {
                    "user_id": user_id,
                    "session_id": session_id,
                    "previous_ip": previous_ip,
                    "new_ip": ip_address
                })
        
        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomalies": anomalies
        }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _cleanup_old_attempts(self, attempts: List[datetime]):
        """Remove attempts older than the tracking window"""
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=self.config["failed_login_window_minutes"]
        )
        attempts[:] = [a for a in attempts if a > cutoff]
    
    def _trigger_lockout(self, ip_address: str = None, email: str = None):
        """Trigger temporary lockout"""
        if not self.config["auto_lockout_enabled"]:
            return
        
        lockout_until = datetime.now(timezone.utc) + timedelta(
            minutes=self.config["lockout_duration_minutes"]
        )
        
        if ip_address:
            self._locked_ips[ip_address] = lockout_until
            print(f"[SECURITY] ⚠️ IP locked: {ip_address} until {lockout_until}")
        
        if email:
            self._locked_users[email] = lockout_until
            print(f"[SECURITY] ⚠️ User locked: {email} until {lockout_until}")
    
    def _get_lockout_remaining(self, ip_address: str, email: str) -> int:
        """Get remaining lockout time in seconds"""
        now = datetime.now(timezone.utc)
        remaining = 0
        
        if ip_address in self._locked_ips:
            remaining = max(remaining, 
                int((self._locked_ips[ip_address] - now).total_seconds()))
        
        if email in self._locked_users:
            remaining = max(remaining,
                int((self._locked_users[email] - now).total_seconds()))
        
        return max(0, remaining)
    
    def _store_security_event(self, event: Dict):
        """Store security event for audit"""
        # Add to in-memory list
        self._security_events.append(event)
        if len(self._security_events) > 1000:
            self._security_events = self._security_events[-1000:]
        
        # Store in Redis if available
        if self.redis:
            try:
                self.redis.lpush("security_events", json.dumps(event))
                self.redis.ltrim("security_events", 0, 9999)  # Keep last 10k events
            except Exception as e:
                print(f"[SECURITY] Failed to store event in Redis: {e}")
        
        # Log to console
        event_type = event.get("type", "unknown")
        print(f"[SECURITY] Event: {event_type} - {event.get('ip_address', 'N/A')}")
    
    def _alert_security_event(self, alert_type: str, details: Dict):
        """Send security alert (integrate with notification system)"""
        alert = {
            "alert_type": alert_type,
            "severity": details.get("severity", "medium"),
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store alert
        if self.redis:
            try:
                self.redis.lpush("security_alerts", json.dumps(alert))
                self.redis.ltrim("security_alerts", 0, 999)
            except (redis.RedisError, Exception) as e:
                print(f"[SECURITY] Error storing alert: {e}")
        
        # Log prominently
        print(f"[SECURITY ALERT] 🚨 {alert_type}")
        print(f"  Details: {json.dumps(details, indent=2)}")
        
        # TODO: Integrate with notification system
        # send_slack_alert(alert)
        # send_email_alert(alert)
    
    def _check_login_anomalies(
        self,
        user_id: str,
        email: str,
        ip_address: str,
        user_agent: str
    ):
        """Check for anomalies in successful login"""
        # Could check:
        # - Login from new IP
        # - Login at unusual time
        # - Login from new device/browser
        pass
    
    # =========================================================================
    # API Methods for Dashboard
    # =========================================================================
    
    def get_security_stats(self) -> Dict:
        """Get security monitoring statistics"""
        now = datetime.now(timezone.utc)
        
        # Count recent events by type
        event_counts = defaultdict(int)
        recent_cutoff = now - timedelta(hours=24)
        
        for event in self._security_events:
            event_time = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            )
            if event_time > recent_cutoff:
                event_counts[event["type"]] += 1
        
        return {
            "total_events_24h": sum(event_counts.values()),
            "events_by_type": dict(event_counts),
            "locked_ips": len(self._locked_ips),
            "locked_users": len(self._locked_users),
            "active_tracking": {
                "ips_tracked": len(self._failed_logins_by_ip),
                "users_tracked": len(self._failed_logins_by_user)
            },
            "config": self.config
        }
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent security alerts"""
        if self.redis:
            try:
                alerts = self.redis.lrange("security_alerts", 0, limit - 1)
                return [json.loads(a) for a in alerts]
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"[SECURITY] Error getting alerts: {e}")
        
        return []
    
    def clear_lockout(self, ip_address: str = None, email: str = None):
        """Manually clear a lockout (admin action)"""
        if ip_address and ip_address in self._locked_ips:
            del self._locked_ips[ip_address]
            print(f"[SECURITY] Lockout cleared for IP: {ip_address}")
        
        if email and email in self._locked_users:
            del self._locked_users[email]
            print(f"[SECURITY] Lockout cleared for user: {email}")


# Global instance
security_monitor = None


def get_security_monitor(redis_client=None) -> SecurityMonitor:
    """Get or create security monitor instance"""
    global security_monitor
    if security_monitor is None:
        security_monitor = SecurityMonitor(redis_client)
    return security_monitor
