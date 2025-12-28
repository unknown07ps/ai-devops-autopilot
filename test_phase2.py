"""
Phase 2 Test Script
Tests supervised actions, memory learning, and interactive workflows
"""

import asyncio
import httpx
import time
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

class Phase2Tester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def print_header(self, text):
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")
    
    async def test_action_proposals(self):
        """Test action proposal workflow"""
        self.print_header("1️⃣ Testing Action Proposals")
        
        print("📊 Generating incident with anomalies...")
        
        # Send baseline
        for i in range(10):
            await self.client.post(f"{BASE_URL}/ingest/metrics", json=[{
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metric_name": "api_latency_ms",
                "value": 100 + (i * 2),
                "labels": {"service": "payment-api"}
            }])
            time.sleep(0.5)
        
        # Send deployment
        await self.client.post(f"{BASE_URL}/ingest/deployment", json={
            "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z",
            "service": "payment-api",
            "version": "v3.1.0",
            "status": "success",
            "metadata": {"commit": "abc789"}
        })
        
        # Trigger anomaly
        await self.client.post(f"{BASE_URL}/ingest/metrics", json=[{
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metric_name": "api_latency_ms",
            "value": 2000,
            "labels": {"service": "payment-api"}
        }])
        
        print("⏳ Waiting for worker to analyze and propose actions...")
        time.sleep(10)
        
        # Check for pending actions
        response = await self.client.get(f"{BASE_URL}/api/v2/actions/pending")
        if response.status_code == 200:
            data = response.json()
            actions = data.get('actions', [])
            print(f"\n✅ Found {len(actions)} proposed actions:")
            
            for action in actions:
                print(f"\n   Action: {action['action_type']}")
                print(f"   Service: {action['service']}")
                print(f"   Risk: {action['risk']}")
                print(f"   Reasoning: {action['reasoning']}")
                print(f"   Status: {action['status']}")
            
            return actions
        else:
            print("❌ Failed to get pending actions")
            return []
    
    async def test_action_approval(self, action_id: str):
        """Test action approval flow"""
        self.print_header("2️⃣ Testing Action Approval")
        
        print(f"✅ Approving action: {action_id}")
        
        response = await self.client.post(
            f"{BASE_URL}/api/v2/actions/approve",
            json={
                "action_id": action_id,
                "approved_by": "test_user",
                "notes": "Approved for testing Phase 2 functionality"
            }
        )
        
        if response.status_code == 200:
            print("✅ Action approved successfully")
            result = response.json()
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")
            
            # Wait for execution
            print("\n⏳ Waiting for action to execute...")
            time.sleep(5)
            
            # Check action status
            response = await self.client.get(f"{BASE_URL}/api/v2/actions/{action_id}")
            if response.status_code == 200:
                action = response.json()['action']
                print(f"\n   Execution Status: {action['status']}")
                if action.get('result'):
                    print(f"   Result: {action['result'].get('message', 'No message')}")
                    if action['result'].get('dry_run'):
                        print("   ⚠️  DRY RUN MODE - No actual changes made")
            
            return True
        else:
            print(f"❌ Approval failed: {response.status_code}")
            return False
    
    async def test_learning_insights(self):
        """Test learning and insights"""
        self.print_header("3️⃣ Testing Learning Insights")
        
        print("📚 Getting learning statistics...")
        
        response = await self.client.get(f"{BASE_URL}/api/v2/learning/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"\n✅ Learning Statistics:")
            print(f"   Total incidents learned: {stats.get('total_incidents_learned', 0)}")
            print(f"   Total actions recorded: {stats.get('total_actions_recorded', 0)}")
            print(f"   Services monitored: {stats.get('services_monitored', 0)}")
        
        print("\n📊 Getting service insights...")
        
        response = await self.client.get(f"{BASE_URL}/api/v2/learning/insights/payment-api")
        if response.status_code == 200:
            insights = response.json()
            
            if insights.get('total_incidents', 0) > 0:
                print(f"\n✅ Service Insights (payment-api):")
                print(f"   Total incidents: {insights['total_incidents']}")
                print(f"   Success rate: {insights['success_rate']:.1f}%")
                print(f"   Avg resolution: {insights['avg_resolution_time_minutes']:.1f} minutes")
                
                if insights.get('top_root_causes'):
                    print(f"\n   Top Root Causes:")
                    for cause in insights['top_root_causes']:
                        print(f"   - {cause['cause']} ({cause['count']}x)")
                
                if insights.get('most_effective_actions'):
                    print(f"\n   Most Effective Actions:")
                    for action in insights['most_effective_actions']:
                        print(f"   - {action['action_type']}: {action['success_rate']:.0f}% success")
            else:
                print("   ℹ️  No incidents recorded yet")
    
    async def test_action_recommendations(self):
        """Test action recommendations based on learning"""
        self.print_header("4️⃣ Testing Action Recommendations")
        
        print("💡 Getting recommended actions for payment-api...")
        
        response = await self.client.get(f"{BASE_URL}/api/v2/recommendations/payment-api")
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            if recommendations:
                print(f"\n✅ Found {len(recommendations)} recommendations:")
                
                for rec in recommendations:
                    print(f"\n   Action: {rec['action_type']}")
                    print(f"   Confidence: {rec['confidence']}%")
                    print(f"   Success count: {rec['success_count']}")
                    print(f"   Avg resolution: {rec['avg_resolution_time_seconds']:.1f}s")
            else:
                print("   ℹ️  No recommendations yet - need more incident history")
    
    async def test_action_history(self):
        """Test action history tracking"""
        self.print_header("5️⃣ Testing Action History")
        
        print("📜 Getting action history...")
        
        response = await self.client.get(f"{BASE_URL}/api/v2/actions/history?limit=10")
        if response.status_code == 200:
            data = response.json()
            actions = data.get('actions', [])
            
            print(f"\n✅ Found {len(actions)} historical actions:")
            
            for action in actions[:5]:
                print(f"\n   ID: {action['id']}")
                print(f"   Type: {action['action_type']}")
                print(f"   Service: {action['service']}")
                print(f"   Status: {action['status']}")
                print(f"   Proposed: {action['proposed_at']}")
                
                if action.get('approved_by'):
                    print(f"   Approved by: {action['approved_by']}")
    
    async def test_similar_incidents(self):
        """Test similar incident matching"""
        self.print_header("6️⃣ Testing Similar Incident Detection")
        
        print("🔍 Finding similar incidents...")
        
        response = await self.client.get(
            f"{BASE_URL}/api/v2/learning/similar-incidents?service=payment-api&limit=3"
        )
        
        if response.status_code == 200:
            data = response.json()
            similar = data.get('similar_incidents', [])
            
            if similar:
                print(f"\n✅ Found {len(similar)} similar incidents:")
                
                for incident in similar:
                    print(f"\n   Incident ID: {incident['id']}")
                    print(f"   Root cause: {incident['root_cause']['description']}")
                    print(f"   Similarity: {incident.get('similarity_score', 0) * 100:.0f}%")
                    print(f"   Resolution time: {incident['resolution_time_seconds'] / 60:.1f}min")
                    print(f"   Actions taken: {len(incident.get('actions_taken', []))}")
            else:
                print("   ℹ️  No similar incidents found yet")
    
    async def test_configuration(self):
        """Test configuration endpoints"""
        self.print_header("7️⃣ Testing Configuration")
        
        print("⚙️  Getting current configuration...")
        
        response = await self.client.get(f"{BASE_URL}/api/v2/config")
        if response.status_code == 200:
            config = response.json()
            print(f"\n✅ Current Configuration:")
            print(f"   Auto-approve low risk: {config['auto_approve_low_risk']}")
            print(f"   Dry run mode: {config['dry_run_mode']}")
            print(f"   Learning enabled: {config['learning_enabled']}")
            print(f"   Action cooldown: {config['action_cooldown_seconds']}s")
    
    async def run_full_test(self):
        """Run complete Phase 2 test suite"""
        try:
            self.print_header("🧪 AI DevOps Autopilot - Phase 2 Test Suite")
            
            # Test 1: Action Proposals
            actions = await self.test_action_proposals()
            
            # Test 2: Action Approval (if we have actions)
            if actions:
                await self.test_action_approval(actions[0]['id'])
            
            # Test 3: Learning Insights
            await self.test_learning_insights()
            
            # Test 4: Recommendations
            await self.test_action_recommendations()
            
            # Test 5: Action History
            await self.test_action_history()
            
            # Test 6: Similar Incidents
            await self.test_similar_incidents()
            
            # Test 7: Configuration
            await self.test_configuration()
            
            # Final Summary
            self.print_header("✅ Phase 2 Test Suite Complete!")
            
            print("🎯 Key Features Tested:")
            print("   ✓ Action proposal workflow")
            print("   ✓ Action approval and execution")
            print("   ✓ Incident memory and learning")
            print("   ✓ Action recommendations based on history")
            print("   ✓ Similar incident detection")
            print("   ✓ Configuration management")
            
            print("\n💡 Next Steps:")
            print("   1. Check Slack for interactive incident alerts")
            print("   2. Use approval buttons to test interactive workflow")
            print("   3. View dashboard to see Phase 2 features")
            print("   4. Enable auto-approval for low-risk actions")
            print("   5. Monitor learning improvements over time")
            
            print("\n🔄 To enable production mode:")
            print("   - Set DRY_RUN_MODE=false in .env")
            print("   - Set AUTO_APPROVE_LOW_RISK=true for automation")
            print("   - Configure real deployment/scaling endpoints")
            
        finally:
            await self.client.aclose()

async def main():
    tester = Phase2Tester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())