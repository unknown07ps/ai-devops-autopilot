# realtime_monitor.py
import asyncio
import httpx
from datetime import datetime

API_BASE = "http://localhost:8000"

async def monitor_system():
    """Real-time system monitor"""
    client = httpx.AsyncClient(timeout=10.0)
    
    print("🔴 LIVE MONITORING STARTED")
    print("=" * 60)
    
    while True:
        try:
            # Get current stats
            stats = await client.get(f"{API_BASE}/api/stats")
            incidents = await client.get(f"{API_BASE}/api/incidents?limit=5")
            pending = await client.get(f"{API_BASE}/api/v2/actions/pending")
            auto_status = await client.get(f"{API_BASE}/api/v3/autonomous/status")
            
            # Clear screen
            print("\033[2J\033[H")
            
            # Display timestamp
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            # Display stats
            if stats.status_code == 200:
                data = stats.json()
                print(f"\n📊 SYSTEM STATUS")
                print(f"  🚨 Active Incidents: {data['active_incidents']}")
                print(f"  ⚠️  Critical Anomalies: {data['critical_anomalies']}")
                print(f"  💚 Healthy Services: {data['healthy_services']}/{data['total_services']}")
                print(f"  ⏱️  Avg Resolution: {data['avg_resolution_time_minutes']}m")
            
            # Display pending actions
            if pending.status_code == 200:
                actions = pending.json().get('actions', [])
                print(f"\n⚡ PENDING ACTIONS: {len(actions)}")
                for action in actions[:3]:
                    print(f"  • {action['action_type']} on {action['service']} ({action['risk']} risk)")
            
            # Display autonomous status
            if auto_status.status_code == 200:
                auto = auto_status.json()
                print(f"\n🤖 AUTONOMOUS MODE")
                print(f"  Mode: {auto.get('execution_mode', 'unknown').upper()}")
                print(f"  Success Rate: {auto.get('success_rate', 0):.1f}%")
                print(f"  Active Actions: {auto.get('active_actions', 0)}")
            
            # Display recent incidents
            if incidents.status_code == 200:
                inc_list = incidents.json().get('incidents', [])
                if inc_list:
                    print(f"\n🚨 RECENT INCIDENTS")
                    for inc in inc_list[:3]:
                        severity_icon = "🔴" if inc['severity'] == 'critical' else "🟠"
                        print(f"  {severity_icon} {inc['service']}: {inc['root_cause'][:50]}...")
            
            print("\n" + "=" * 60)
            print("Press Ctrl+C to stop monitoring")
            
            await asyncio.sleep(5)  # Refresh every 5 seconds
            
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(5)
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(monitor_system())