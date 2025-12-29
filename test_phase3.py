"""
Phase 3 Comprehensive Test Script
Tests all autonomous execution features
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict

BASE_URL = "http://localhost:8000"

class Phase3Tester:
    def __init__(self):
        self.client = None
        self.test_results = []
    
    async def setup(self):
        """Setup test client"""
        self.client = httpx.AsyncClient(timeout=30.0)
        print("🚀 Phase 3 Autonomous Mode Test Suite")
        print("=" * 60)
        print()
    
    async def teardown(self):
        """Cleanup"""
        if self.client:
            await self.client.aclose()
        
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['name']}: {result['error']}")
    
    def record_test(self, name: str, passed: bool, error: str = None):
        """Record test result"""
        self.test_results.append({
            'name': name,
            'passed': passed,
            'error': error
        })
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        if error and not passed:
            print(f"      Error: {error}")
    
    async def test_autonomous_status(self):
        """Test 1: Get autonomous status"""
        print("\n1️⃣  Testing Autonomous Status")
        print("-" * 60)
        
        try:
            response = await self.client.get(f"{BASE_URL}/api/v3/autonomous/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Mode: {data.get('execution_mode', 'N/A')}")
                print(f"   Enabled: {data.get('autonomous_enabled', False)}")
                print(f"   Confidence Threshold: {data.get('confidence_threshold', 0)}%")
                print(f"   Total Actions: {data.get('total_autonomous_actions', 0)}")
                print(f"   Success Rate: {data.get('success_rate', 0)}%")
                
                if data.get('learning_weights'):
                    weights = data['learning_weights']
                    print(f"   Learning Weights:")
                    print(f"      Rule-based: {weights.get('rule_based', 0)}")
                    print(f"      AI: {weights.get('ai', 0)}")
                    print(f"      Historical: {weights.get('historical', 0)}")
                
                self.record_test("Get autonomous status", True)
            else:
                self.record_test("Get autonomous status", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Get autonomous status", False, str(e))
    
    async def test_mode_changes(self):
        """Test 2: Change execution modes"""
        print("\n2️⃣  Testing Mode Changes")
        print("-" * 60)
        
        modes_to_test = [
            ("supervised", 75),
            ("night_mode", 80),
            ("autonomous", 85),
            ("manual", 70)
        ]
        
        for mode, threshold in modes_to_test:
            try:
                response = await self.client.post(
                    f"{BASE_URL}/api/v3/autonomous/mode",
                    json={
                        "mode": mode,
                        "confidence_threshold": threshold
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Changed to {mode} (threshold: {threshold}%)")
                    self.record_test(f"Set mode to {mode}", True)
                else:
                    self.record_test(f"Set mode to {mode}", False, f"Status {response.status_code}")
                
                await asyncio.sleep(0.5)
            
            except Exception as e:
                self.record_test(f"Set mode to {mode}", False, str(e))
        
        # Test invalid mode
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v3/autonomous/mode",
                json={"mode": "invalid_mode"}
            )
            
            if response.status_code == 400:
                print("   Invalid mode correctly rejected")
                self.record_test("Reject invalid mode", True)
            else:
                self.record_test("Reject invalid mode", False, "Should return 400")
        
        except Exception as e:
            self.record_test("Reject invalid mode", False, str(e))
    
    async def test_safety_rails(self):
        """Test 3: Safety rail status"""
        print("\n3️⃣  Testing Safety Rails")
        print("-" * 60)
        
        try:
            response = await self.client.get(f"{BASE_URL}/api/v3/autonomous/safety-status")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('limits'):
                    limits = data['limits']
                    print(f"   Limits:")
                    print(f"      Max concurrent actions: {limits.get('max_concurrent_actions')}")
                    print(f"      Action cooldown: {limits.get('action_cooldown_seconds')}s")
                    print(f"      Max rollbacks/hour: {limits.get('max_rollbacks_per_hour')}")
                    print(f"      Max scale factor: {limits.get('max_scale_factor')}x")
                
                if data.get('current_state'):
                    state = data['current_state']
                    print(f"   Current State:")
                    print(f"      Active actions: {state.get('active_actions')}")
                    print(f"      Active cooldowns: {state.get('active_cooldowns')}")
                    print(f"      Recent rollbacks: {state.get('recent_rollbacks')}")
                    
                    if state.get('cooldowns'):
                        print(f"      Active cooldowns:")
                        for cooldown in state['cooldowns'][:3]:
                            print(f"         {cooldown['service']}/{cooldown['action_type']}: {cooldown['remaining_seconds']}s")
                
                self.record_test("Get safety status", True)
            else:
                self.record_test("Get safety status", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Get safety status", False, str(e))
    
    async def test_autonomous_outcomes(self):
        """Test 4: Autonomous outcomes and learning"""
        print("\n4️⃣  Testing Autonomous Outcomes")
        print("-" * 60)
        
        try:
            response = await self.client.get(f"{BASE_URL}/api/v3/autonomous/outcomes?limit=20")
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('statistics', {})
                
                print(f"   Total outcomes: {stats.get('total', 0)}")
                print(f"   Successes: {stats.get('successes', 0)}")
                print(f"   Failures: {stats.get('failures', 0)}")
                print(f"   Success rate: {stats.get('success_rate', 0)}%")
                
                if stats.get('by_action_type'):
                    print(f"   By action type:")
                    for action_stat in stats['by_action_type'][:5]:
                        print(f"      {action_stat['action_type']}: "
                              f"{action_stat['success_rate']}% "
                              f"({action_stat['successes']}/{action_stat['total']})")
                
                self.record_test("Get autonomous outcomes", True)
            else:
                self.record_test("Get autonomous outcomes", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Get autonomous outcomes", False, str(e))
        
        # Test with filters
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v3/autonomous/outcomes?limit=10&success_only=true"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Successful outcomes only: {len(data.get('outcomes', []))}")
                self.record_test("Filter outcomes by success", True)
            else:
                self.record_test("Filter outcomes by success", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Filter outcomes by success", False, str(e))
    
    async def test_action_history(self):
        """Test 5: Autonomous action history"""
        print("\n5️⃣  Testing Action History")
        print("-" * 60)
        
        try:
            response = await self.client.get(f"{BASE_URL}/api/v3/autonomous/action-history?limit=10")
            
            if response.status_code == 200:
                data = response.json()
                actions = data.get('actions', [])
                
                print(f"   Total actions: {data.get('total', 0)}")
                
                if actions:
                    print(f"   Recent actions:")
                    for action in actions[:5]:
                        status_icon = "✅" if action.get('success') else "❌"
                        print(f"      {status_icon} {action['action_type']} on {action['service']} "
                              f"({action['confidence']}% confidence)")
                
                self.record_test("Get action history", True)
            else:
                self.record_test("Get action history", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Get action history", False, str(e))
        
        # Test with filters
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v3/autonomous/action-history?action_type=rollback&limit=5"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Rollback actions only: {len(data.get('actions', []))}")
                self.record_test("Filter action history", True)
            else:
                self.record_test("Filter action history", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Filter action history", False, str(e))
    
    async def test_learning_weights(self):
        """Test 6: Adjust learning weights"""
        print("\n6️⃣  Testing Learning Weight Adjustment")
        print("-" * 60)
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v3/autonomous/adjust-weights",
                json={
                    "rule_weight": 0.5,
                    "ai_weight": 0.3,
                    "historical_weight": 0.2
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                weights = data.get('learning_weights', {})
                print(f"   Updated weights:")
                print(f"      Rule-based: {weights.get('rule_based')}")
                print(f"      AI: {weights.get('ai')}")
                print(f"      Historical: {weights.get('historical')}")
                
                # Verify they sum to 1.0
                total = sum(weights.values())
                if abs(total - 1.0) < 0.01:
                    print(f"   ✓ Weights normalized (sum = {total:.3f})")
                    self.record_test("Adjust learning weights", True)
                else:
                    self.record_test("Adjust learning weights", False, f"Weights don't sum to 1.0: {total}")
            else:
                self.record_test("Adjust learning weights", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Adjust learning weights", False, str(e))
        
        # Test invalid weights
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v3/autonomous/adjust-weights",
                json={"rule_weight": 1.5}  # Invalid: > 1.0
            )
            
            if response.status_code == 400:
                print("   Invalid weights correctly rejected")
                self.record_test("Reject invalid weights", True)
            else:
                self.record_test("Reject invalid weights", False, "Should return 400")
        
        except Exception as e:
            self.record_test("Reject invalid weights", False, str(e))
    
    async def test_confidence_breakdown(self):
        """Test 7: Confidence breakdown"""
        print("\n7️⃣  Testing Confidence Breakdown")
        print("-" * 60)
        
        # First, get some action IDs
        try:
            response = await self.client.get(f"{BASE_URL}/api/v3/autonomous/action-history?limit=5")
            
            if response.status_code == 200:
                data = response.json()
                actions = data.get('actions', [])
                
                if actions:
                    action_id = actions[0]['action_id']
                    
                    # Get confidence breakdown
                    response = await self.client.get(
                        f"{BASE_URL}/api/v3/autonomous/confidence-breakdown/{action_id}"
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"   Action: {data.get('action_type')} on {data.get('service')}")
                        print(f"   Overall confidence: {data.get('overall_confidence')}%")
                        print(f"   Status: {data.get('status')}")
                        
                        if data.get('reasoning'):
                            print(f"   Reasoning:")
                            for line in data['reasoning'].split('\n')[:5]:
                                if line.strip():
                                    print(f"      {line}")
                        
                        self.record_test("Get confidence breakdown", True)
                    else:
                        self.record_test("Get confidence breakdown", False, f"Status {response.status_code}")
                else:
                    print("   No autonomous actions found to test")
                    self.record_test("Get confidence breakdown", True, "No data to test")
            else:
                self.record_test("Get confidence breakdown", False, "Could not get action history")
        
        except Exception as e:
            self.record_test("Get confidence breakdown", False, str(e))
    
    async def test_integration_with_phase2(self):
        """Test 8: Integration with Phase 2 endpoints"""
        print("\n8️⃣  Testing Phase 2 Integration")
        print("-" * 60)
        
        try:
            # Get pending actions
            response = await self.client.get(f"{BASE_URL}/api/v2/actions/pending")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Pending actions: {data.get('total', 0)}")
                self.record_test("Phase 2 integration", True)
            else:
                self.record_test("Phase 2 integration", False, f"Status {response.status_code}")
        
        except Exception as e:
            self.record_test("Phase 2 integration", False, str(e))
    
    async def run_all_tests(self):
        """Run all tests"""
        await self.setup()
        
        try:
            await self.test_autonomous_status()
            await asyncio.sleep(1)
            
            await self.test_mode_changes()
            await asyncio.sleep(1)
            
            await self.test_safety_rails()
            await asyncio.sleep(1)
            
            await self.test_autonomous_outcomes()
            await asyncio.sleep(1)
            
            await self.test_action_history()
            await asyncio.sleep(1)
            
            await self.test_learning_weights()
            await asyncio.sleep(1)
            
            await self.test_confidence_breakdown()
            await asyncio.sleep(1)
            
            await self.test_integration_with_phase2()
        
        finally:
            await self.teardown()

async def main():
    tester = Phase3Tester()
    await tester.run_all_tests()

if __name__ == "__main__":
    print("\n⚡ Starting Phase 3 Test Suite...")
    print("📝 Make sure the API server is running on localhost:8000")
    print("🔄 Starting in 2 seconds...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")