#!/usr/bin/env python3
"""
AI DevOps Autopilot - System Integrity Test Script
Tests all critical components, endpoints, and integrations
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = f"test_{int(time.time())}@example.com"
TEST_PASSWORD = "deployr1374"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_test(name: str):
    print(f"{Colors.YELLOW}[TEST]{Colors.END} {name}...", end=" ")

def print_pass(message: str = "PASSED"):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_fail(message: str = "FAILED"):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {message}")

# Test Results Tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}

def run_test(test_name: str, test_func):
    """Run a test and track results"""
    print_test(test_name)
    try:
        result, message = test_func()
        if result:
            print_pass(message)
            test_results["passed"] += 1
            return True
        else:
            print_fail(message)
            test_results["failed"] += 1
            test_results["errors"].append(f"{test_name}: {message}")
            return False
    except Exception as e:
        print_fail(f"Exception: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{test_name}: {str(e)}")
        return False

# ============================================================================
# Test Functions
# ============================================================================

def test_health_check() -> Tuple[bool, str]:
    """Test basic health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        if data.get("status") in ["healthy", "degraded"]:
            return True, f"Status: {data['status']}"
    return False, f"Status code: {response.status_code}"

def test_database_health() -> Tuple[bool, str]:
    """Test database connectivity"""
    response = requests.get(f"{BASE_URL}/health/database")
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "healthy":
            return True, f"Connection active, {data['statistics']['users']} users"
    return False, f"Database unhealthy"

def test_redis_connection() -> Tuple[bool, str]:
    """Test Redis connectivity through health check"""
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        redis_status = data.get("components", {}).get("redis")
        if redis_status == "healthy":
            return True, "Redis connected"
    return False, "Redis connection failed"

def test_user_registration() -> Tuple[bool, str]:
    """Test user registration flow"""
    payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Test User",
        "company": "Test Company"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
    
    if response.status_code == 201:
        data = response.json()
        if "access_token" in data and "refresh_token" in data:
            # Store token for later tests
            global AUTH_TOKEN
            AUTH_TOKEN = data["access_token"]
            return True, f"User registered, token received"
    return False, f"Status: {response.status_code}, Response: {response.text[:100]}"

def test_user_login() -> Tuple[bool, str]:
    """Test user login"""
    payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_PASSWORD
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            global AUTH_TOKEN
            AUTH_TOKEN = data["access_token"]
            return True, "Login successful"
    return False, f"Status: {response.status_code}"

def test_user_profile() -> Tuple[bool, str]:
    """Test getting user profile"""
    if 'AUTH_TOKEN' not in globals():
        return False, "No auth token (registration/login failed)"
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("user", {}).get("email") == TEST_USER_EMAIL:
            subscription = data.get("subscription", {})
            return True, f"Profile loaded, Plan: {subscription.get('plan', 'none')}"
    return False, f"Status: {response.status_code}"

def test_subscription_creation() -> Tuple[bool, str]:
    """Test that trial subscription was auto-created"""
    if 'AUTH_TOKEN' not in globals():
        return False, "No auth token"
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        subscription = data.get("subscription", {})
        
        if subscription.get("plan") == "trial":
            days_remaining = subscription.get("days_remaining", 0)
            return True, f"Trial active, {days_remaining} days remaining"
    
    return False, "No trial subscription found"

def test_dashboard_stats() -> Tuple[bool, str]:
    """Test dashboard statistics endpoint"""
    response = requests.get(f"{BASE_URL}/api/stats")
    
    if response.status_code == 200:
        data = response.json()
        required_fields = ["active_incidents", "healthy_services", "total_services"]
        if all(field in data for field in required_fields):
            return True, f"{data['healthy_services']}/{data['total_services']} services healthy"
    return False, f"Status: {response.status_code}"

def test_phase2_config() -> Tuple[bool, str]:
    """Test Phase 2 configuration endpoint"""
    response = requests.get(f"{BASE_URL}/api/v2/config")
    
    if response.status_code == 200:
        data = response.json()
        if "learning_enabled" in data:
            return True, f"Learning: {data['learning_enabled']}, Dry-run: {data.get('dry_run_mode')}"
    return False, f"Status: {response.status_code}"

def test_phase3_autonomous_status() -> Tuple[bool, str]:
    """Test Phase 3 autonomous mode status"""
    if 'AUTH_TOKEN' not in globals():
        return False, "No auth token"
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/v3/autonomous/status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        enabled = data.get("autonomous_enabled", False)
        has_access = data.get("user_has_access", False)
        return True, f"Enabled: {enabled}, User access: {has_access}, Plan: {data.get('user_plan')}"
    return False, f"Status: {response.status_code}"

def test_razorpay_plans() -> Tuple[bool, str]:
    """Test Razorpay plans endpoint"""
    response = requests.get(f"{BASE_URL}/api/razorpay/plans")
    
    if response.status_code == 200:
        data = response.json()
        plans = data.get("plans", [])
        if len(plans) > 0:
            return True, f"{len(plans)} plans available"
    return False, f"Status: {response.status_code}"

def test_metrics_ingestion() -> Tuple[bool, str]:
    """Test metrics ingestion endpoint"""
    payload = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "metric_name": "test_metric",
            "value": 100.0,
            "labels": {"service": "test-service", "env": "test"}
        }
    ]
    response = requests.post(f"{BASE_URL}/ingest/metrics", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "accepted":
            return True, f"{data.get('count')} metrics accepted"
    return False, f"Status: {response.status_code}"

def test_services_endpoint() -> Tuple[bool, str]:
    """Test services listing endpoint"""
    response = requests.get(f"{BASE_URL}/api/services")
    
    if response.status_code == 200:
        data = response.json()
        services = data.get("services", [])
        return True, f"{len(services)} services found"
    return False, f"Status: {response.status_code}"

def test_anomalies_endpoint() -> Tuple[bool, str]:
    """Test anomalies endpoint"""
    response = requests.get(f"{BASE_URL}/api/anomalies")
    
    if response.status_code == 200:
        data = response.json()
        anomalies = data.get("anomalies", [])
        return True, f"{len(anomalies)} anomalies found"
    return False, f"Status: {response.status_code}"

def test_incidents_endpoint() -> Tuple[bool, str]:
    """Test incidents endpoint"""
    response = requests.get(f"{BASE_URL}/api/incidents")
    
    if response.status_code == 200:
        data = response.json()
        incidents = data.get("incidents", [])
        return True, f"{len(incidents)} incidents found"
    return False, f"Status: {response.status_code}"

def test_unauthorized_access() -> Tuple[bool, str]:
    """Test that protected endpoints require auth"""
    response = requests.get(f"{BASE_URL}/api/auth/me")
    
    # Should fail without token
    if response.status_code == 401:
        return True, "Auth protection working"
    return False, f"Expected 401, got {response.status_code}"

def test_payment_gateway_config() -> Tuple[bool, str]:
    """Test payment gateway configuration"""
    response = requests.get(f"{BASE_URL}/health/payments")
    
    if response.status_code == 200:
        data = response.json()
        configured = data.get("configured", False)
        status = data.get("status", "unknown")
        return True, f"Status: {status}, Configured: {configured}"
    return False, f"Status: {response.status_code}"

# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    print_header("AI DevOps Autopilot - System Integrity Tests")
    print_info(f"Testing against: {BASE_URL}")
    print_info(f"Test user: {TEST_USER_EMAIL}")
    print()
    
    # Phase 1: Basic Infrastructure Tests
    print_header("Phase 1: Infrastructure & Health Checks")
    run_test("Health Check", test_health_check)
    run_test("Database Connection", test_database_health)
    run_test("Redis Connection", test_redis_connection)
    
    # Phase 2: Authentication Tests
    print_header("Phase 2: Authentication & User Management")
    run_test("User Registration", test_user_registration)
    run_test("User Login", test_user_login)
    run_test("Get User Profile", test_user_profile)
    run_test("Unauthorized Access Block", test_unauthorized_access)
    
    # Phase 3: Subscription Tests
    print_header("Phase 3: Subscription Management")
    run_test("Trial Subscription Auto-Creation", test_subscription_creation)
    run_test("Payment Gateway Config", test_payment_gateway_config)
    run_test("Razorpay Plans", test_razorpay_plans)
    
    # Phase 4: Core Feature Tests
    print_header("Phase 4: Core Features")
    run_test("Dashboard Statistics", test_dashboard_stats)
    run_test("Services Listing", test_services_endpoint)
    run_test("Anomalies Endpoint", test_anomalies_endpoint)
    run_test("Incidents Endpoint", test_incidents_endpoint)
    run_test("Metrics Ingestion", test_metrics_ingestion)
    
    # Phase 5: Advanced Features
    print_header("Phase 5: Advanced Features (Phase 2 & 3)")
    run_test("Phase 2 Configuration", test_phase2_config)
    run_test("Phase 3 Autonomous Status", test_phase3_autonomous_status)
    
    # Final Summary
    print_header("Test Summary")
    total = test_results["passed"] + test_results["failed"] + test_results["skipped"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {test_results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {test_results['failed']}{Colors.END}")
    print(f"{Colors.YELLOW}Skipped: {test_results['skipped']}{Colors.END}")
    print(f"\nPass Rate: {pass_rate:.1f}%")
    
    if test_results["errors"]:
        print(f"\n{Colors.RED}Errors:{Colors.END}")
        for error in test_results["errors"]:
            print(f"  - {error}")
    
    print()
    
    # Exit code based on results
    if test_results["failed"] > 0:
        print(f"{Colors.RED}❌ Some tests failed{Colors.END}")
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}✅ All tests passed!{Colors.END}")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.END}")
        sys.exit(1)